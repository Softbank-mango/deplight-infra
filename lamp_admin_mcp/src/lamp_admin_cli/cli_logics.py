import json
import logging
import os
from typing import Literal
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from typing import Union

import yaml
from boto3 import resource
from mlflow import MlflowClient
from mlflow.store.artifact.runs_artifact_repo import RunsArtifactRepository

from lamp_admin_cli.inhouse.cli_logics import ENDPOINT_SPEC_VALUES_TAG_KEY

from lamp_admin_cli.settings import Configure, set_env
from lamp_admin_cli.utils import get_project_dir, masking_password
from lamp_admin_cli.validation import VALID_FILE_NAME, files_validate_and_convert_path

# stress_test 모듈은 지연 import로 처리 (MCP 서버에서 gevent 충돌 방지)
def _import_stress_test():
    try:
        from lamp_admin_cli.tool.stress_test.service import (
            calculate_rps,
            locust_run,
            request_single_shot,
        )
        return calculate_rps, locust_run, request_single_shot
    except ModuleNotFoundError:
        # only installed base
        return None, None, None
logger = logging.getLogger(__name__)
#console = Console()
s3 = resource('s3')

mlflow_client = MlflowClient()


def register(
        profile: Configure,
        run_id: str,
        project_id: int,
        test_form: Union[Path, None] = None,
        signature: Union[Path, None] = None,
        report: Union[Path, None] = None,
):

    # 4. if files,
    # validation (json format, file name)
    files = files_validate_and_convert_path(
        test_form=test_form,
        signature=signature,
        report=report
    )

            
    
    # 1. run_id check
    
    
    run = mlflow_client.get_run(run_id=run_id)
    experiment = mlflow_client.get_experiment(experiment_id=run.info.experiment_id)
    
    logging.info(f"run [green]{run.info.run_name}[/green] in experiment [green]{experiment.name}[/green] ")
    
    # 2. project_id check (register model)
    
    project = mlflow_client.get_registered_model(name=str(project_id))
    
    logging.info(f"project named [green]{project.tags.get('lamp_project_name')}[/green]")
    
    # 3. register
    # Are you sure? 넣을까 말까
    
    # 이미 run이 등록된 상태면? -> 상관 없네?
    # 파일만 추가하고 싶으면? -> upload_files cli
    # Determine source path for model version
    # Default to runs:/<run_id>/model, but for in-house runs without a logged model
    # use the run's artifact root so the underlying path exists.
    # Consistent non-waiting behavior so registration returns immediately
    additioanl_kwargs = {"await_creation_for": 0}
    if run.data.tags.get(ENDPOINT_SPEC_VALUES_TAG_KEY):
        runs_uri = f'runs:/{run_id}'
    else:
        runs_uri = f'runs:/{run_id}/model'
    source_uri = RunsArtifactRepository.get_underlying_uri(runs_uri=runs_uri)

    model_version = mlflow_client.create_model_version(
        name=str(project_id),
        source=source_uri, # type: ignore
        run_id=run_id,
        **additioanl_kwargs
    )

    # upload
    # TODO
    if any(files.values()):
        _upload_files(profile, project_id, model_version.version, files)
            
    logging.info(f"Done register run_id {run_id} to lamp project_id {project_id}")
    return True
    
    

def upload_files(
        profile: Configure,
        project_id: int,
        model_version: int,
        test_form: Union[Path, None] = None,
        signature: Union[Path, None] = None,
        report: Union[Path, None] = None,
):
    # model_version 있는지 확인
    mlflow_model_version = mlflow_client.get_model_version(name=str(project_id), version=str(model_version))
    files = files_validate_and_convert_path(
        test_form=test_form,
        signature=signature,
        report=report
    )
    _upload_files(
        profile,
        project_id,
        mlflow_model_version.version,
        files
    )
    logging.info(f"Done")
    return True


def _upload_files(
        profile: Configure,
        project_id,
        model_version: int,
        files: dict,
):
    """
    LAMP_AI_S3_Bucket/projects/pid/model_version/VALID_FILE_NAME[test_form.json|signature.json|report.pdf]에 업로드
    """
    logging.info("Upload files to LAMP S3 Bucket")
    bucket = profile.LAMP_ENVIRONMENT.CONF.LAMP_S3_REPOSITORY
    bucket = s3.Bucket(bucket)
    for n, _f in files.items():
        if not _f:
            continue
        key = _get_dst_lamp_file(project_id, model_version, n)
        bucket.upload_file(
            _f.resolve().as_posix(),
            key
        )
        logging.info(f"Upload [green]{_f.name}[/green] to [green]{bucket.name}/{key}[/green]")

def _download_files(
        profile: Configure,
        project_id,
        model_version: str,
        dst_dir: Path
):
    dst_dir.mkdir(exist_ok=True, parents=True)
    dst_dir_str = dst_dir.absolute().as_posix()
    logging.info("Download files from LAMP S3 Bucket")
    bucket = profile.LAMP_ENVIRONMENT.CONF.LAMP_S3_REPOSITORY
    bucket = s3.Bucket(bucket)
    for obj in  bucket.objects.filter(Prefix=f"projects/{project_id}/{model_version}"):
        bucket.download_file(
            obj.key,
            dst_dir_str + "/" + obj.key.split("/")[-1]
        )

    
def _get_dst_lamp_file(project_id, model_version, file_type: Literal["test-form", "signautre", "report"]):
    return f'projects/{project_id}/{model_version}/{VALID_FILE_NAME[file_type]}'


def download_files_for_project(
    profile: Configure,
    pid: str = "",
    mv: str = "",
):
    bucket = profile.LAMP_ENVIRONMENT.CONF.LAMP_S3_REPOSITORY
    bucket = s3.Bucket(bucket) # type: ignore
    dst_dir =  get_project_dir().joinpath(Path(pid+ "/" + str(mv)))
    if not list(bucket.objects.filter(Prefix=f"projects/{pid}/{mv}")):
        logging.info(f"No files in a given project")
        return
    _download_files(profile, pid, mv, dst_dir)
    return True


def copy_run(
        src_profile: Configure,
        project_id: int,
        model_version: int,
        dst_profile: Configure,
):

    # 1. Check src project, model version
    set_env(src_profile)

    o_mv = mlflow_client.get_model_version(name=str(project_id), version=model_version) # type: ignore
    o_run = mlflow_client.get_run(run_id=o_mv.run_id) # type: ignore
    o_experiment = mlflow_client.get_experiment(experiment_id=o_run.info.experiment_id)

    o_bucket = s3.Bucket(name=src_profile.LAMP_ENVIRONMENT.CONF.DATABRICKS_S3_BUCKET)
    o_artifact_prefix = o_run.info.artifact_uri.split("databricks/")[1] # type: ignore
    o_artifacts = o_bucket.objects.filter(
        Prefix=src_profile.LAMP_ENVIRONMENT.CONF.DATABRICKS_S3_PREFIX + '/' + o_artifact_prefix
    )
    n_bucket = s3.Bucket(name=dst_profile.LAMP_ENVIRONMENT.CONF.DATABRICKS_S3_BUCKET)
    
    # 2. copy run (except artifact)
    
    set_env(dst_profile)
    
    logging.info("migrate experiment")
    n_experiemnt = mlflow_client.get_experiment_by_name(name=o_experiment.name)
    if not n_experiemnt:
        logging.info(f"Can not find experiment name [green]{o_experiment.name}[/green], create new one")
        n_experiemnt = mlflow_client.create_experiment(name=o_experiment.name, tags=o_experiment.tags)
        n_experiemnt = mlflow_client.get_experiment_by_name(name=o_experiment.name)
    logging.info(f"experiment {n_experiemnt.name} is ready") # type: ignore
    
    logging.info("migrate run")
    
    n_tags = o_run.data.tags
    n_tags.update({
        "letsur_copied.origin_env": str(src_profile.LAMP_ENVIRONMENT.val), 
        "letsur_copied.origin_run_id": o_run.info.run_id}
    )
    n_run = mlflow_client.create_run(
        experiment_id=n_experiemnt.experiment_id, # type: ignore
        tags=n_tags,
        run_name=o_run.info.run_name
    )
    nrun_id = n_run.info.run_id
    params = o_run.data.params
    #metrics는 일단 생략
    _inputs = o_run.inputs.dataset_inputs
    
    for key, val in params.items():
        mlflow_client.log_param(run_id=nrun_id, key=key, value=val)

    mlflow_client.log_inputs(run_id=nrun_id, datasets=_inputs)
    mlflow_client.set_terminated(run_id=nrun_id)
    
    logging.info(f"run {n_run.info.run_name} is copied")
    
    
    # 3. Get artifact path
    
    logging.info(f"migrating artifacts")
    
    for o_file in o_artifacts:
        n_key = _get_dst_key_for_artifacts(
            o_file.key,
            n_experiemnt.experiment_id, # type: ignore
            nrun_id,
            src_profile.LAMP_ENVIRONMENT.CONF.DATABRICKS_S3_PREFIX,
            dst_profile.LAMP_ENVIRONMENT.CONF.DATABRICKS_S3_PREFIX
            )
        copy_source = {'Bucket': o_bucket.name, 'Key': o_file.key}
        n_bucket.copy(copy_source, n_key) # type: ignore
    
    logging.info("artifacts migration done")


    logging.info(f"[green]Done[/green]\n urls: {dst_profile.LAMP_ENVIRONMENT.CONF.DATABRICKS_HOST}/ml/experiments/{n_experiemnt.experiment_id}/runs/{nrun_id}") # type: ignore

    # 5. return dst_profile run_id
    return True

    
def _get_dst_key_for_artifacts(o_key, n_experiment_id, n_run_id, src_prefix, dst_prefix):
    # o_key example
    # src_prefix/mlflow-tracking/e_id/run_id/artifacts/model/file
    
    o_key = o_key.split(src_prefix)[1].lstrip('/').split('/')
    
    # [mlflow-t.., e_id, run_id, ...]
    
    o_key[1] = n_experiment_id
    o_key[2] = n_run_id
    n_key = '/'.join([dst_prefix, *o_key])
    return n_key


###
# stress-test

def stress_test(
    profile: Configure,
    project_id: int,
    data: Path,
    interval: int,
    user_steps: tuple,
    show_log: bool,
    output_dir: Union[Path, None] = None,
):
    with open(data, 'r', encoding="utf-8") as f:
        data = json.load(f)
    
    project = mlflow_client.get_registered_model(name=str(project_id))
    lamp_project_name = project.tags.get('lamp_project_name')
    
    logging.info(f"Project : [green]{lamp_project_name}[/green]")
    logging.info(f"Monitor Model Server in {profile.LAMP_ENVIRONMENT.CONF.DATABRICKS_HOST}/ml/endpoints/{project_id}")
    logging.info(f"Request Single shot to check server")
    ret, lat = request_single_shot(
        host=profile.LAMP_ENVIRONMENT.CONF.DATABRICKS_HOST,
        token=profile.DATABRICKS_TOKEN,
        post_url=f"/serving-endpoints/{project_id}/invocations",
        data=data, # type: ignore
    )
    logging.info(json.dumps(ret, indent=2))
    logging.info(f"Single shot Latency: [green]{lat}[/green]")
    
    # 1. make dir
    base = Path.cwd()
    path_dir = base.joinpath(Path(f"lamp_{profile.LAMP_ENVIRONMENT.repr_v}_model_{project_id}"))
    if output_dir:
        path_dir = output_dir
    if not path_dir.exists():
        logging.info(f"Create directory [green]{path_dir.as_posix()}[/green] to save reports")
        path_dir.mkdir()
    elif path_dir.is_file():
        logging.info(f"Directory [red]{path_dir.as_posix()}[/red] where the report will be saved is not appropriate.")
        x = uuid4()
        path_dir = base.joinpath(Path(str(x)))
        logging.info(f"Instead of, create directory [green]{path_dir.as_posix()}[/green] to save reports")
    
    # for window system -> ":" replcae to "-"
    prefix = Path(datetime.now().isoformat(timespec="minutes").replace(":", "-"))
    

    
    # 2. setup for stress test (locust)
    logging.info("Start Stress Test")
    logging.info(f"Monitor Model Server at {profile.LAMP_ENVIRONMENT.CONF.DATABRICKS_HOST}/ml/endpoints/{project_id}")
    locust_run(
        host=profile.LAMP_ENVIRONMENT.CONF.DATABRICKS_HOST,
        token=profile.DATABRICKS_TOKEN,
        post_url=f"/serving-endpoints/{project_id}/invocations",
        data=data, # type: ignore
        _range=range(*user_steps),
        interval=interval,
        path_dir=path_dir,
        prefix=prefix,
        is_shell_log=show_log,
    )

    logging.info("Finish Stress Test")
    logging.info("Start Caculate guaranteed RPS")

    # 3 analysis
    bounds, guarnteeds = calculate_rps(
        Path((path_dir / prefix).as_posix() + "_stats_history.csv"),
    )

    # Latency 추가
    logging.info(f"[red]Maximum RPS[/red]: {bounds[0]} [Response/s] Latency: {bounds[1].round(3)} \[ms]")
    logging.info(f"[green]Guaranteed RPS[/green]: {guarnteeds[0]} [Response/s] Latency: {guarnteeds[1].round(3)} \[ms]")
    
    # 4. save test summary 

    summary = {
        "info": {
                "user": os.getlogin(),
                "profile_name": profile.name,
                "lamp_environment": profile.LAMP_ENVIRONMENT.repr_v,
                "LAMP_project_id": project_id,
                "LAMP_project_name": lamp_project_name,
                "execution_datetime": datetime.now().isoformat()
                },
        "result": {
            "output_dir": output_dir.absolute().as_posix(), # type: ignore
            "MaxRPS": float(bounds[0].round(3)),
            "LatencyAtMaxRPS": float(bounds[1].round(3)),
            "GuarnteedRPS": float(guarnteeds[0].round(3)),
            "LatencyAtGuarnteedRPS": float(guarnteeds[1].round(3))
        }
    }
    
    with open((path_dir / prefix).as_posix() + "_summary.yaml", "w") as f:
         yaml.safe_dump(summary, f, encoding="utf-8")
    logging.info(f"Save summary [green]{(path_dir / prefix).as_posix() + '_summary.yaml'}[/green]")
    logging.info("Done")
    return True
