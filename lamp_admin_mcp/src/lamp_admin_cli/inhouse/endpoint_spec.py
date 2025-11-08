import base64
import os
import re
import subprocess
from pathlib import Path
from typing import Callable, List, Optional

import boto3
from docker import ContextAPI, DockerClient, errors
from dotenv import dotenv_values
from jinja2 import Environment, FileSystemLoader

from lamp_admin_cli.settings import LAMPStage
from lamp_admin_cli.utils import get_project_dir, get_serving_app_version

CLI_CUR_DIR = Path(__file__).parent
USER_DIR = get_project_dir()

template_dir = Path(__file__).parent / Path("template")
file_loader = FileSystemLoader(template_dir)
jinja_env = Environment(loader=file_loader)



def _get_metadata_yaml(*args, **kwargs):
    t = jinja_env.get_template("metadata.{{ stage }}.yaml.jinja2")
    return t.render(**kwargs)

def _get_default_values(*args, **kwargs):
    t = jinja_env.get_template("default_values.yaml")
    return t.render(**kwargs)

class BaseEndpointSpec:
    name_tmp: str
    render_func: Optional[Callable]
    
    def __init__(self, stage: LAMPStage, body="", file_name_kwargs=None, render_kwargs=None) -> None:
        self.stage = stage.val
        self.body = body
        self.file_name_kwargs = file_name_kwargs or {}
        self.render_kwargs = render_kwargs or {}
        
        if not self.body and self.render_func:
            self.body = self.render_func(**self.render_kwargs)
            
    def file_name(self) -> Path:
        return Path(self.name_tmp.format(stage=self.stage, **self.file_name_kwargs))
    
    def save(self, output_dir: Path):
        output_path = output_dir / self.file_name()
        
        with open(output_path, "w") as f:
            f.write(self.body)
        
        
class MetadataSpec(BaseEndpointSpec):
    name_tmp = "metadata.{stage}.yaml"
    render_func = _get_metadata_yaml
    
class ValuesSpec(BaseEndpointSpec):
    name_tmp = "values.{stage}.yaml"
    render_func = _get_default_values

class EnvSpec(BaseEndpointSpec):
    name_tmp = ".env.{service}.{stage}"
    render_func = None
    
# TF-529
# openapi.json 파일이 endpoint spec 업로드 과정에 추가.
# model spec이지만...
# Gen openapi.json
# and also can check that is app startup with given env
# 적어도 누락된 환경변수에 대한 검증은 가능.

def run_docker_for_generate_openapi_json(project_path: Path, dst_dir: Path, env_files_path: List[Path]) -> Path:
    """
    1. docker-compose.yaml과 docker-compose.sh 파일이 존재하는 경로를 입력으로 받음.
    2. docker-compose.sh build fastapi 로 이미지 빌드.
    1. 이미지와 환경변수로 실행하여 dst_dir 폴더에 openapi.json 파일 생성.
    2. 해당 파일 경로 리턴.
    """
    envs = {}
    for env_path in env_files_path:
        envs.update(dotenv_values(env_path))
    
    envs.update({
        "LAMP_PROJECT_ID": "test-in-lamp-cli",
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test",
        "AWS_DEFAULT_REGION": "test",
    })

    print("Build Docker for Generate openapi")
    
    script = f"{project_path}/docker-compose.sh"
    if not os.access(script, os.X_OK):
         print(f"{script} is not executable. Fixing permission...")
         os.chmod(script, 0o755)
    
    build_env = os.environ.copy()
    build_env["DOCKER_BUILDKIT"] = "1"
    result = subprocess.run(
        " ".join([script, "build", "fastapi"]),
        env=build_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
        shell=True,
    )
    o = result.stdout

    if result.stderr:
        print(result.stderr)
        
    image_ids = re.findall(r"(?:writing image|exporting manifest list) sha256:([0-9a-f]{64})", o)
    assert image_ids and len(image_ids) == 1
    
    
    try:
        client = DockerClient.from_env()
    except errors.DockerException:
        c = ContextAPI.get_current_context()
        base_url = c.endpoints.get("docker", {}).get("Host", "")
        client = DockerClient(base_url=base_url, version="auto", tls=c.TLSConfig)
    

    # build 완료 이후 실행인데..
    version = get_serving_app_version(project_path)
    scripts_dir = project_path / "scripts/"
    print("Running Docker for Generate openapi")
    if version.release >= (0, 3, 0):
        print("서빙앱 버전이 v0.3.0보다 높아 scripts/cli.py generate-openapi 기능을 사용합니다. description.md 파일 ")
        # description.md 파일이 있다.
        entrypoint = ["python", "scripts/cli.py", "generate-openapi", "--output-path", "/tmp/openapi.json"]
        volumes = [f"{dst_dir.absolute()}:/tmp", f"{scripts_dir.absolute()}:/code/scripts"]

        description_md_file = project_path / Path("description.md")

        # For MCP compatibility: use existing description.md if available (default behavior)
        use_description = description_md_file.exists()
        if use_description:
            # 써라
            entrypoint.append("--description-file-path")
            entrypoint.append("description.md")
            volumes.append(f"{description_md_file.absolute()}:/code/description.md")
        else:
            # 그냥 하자.
            pass
        
        c = client.containers.run(
            image=image_ids[0],
            entrypoint=entrypoint,
            environment=envs,
            volumes=volumes,
            user=f"{os.getuid()}:{os.getgid()}",
            auto_remove=True,
            stdout=True,
            stderr=True,
            detach=False,
        )

        # 실패 여부 확인
        if b"Traceback" in c:
            raise RuntimeError("openapi.json 생성 중 컨테이너 내부 오류가 발생했습니다.\n" + c.decode())

    else:
        # 하던대로
        c = client.containers.run(
            image=image_ids[0],
            entrypoint=["python", "-c", "import json; from fastapi.openapi.utils import get_openapi; from src._core.app import app; spec = json.dumps(get_openapi(title=app.title,version=app.version,openapi_version=app.openapi_version,description=app.description,routes=app.routes,)); f = open('/tmp/openapi.json', 'w'); f.write(spec); print('success_gen_open_api'); "],
            environment=envs,
            volumes=[f"{dst_dir.absolute()}:/tmp"],
            user=f"{os.getuid()}:{os.getgid()}",
            auto_remove=True,
            stdout=True,
            stderr=True,
            detach=False,
        )
        # 실패 여부 확인
        if b"Traceback" in c:
            raise RuntimeError("openapi.json 생성 중 컨테이너 내부 오류가 발생했습니다.\n" + c.decode())
        
    print("[Done] Running Docker for Generate openapi")
    return dst_dir / "openapi.json"
