import os
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from requests import Response, request

from lamp_admin_cli.configure import T_STAGES
from lamp_admin_cli.settings import LAMP_CLI_LOCAL_DEV

MLBO_HOST = "http://127.0.0.1:8080" if LAMP_CLI_LOCAL_DEV else "https://api-c1-admin.letsur.ai/mlbo"


def _get_user() -> str:
    """Return the current user in a robust way.

    os.getlogin() fails in non-interactive contexts (e.g., MCP server without a
    controlling TTY). Fall back to common env vars or getpass.getuser().
    """
    try:
        return os.getlogin()
    except Exception:
        # Try common environment variables
        for key in ("LOGNAME", "USER", "LNAME", "USERNAME"):
            val = os.environ.get(key)
            if val:
                return val
        try:
            import getpass
            return getpass.getuser()
        except Exception:
            return "unknown"

class MLBOEndpoints(Enum):
    """
    METHOD, path
    """
    SEARCH_EXPERIMENT=("GET", "/experiments/search")
    GET_EXPERIMENT_BY_NAME=("GET", "/experiments/byName/{exp_name}")
    CREATE_EXPERIMENT=("POST", "/experiments")
    
    CREATE_RUN=("POST", "/experiments/{exp_id}/runs")
    GET_RUN=("GET", "/runs/{run_uuid}")
    SEARCH_RUN_BY_NAME=("GET", "/experiments/{exp_id}/runs")
    SEARCH_RUN=("GET", "/runs/search")
    
    PUT_SPECS=("PUT", "/runs/{run_uuid}")
    PATCH_SPECS=("PATCH", "/runs/{run_uuid}")
    
    GET_HISTORIES=("GET", "/histories")
    
    LIST_EXPORTS=("GET", "/exports")
    CREATE_EXPORT=("POST", "/exports")
    UPDATE_EXPORT=("PUT", "/exports/{export_id}")

    GET_RUN_EXPORT_DETAIL=("GET", "/exports/{run_export_id}")

class MLBOAPIClient:

    def request(self, endpoint: MLBOEndpoints, paths: Optional[dict] = None, params: Optional[dict] = None, json: Optional[dict] = None) -> dict:
        if not paths:
            paths = dict()
        r: Response = request(
            method=endpoint.value[0],
            url=MLBO_HOST + endpoint.value[1].format(**paths),
            params=params,
            json=json
        )
        r.raise_for_status()
        return r.json()

    def search_experiment_by_name(self, name: str):
        return self.request(MLBOEndpoints.SEARCH_EXPERIMENT, params={"name": name})
    
    def get_experiment_by_name(self, name: str):
        return self.request(MLBOEndpoints.GET_EXPERIMENT_BY_NAME, paths={"exp_name": name})
    
    def create_experiment(self, name: str):
        return self.request(MLBOEndpoints.CREATE_EXPERIMENT, params={"name": name, "created_by": _get_user()})
    
    def create_dummy_run(self, experiment_id: int, run_name: str):
        return self.request(
            MLBOEndpoints.CREATE_RUN,
            paths={"exp_id": experiment_id},
            params={"created_by": _get_user()},
            json={"name": run_name}
        )
        
    def get_run(self, run_uuid: UUID):
        return self.request(
            MLBOEndpoints.GET_RUN,
            paths={"run_uuid": run_uuid.hex},
        )

    def search_run_by_dbx_run_id(self, export_entity_id: UUID, stage: T_STAGES) -> List[Dict]:
        return self.request(
            MLBOEndpoints.SEARCH_RUN,
            params={"export_entity_id": export_entity_id.hex, "stage": stage},
        )
    
    
    def put_spec_to_run(
        self, run_uuid: UUID, specs: List[dict]
    ):
        return self.request(
            MLBOEndpoints.PUT_SPECS,
            paths={"run_uuid": run_uuid.hex},
            json={"specs": specs, "created_by": _get_user()},
        )
    
    def append_spec_to_run(self, run_uuid: UUID, specs: List[dict]):
        """
        [
            {
                "spec_type": "serving_model",
                "file_type": "metadata",
                "data": "",
                "stage": "local",
                "service": "apiServer"
            }
        ]
        """
        return self.request(
            MLBOEndpoints.PATCH_SPECS,
            paths={"run_uuid": run_uuid.hex},
            json=specs,
        )
        
    def export_run(self, history_id: int, stage: T_STAGES, export_entity_id: UUID, run_uuid: Optional[UUID] = None):
        """
        lamp-cli에선 실제 export는 MLBO를 통하지 않고 DBX에 export를 바로 하기 때문에, 
        lamp-cli에 의해 DBX로 export된 export_entity_id를 인용하여 사용.
        MLBO에 export 레코드를 만들어주기 위한 용도
        """
        params = {
            "history_id": history_id,
            "stage": stage,
            "export_entity_id": export_entity_id.hex,
            "created_by": _get_user()
        }
        if run_uuid is not None:
            params.update({"run_uuid": run_uuid.hex})

        return self.request(
            MLBOEndpoints.CREATE_EXPORT,
            params=params
        )
        
    def update_export(self, export_id: int, run_history_id: int):
        return self.request(
            MLBOEndpoints.UPDATE_EXPORT,
            paths={
                "export_id": export_id,
            },
            params={
                "apply_to_dbx": False,
            },
            json={
                "run_history_id": run_history_id,
                "updated_by": _get_user(),
            }
        )
    
    def get_histories(self, run_uuid: UUID) -> List[dict]:
        return self.request(
            MLBOEndpoints.GET_HISTORIES,
            params={"run_uuid": run_uuid.hex}
        )
        
    def search_experiment_runs(self, experiment_id: int, name: str):
        return self.request(
            MLBOEndpoints.SEARCH_RUN_BY_NAME,
            paths={"exp_id": experiment_id},
            params={"name": name}
        )
    
    def list_exports(self, run_uuid: UUID):
        return self.request(
            MLBOEndpoints.LIST_EXPORTS,
            params={"run_uuid": run_uuid.hex}
        )
    
        
    def get_run_export_detail(self, run_export_id: int):
        """
        {
        "export_entity_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "stage": "dev",
        "id": 0,
        "created_at": "2025-05-14T08:23:52.144Z",
        "created_by": "",
        "updated_at": "2025-05-14T08:23:52.144Z",
        "last_updated_by": "",
        "run_history": {
            "specs": [
            {
                "data": "",
                "file_type": "metadata",
                "spec_type": "serving_endpoint",
                "stage": "dev"
            }
            ],
            "exports": [],
            "created_by": "",
            "id": 0,
            "version": 0,
            "created_at": "2025-05-14T08:23:52.144Z"
        }
        } 
        """
        return self.request(
            MLBOEndpoints.GET_RUN_EXPORT_DETAIL,
            paths={"run_export_id": run_export_id}
        )
