import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4
from typing_extensions import List, Optional, Union, TYPE_CHECKING

import yaml
from boto3 import resource
from mlflow import MlflowClient
from mlflow.entities.run import Run
from mlflow.store.artifact.runs_artifact_repo import RunsArtifactRepository
import logging


from lamp_admin_cli.inhouse.endpoint_spec import run_docker_for_generate_openapi_json
from lamp_admin_cli.inhouse.mlbo.client import MLBOAPIClient
from lamp_admin_cli.settings import LAMP_CLI_LOCAL_DEV, Configure
from lamp_admin_cli.utils import get_project_dir, is_serving_app_dir

"""In-house logic for MCP tools.

This MCP-only branch removes stress-test utilities and CLI integrations.
"""

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

logger = logging.getLogger(__name__)
mlflow_client = MlflowClient()
mlbo_client = MLBOAPIClient()
#console = Console()
s3 = resource(
    's3',
    endpoint_url="http://127.0.0.1:4566" if LAMP_CLI_LOCAL_DEV else None
)


PROJECT_NAME = "project_name"
BUILD_VERSION = "last_modified_build_version"
MODEL_SPEC_DOCKER_COMPOSE_TAG_KEY = "model_spec_docker_compose"
MODEL_SPEC_ENVS_TAG_KEY = "model_spec_envs"

MODEL_SPEC_OPENAPI_TAG_KEY = "model_spec_openapi"
ENDPOINT_SPEC_VALUES_TAG_KEY = "endpoint_spec_values"
ENDPOINT_SPEC_ENVS_TAG_KEY = "endpoint_spec_envs"
ENDPOINT_SPEC_METADATA_TAG_KEY = "endpoint_spec_metadata"

def download_spec_from_registered_model(
    profile: Configure,
    pid: str = "",
    mv: str = "",
):
    bucket = profile.LAMP_ENVIRONMENT.CONF.INHOUSE_SERVING_REPOSITORY
    bucket = s3.Bucket(name=bucket)
    
    model_version = mlflow_client.get_model_version(name=pid, version=mv)

    run_id = model_version.run_id
    run = mlflow_client.get_run(run_id=str(run_id))
    if not run:
        raise ValueError(f"Can not find a given run: {run_id}")
    project_name = _get_project_name(run)
    build_version = _get_build_version(run, bucket, project_name)

    if not list(bucket.objects.filter(Prefix=project_name+"/"+str(build_version))):
        raise ValueError(f"Can not find Spec artifacts from project")

    dst_dir =  get_project_dir().joinpath(Path(project_name+ "/" + str(build_version)))
    _download_specs(bucket, project_name, build_version, dst_dir)

    bucket = profile.LAMP_ENVIRONMENT.CONF.DATABRICKS_S3_BUCKET
    return True

def download_spec(
    profile: Configure,
    project_name: str = "",
    build_version: str = "",
    run_id: str = "",
):
    bucket = profile.LAMP_ENVIRONMENT.CONF.INHOUSE_SERVING_REPOSITORY
    bucket = s3.Bucket(name=bucket)
    
    if run_id:
        run = mlflow_client.get_run(run_id=run_id)
        if not run:
            logging.info(f"Can not find a given run: {run_id}")
            return None

        project_name = _get_project_name(run)
        build_version = build_version or _get_build_version(run, bucket, project_name)

    if not (project_name and build_version):
        raise ValueError("(project_name, build_version), (run_id) 중 옳은 값을 입력해주셔야 합니다.")
    if not list(bucket.objects.filter(Prefix=project_name+"/"+str(build_version))):
        raise ValueError(f"Can not find Spec artifacts from project")

    dst_dir =  get_project_dir().joinpath(Path(project_name+ "/" + str(build_version)))
    _download_specs(bucket, project_name, build_version, dst_dir)
    return True

    
    # get build version
def create_dummy_run(
    profile: Configure,
    project_name: str,
    run_name: str = ""
):
    exp_name = "/Shared/" + project_name
    
    
    exp = mlflow_client.get_experiment_by_name(exp_name)
    
    if not exp:
        logging.info(f"Can not find experiment named {exp_name}, create experiment")
        exp = mlflow_client.create_experiment(name=exp_name)
        exp = mlflow_client.get_experiment_by_name(exp_name)

    # Run 생성
    run = mlflow_client.create_run(
        experiment_id=exp.experiment_id, # type: ignore
        run_name=run_name,
        # run_name=run_name if run_name else None,
        tags={
            PROJECT_NAME: project_name,
            }
        )
    # Run status finished
    mlflow_client.set_terminated(run_id=run.info.run_id)
    # Dummy MLserving 등록
    
    
    logging.info(f"Create run")
    j =run.to_dictionary()
    logging.info(json.dumps(j))
    
    return run



def upload_serving_model_spec(
    profile: Configure,
    run_id,
    docker_compose: List[Path],
    env_files: List[Path],
    is_override: bool
):
    run = mlflow_client.get_run(run_id=run_id)
    if not run:
        raise ValueError(f"Can not find a given run: {run_id}")

    tags = run.data.tags
    if (tags.get(ENDPOINT_SPEC_ENVS_TAG_KEY) \
            or tags.get(ENDPOINT_SPEC_METADATA_TAG_KEY) \
            or tags.get(ENDPOINT_SPEC_VALUES_TAG_KEY)
            ):
        if not is_override:
            raise ValueError(
                "이미 업로드 된 Serving Endpoint Spec이 존재합니다. "
                "Model Spec을 재업로드 시 Endpoint Spec이 무시되며 "
                "해당 Run을 통해 Serving 중인 모델이 있다면 장애가 발생합니다."
            )
    
    project_name = _get_project_name(run)

    
    bucket = profile.LAMP_ENVIRONMENT.CONF.INHOUSE_SERVING_REPOSITORY
    
    # get build version
    bucket = s3.Bucket(name=bucket)
    build_version = _get_build_version(run, bucket, project_name, next_bool=True)
    
    paths = _upload_specs(bucket, project_name, build_version, [*docker_compose, *env_files])
    tag_paths = _get_tag_paths(paths, len(docker_compose), len(env_files))
    
    # Tagging run
    _run_set_tags(run,
                  [BUILD_VERSION, MODEL_SPEC_DOCKER_COMPOSE_TAG_KEY, MODEL_SPEC_ENVS_TAG_KEY],
                  [build_version, *tag_paths])
    # Delete Endpoint Spec tag
    if is_override:
        _run_delete_tags(run, [ENDPOINT_SPEC_METADATA_TAG_KEY,
                   ENDPOINT_SPEC_VALUES_TAG_KEY,
                   ENDPOINT_SPEC_ENVS_TAG_KEY]
        )
    logging.info(f"Upload_serving_model_spec to {run_id}")
    
    return True



def generate_openapi(
    docker_compose_sh: Path,
    env_files: List[Path],
    ) -> Path:

    # 3. get dst_dir
    dst_parent_dir =  docker_compose_sh.parent
    if is_serving_app_dir(dst_parent_dir):
        dst_dir = dst_parent_dir / Path(".deployment")
        if not dst_dir.exists():
            dst_dir.mkdir()
    else:
        dst_dir = dst_parent_dir

    # https://github.com/letsur-dev/lamp_admin_cli/issues/43
    # 1. 입력 받은 env_path로 실행
    # 2. local 용 .env로 실행
    ret = run_docker_for_generate_openapi_json(dst_parent_dir, dst_dir, env_files)

    return ret

    
def upload_serving_endpoint_spec(
    profile: Configure,
    run_id: str,
    build_version: str,
    metadata_files: List[Path],
    values_files: List[Path],
    env_files: List[Path],
    openapi_files: List[Path],
):
    run = mlflow_client.get_run(run_id=run_id)
    if not run:
        raise ValueError(f"Can not find a given run: {run_id}")

    tags = run.data.tags
    if not (tags.get(MODEL_SPEC_DOCKER_COMPOSE_TAG_KEY) \
            or not tags.get(MODEL_SPEC_ENVS_TAG_KEY)):
        raise ValueError(f"Serving Model Spec이 업로드되지 않았습니다.")
    
    bucket = profile.LAMP_ENVIRONMENT.CONF.INHOUSE_SERVING_REPOSITORY
    bucket = s3.Bucket(name=bucket)
    # GET tags for find S3 path
    project_name = _get_project_name(run)
    build_version = build_version or _get_build_version(run, bucket=bucket, project_name=project_name)
    
 
    paths = _upload_specs(bucket, project_name, build_version, [*metadata_files, *values_files, *env_files, *openapi_files])
    tag_paths = _get_tag_paths(paths, len(metadata_files), len(values_files), len(env_files), len(openapi_files))
    
    # Tagging run
    _run_set_tags(run,
                  [ENDPOINT_SPEC_METADATA_TAG_KEY,
                   ENDPOINT_SPEC_VALUES_TAG_KEY,
                   ENDPOINT_SPEC_ENVS_TAG_KEY,
                   MODEL_SPEC_OPENAPI_TAG_KEY,
                   ],
                  tag_paths)
    logging.info(f"Upload_serving_endpoint_spec to {run_id}")
    return True

    

def _get_tag_paths(paths: List, *args):
    """
    paths: _upload_specs의 ret, path
    args: files들의 각각 len(files)
    
    retrun len(args) 길이의 ,로 조인된 파일 이름들. len(files)가 0이면, '' 값 
    """
    assert sum(args) == len(paths)
    ret = []
    i = 0
    for x in args:
        j = i + x
        tmp = ','.join(paths[i:j])
        ret.append(tmp)
        i = j
    return ret
        

def _get_project_name(run: Run):
    if ret:= run.data.tags.get(PROJECT_NAME):
        return ret
    project_name = mlflow_client.get_experiment(run.info.experiment_id).name.split("/")[-1]
    _run_set_tags(run, [PROJECT_NAME], [project_name])
    return project_name


def _make_unique_build_version(run: Run, v: int) -> str:
    return run.info.run_id + "_" + str(v)

def _get_build_version_id(v: str) -> int:
    """
    MLOP-322
    기존의 {build_version_uid}의 BUILD_VERSION이
    {run_id}_{build_version_uid}로 변함.
    """
    return int(v.split("_")[-1])

def _get_build_version(run: Run, bucket, project_name, next_bool=False) -> str:
    if last_version := run.data.tags.get(BUILD_VERSION):
        last_version_id = _get_build_version_id(last_version)
        if next_bool:
            last_version_id = last_version_id + 1
            return _make_unique_build_version(run, last_version_id)
        return last_version
        

    # Build Version Tag가 없을 땐
    # S3를 뒤져본다.
    
    # For backward comparibility
    build_version_id = 0
    visited = set()
    # TODO
    # bucket.objects.filter(Prefix=project_name+"/"+run.info.run_id)
    # 현재 3가지 케이스 존재, run_id1+build_version_id, run_id2+build_version_id, build_version_id
    # build_version_id가 모두 사라지면 교체.
    for item in bucket.objects.filter(Prefix=project_name+"/"+run.info.run_id):
        build_version_dir = item.key.rstrip("/").split("/")
        if len(build_version_dir) >= 2:
            model_version = build_version_dir[1]
            
            if model_version in visited:
                continue
            
            # run_id1의 build_version_id를 찾는 중
            # run_id2의 build_version이 보이면, 무시한다.
            # TODO와 같이 임시로 진행.
            # if len(model_version.split("_")) > 1 and model_version.split("_")[0] != run.info.run_id:
            #     visited.add(model_version)
            #     continue

            try:
                current_version_id = _get_build_version_id(model_version)
            except ValueError:
                continue
            visited.add(model_version)
            build_version_id = max(build_version_id, current_version_id)
    
    if next_bool:
        build_version_id += 1
    build_version = _make_unique_build_version(run, build_version_id)
    _run_set_tags(run, [BUILD_VERSION], [build_version])
    return build_version

def _download_specs(
    bucket,
    project_name,
    build_version,
    dst_dir: Path
):
    """
    download_spec to dst_folder
    """
    dst_dir.mkdir(exist_ok=True, parents=True)
    dst_dir_str = dst_dir.absolute().as_posix()
    
    
    for obj in bucket.objects.filter(Prefix=project_name+"/"+str(build_version)):
        bucket.download_file(
            obj.key,
            dst_dir_str + "/" + obj.key.split("/")[-1]
        )
        logging.info(f"{obj.key} download to {dst_dir_str + '/' + obj.key.split('/')[-1]}")

def _upload_specs(
    bucket,
    project_name,
    build_version,
    file_paths: List[Union[Path, None]]
):
    """
    INHOUSE_SERVING_Bucket/project_name/build_version/file_name에 업로드
    S3 key들 return
    """
    ret = []
    for file_path in file_paths:
        if not file_path:
            continue
        file_name = file_path.name
        key = "/".join([project_name, build_version, file_name])
        bucket.upload_file(
            Filename=file_path.absolute().as_posix(),
            Key=key
        )
        ret.append(file_name)
        logging.info(f"{file_path} upload to {key}")
    return ret
    
def _run_set_tags(
    run: Run,
    keys: List,
    values: List,
):
    logging.info(f"Start tagging into run {run.info.run_name} ({run.info.run_id})")
    for key, value in zip(keys, values):
        if not value:
            continue
        mlflow_client.set_tag(run.info.run_id, str(key), str(value), synchronous=False)
        logging.info(f"Set tag:: {key}: {value}")

def _run_delete_tags(
    run: Run,
    keys: List
):
    logging.info(f"Delete Tag in run {run.info.run_name} ({run.info.run_id})")
    for key in keys:
        mlflow_client.delete_tag(run.info.run_id, str(key))
        logging.info(f"Delete tag:: {key}")

### End of MCP-only adjustments.
