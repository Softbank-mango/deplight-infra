import json
from pathlib import Path
from typing import List
from uuid import UUID

from requests import HTTPError
import logging

from lamp_admin_cli.inhouse.mlbo.client import MLBOAPIClient
from lamp_admin_cli.settings import LAMP_CLI_LOCAL_DEV, Configure

mlbo_client = MLBOAPIClient()


def create_mlbo_run(profile: Configure, exp_name: str, run_name: str, export_entity_id: str):
    ### MLBO
    logging.info(f"Create run in MLBO")
    try:
        mlbo_exp = mlbo_client.get_experiment_by_name(name=exp_name)
        logging.info(f"Found existing experiment {exp_name} in MLBO")
    except HTTPError as e:
        # exp가 없을 때, 404 에러 발생
        if e.response.status_code == 404:
            mlbo_exp = mlbo_client.create_experiment(name=exp_name)
            logging.info(f"Created new experiment {exp_name} in MLBO")
        else:
            raise e
    
    runs = mlbo_client.search_experiment_runs(experiment_id=mlbo_exp.get("id"), name=run_name)
    if len(runs) == 1:
        mlbo_run = runs[0]
    else:
        mlbo_run = mlbo_client.create_dummy_run(experiment_id=mlbo_exp.get("id"), run_name=run_name)
    # dbx에 run 만든 것 표시
    # Ensure we have the fresh run data to retrieve correct IDs
    mlbo_run = mlbo_client.get_run(run_uuid=UUID(mlbo_run.get("uuid")))
    latest_history_id = mlbo_run.get("latest_history", {}).get("id")
    run_uuid = UUID(mlbo_run.get("uuid"))
    mlbo_run_export = mlbo_client.export_run(
        history_id=latest_history_id,
        stage=profile.LAMP_ENVIRONMENT.val,
        export_entity_id=UUID(export_entity_id),
        run_uuid=run_uuid,
    )
    
    logging.info(f"DONE Create run in MLBO")
    if LAMP_CLI_LOCAL_DEV:
        logging.info(json.dumps(mlbo_run))
        logging.info(json.dumps(mlbo_run_export))
    return mlbo_run


def upload_serving_model_spec_to_mlbo(profile: Configure, run_id: str, docker_compose: List[Path], env_files: List[Path]):
    mlbo_runs = mlbo_client.search_run_by_dbx_run_id(
        export_entity_id=UUID(run_id),
        stage=profile.LAMP_ENVIRONMENT.val
    )
    assert mlbo_runs and len(mlbo_runs) == 1
    run_uuid = mlbo_runs[0]["uuid"]
    last_exports = mlbo_client.list_exports(run_uuid=UUID(run_uuid))
    last_export = None
    for e in last_exports:
        if e.get("export_entity_id", "") == UUID(run_id):
            last_export = e
            break
    
    
    specs = []
    for d in docker_compose:
        with open(d, mode="r", encoding="utf-8") as f:
            specs.append({
              "spec_type": "serving_model",
              "file_type": "docker-compose",
              "data": f.read(),
              "stage": profile.LAMP_ENVIRONMENT.val,
            })
    for d in env_files:
        service_name = "apiServer"
        for n in ["apiServer", "worker", "triton"]:
            if n in d.name: 
                service_name = n
        with open(d, mode="r", encoding="utf-8") as f:
            specs.append({
              "spec_type": "serving_model",
              "file_type": "env",
              "data": f.read(),
              "stage": profile.LAMP_ENVIRONMENT.val,
              # .env.service.stage
              "service": service_name
            })
    mlbo_run = mlbo_client.append_spec_to_run(
        run_uuid=UUID(run_uuid),
        specs=specs
    )
    # export 하는 척
    if last_export:
        ret = mlbo_client.update_export(
            export_id=last_export.get("id"),
            run_history_id=mlbo_run.get("latest_history", {}).get("id")
        )
    else:
        ret = mlbo_client.export_run(
            history_id=mlbo_run.get("latest_history", {}).get("id"),
            stage=profile.LAMP_ENVIRONMENT.val,
            export_entity_id=UUID(run_id)
        )
    return ret # RunExportDetail
        
def upload_serving_endpoint_spec_to_mlbo(profile: Configure, run_id: str, metadata_files: List[Path], values_files: List[Path], env_files: List[Path]):
    mlbo_runs = mlbo_client.search_run_by_dbx_run_id(
        export_entity_id=UUID(run_id),
        stage=profile.LAMP_ENVIRONMENT.val
    )
    assert mlbo_runs and len(mlbo_runs) == 1
    run_uuid = mlbo_runs[0].get("uuid")
    last_exports = mlbo_client.list_exports(run_uuid=UUID(run_uuid))
    last_export = None
    for e in last_exports:
        if e.get("export_entity_id", "") == UUID(run_id):
            last_export = e
            break
    
    
    specs = []
    for d in metadata_files:
        with open(d, mode="r", encoding="utf-8") as f:
            specs.append({
              "spec_type": "serving_endpoint",
              "file_type": "metadata",
              "data": f.read(),
              "stage": profile.LAMP_ENVIRONMENT.val,
            })
    for d in values_files:
        with open(d, mode="r", encoding="utf-8") as f:
            specs.append({
              "spec_type": "serving_endpoint",
              "file_type": "values",
              "data": f.read(),
              "stage": profile.LAMP_ENVIRONMENT.val,
            })
    for d in env_files:
        service_name = "apiServer"
        for n in ["apiServer", "worker", "triton"]:
            if n in d.name:
                service_name = n
        with open(d, mode="r", encoding="utf-8") as f:
            specs.append({
              "spec_type": "serving_endpoint",
              "file_type": "env",
              "data": f.read(),
              "stage": profile.LAMP_ENVIRONMENT.val,
              # .env.service.stage
              "service": service_name
            })
    mlbo_run = mlbo_client.append_spec_to_run(
        run_uuid=UUID(run_uuid),
        specs=specs
    )
    # export 하는 척
    if last_export:
        ret = mlbo_client.update_export(
            export_id=last_export.get("id"),
            run_history_id=mlbo_run.get("latest_history", {}).get("id")
        )
    else:
        ret = mlbo_client.export_run(
            history_id=mlbo_run.get("latest_history", {}).get("id"),
            stage=profile.LAMP_ENVIRONMENT.val,
            export_entity_id=UUID(run_id)
        )
    return ret # RunExportDetail
