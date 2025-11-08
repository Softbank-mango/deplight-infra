import os
from dataclasses import dataclass
from enum import Enum
from typing import Literal, Union, get_args, Optional, Type

import yaml
import logging

from .utils import _configure_init, _get_configure_paths, masking_password

LAMP_DEFAULT_PROFILE = os.environ.get('LAMP_DEFAULT_PROFILE', 'default')
LAMP_CLI_LOCAL_DEV = os.environ.get("LAMP_CLI_LOCAL_DEV", False)

# Prefer workspace-local config when LAMP_CONF_DIR is set; fall back to home.
CONF_DIR, CONF_FILE = _configure_init()
#console = Console()


class BasePublicConfigure():
    LAMP_S3_REPOSITORY: str
    DATABRICKS_S3_BUCKET: str
    DATABRICKS_S3_PREFIX: str
    DATABRICKS_HOST: str
    
    INHOUSE_SERVING_REPOSITORY: str
    INHOUSE_SERVING_HOST: str
    
class _CONF_DEV(BasePublicConfigure):
    LAMP_S3_REPOSITORY = 'letsur-ai-lamp-s3-dev'
    DATABRICKS_S3_BUCKET = 'databricks-workspace-stack-aa0ff-bucket'
    DATABRICKS_S3_PREFIX = 'singapore-prod/3662097480022968.jobs'
    DATABRICKS_HOST = 'https://dbc-3e212767-46ad.cloud.databricks.com'
    
    INHOUSE_SERVING_REPOSITORY = 'letsur-serving-models-dev'
    INHOUSE_SERVING_HOST = 'https://api-dev-c1.letsur.ai'

class _CONF_STG(BasePublicConfigure):
    LAMP_S3_REPOSITORY = 'letsur-ai-lamp-s3-stg'
    DATABRICKS_S3_BUCKET = 'databricks-workspace-stack-37cc7-bucket'
    DATABRICKS_S3_PREFIX = 'singapore-prod/6232191226368536.jobs'
    DATABRICKS_HOST = 'https://dbc-f3048f8d-8575.cloud.databricks.com'

    INHOUSE_SERVING_REPOSITORY = 'letsur-serving-models-prd'
    INHOUSE_SERVING_HOST = 'https://api-stg-c1.letsur.ai'

class _CONF_PRD(BasePublicConfigure):
    LAMP_S3_REPOSITORY = 'letsur-ai-lamp-s3-prd'
    DATABRICKS_S3_BUCKET = 'databricks-workspace-stack-9b1f2-bucket'
    DATABRICKS_S3_PREFIX = 'singapore-prod/4676012774434797.jobs'
    DATABRICKS_HOST = 'https://dbc-1f90ab2e-8d80.cloud.databricks.com'
    
    INHOUSE_SERVING_REPOSITORY = 'letsur-serving-models-prd'
    INHOUSE_SERVING_HOST = 'https://api-c1.letsur.ai'
    
    
class _CONF_LOCAL_DEV(BasePublicConfigure):
    LAMP_S3_REPOSITORY = 'lamp-dev'
    DATABRICKS_S3_BUCKET = 'databricks-workspace-stack-aa0ff-bucket'
    DATABRICKS_S3_PREFIX = 'singapore-prod/3662097480022968.jobs'
    DATABRICKS_HOST = 'http://127.0.0.1:5000'
    
    INHOUSE_SERVING_REPOSITORY = 'ai-dev'
    INHOUSE_SERVING_HOST = 'https://api-dev-c1.letsur.ai'
    
class _CONF_LOCAL_STG(BasePublicConfigure):
    LAMP_S3_REPOSITORY = 'lamp-stg'
    DATABRICKS_S3_BUCKET = 'databricks-workspace-stack-aa0ff-bucket'
    DATABRICKS_S3_PREFIX = 'singapore-prod/3662097480022968.jobs'
    DATABRICKS_HOST = 'http://127.0.0.1:5001'
    
    INHOUSE_SERVING_REPOSITORY = 'ai-stg'
    INHOUSE_SERVING_HOST = 'https://api-stg-c1.letsur.ai'
    
class _CONF_LOCAL_PRD(BasePublicConfigure):
    LAMP_S3_REPOSITORY = 'lamp-prd'
    DATABRICKS_S3_BUCKET = 'databricks-workspace-stack-aa0ff-bucket'
    DATABRICKS_S3_PREFIX = 'singapore-prod/3662097480022968.jobs'
    DATABRICKS_HOST = 'http://127.0.0.1:5001'
    
    INHOUSE_SERVING_REPOSITORY = 'ai-prd'
    INHOUSE_SERVING_HOST = 'https://api-c1.letsur.ai'

T_STAGES = Literal['dev', 'stg', 'prd']

class LAMPStage(Enum):
    DEV = ('dev', 'develop', _CONF_DEV, _CONF_LOCAL_DEV)
    STG = ('stg', 'staging', _CONF_STG, _CONF_LOCAL_STG)
    PRD = ('prd', 'production', _CONF_PRD, _CONF_LOCAL_PRD)
    
    def __init__(self, val, repr_v, conf: Type[BasePublicConfigure], local_dev_conf: Type[BasePublicConfigure]) -> None:
        self.val = val
        self.repr_v = repr_v
        self.CONF = conf
        if LAMP_CLI_LOCAL_DEV:
            self.CONF = local_dev_conf
    
    @classmethod
    def all_values(cls):
        return [c.val for c in cls]
    
    @classmethod
    def from_value(cls, val: T_STAGES):
        for c in cls:
            if c.val == val:
                return c
        raise ValueError("No proper value")
    
    def __str__(self) -> str:
        return self.val
    
@dataclass
class Configure:
    _profile_name: str
    LAMP_ENVIRONMENT: LAMPStage
    _LAMP_ENVIRONMENT_TYPE: T_STAGES
    DATABRICKS_TOKEN: str
    GITHUB_AUTH_TOKEN: str = ""

    @classmethod
    def from_dict(
                  cls,
                  _profile_name: str,
                  LAMP_ENVIRONMENT: T_STAGES,
                  DATABRICKS_TOKEN: str,
                  GITHUB_AUTH_TOKEN: Optional[str] = None,
                ):
        _LAMP_ENVIRONMENT_TYPE = LAMP_ENVIRONMENT
        LAMP_ENVIRONMENT_instance = LAMPStage.from_value(LAMP_ENVIRONMENT)
        return Configure(_profile_name=_profile_name, LAMP_ENVIRONMENT=LAMP_ENVIRONMENT_instance, _LAMP_ENVIRONMENT_TYPE=_LAMP_ENVIRONMENT_TYPE, DATABRICKS_TOKEN=DATABRICKS_TOKEN, GITHUB_AUTH_TOKEN=GITHUB_AUTH_TOKEN or "")

    @property
    def name(self):
        return self._profile_name

    def __str__(self):
        return "[green]{profile_name}[/green]\n \
\tGITHUB_AUTH_TOKEN: {gtoken}\n \
\tLAMP_ENVIRONMENT: {lenv}\n \
\t\tLAMP_S3_REPOSITORY: {lenv_lamp_s3_repo}\n \
\t\tDATABRICKS_S3_BUCKET: {lenv_dbx_s3_repo}\n \
\t\tDATABRICKS_HOST: {lenv_dbx_host}\n \
\t\tDATABRICKS_TOKEN: {dtoken}\n \
\t\tINHOUSE_SERVING_REPOSITORY: {lenv_inhouse_s3_repo}\n \
                ".format(
                    profile_name=self._profile_name,
                    lenv = self.LAMP_ENVIRONMENT.repr_v,
                    lenv_lamp_s3_repo=self.LAMP_ENVIRONMENT.CONF.LAMP_S3_REPOSITORY,
                    lenv_dbx_s3_repo=self.LAMP_ENVIRONMENT.CONF.DATABRICKS_S3_BUCKET,
                    lenv_dbx_host=self.LAMP_ENVIRONMENT.CONF.DATABRICKS_HOST,
                    lenv_inhouse_s3_repo=self.LAMP_ENVIRONMENT.CONF.INHOUSE_SERVING_REPOSITORY,
                    dtoken=masking_password(self.DATABRICKS_TOKEN),
                    gtoken=masking_password(self.GITHUB_AUTH_TOKEN),
                )
    
    def warning_if_empty(self):
        p = ""
        if not self.GITHUB_AUTH_TOKEN:
            p += "[red]No GITHUB AUTH TOKEN[/red]\nEndpoint Spec Validation 및 Generation 기능을 사용할 수 없습니다."
        if p:
            logging.info(p)

        
def list_configure_keys(path=".lamp"):
    _, CONF_FILE = _get_configure_paths(path=path)
    with open(CONF_FILE, 'r') as f:
        dict_confs = yaml.safe_load(f)
    return list(dict_confs.keys())

def show_configure_list(path=".lamp"):
    _, CONF_FILE = _get_configure_paths(path=path)
    with open(CONF_FILE, 'r') as f:
        dict_confs = yaml.safe_load(f)
    for profile_name, conf in dict_confs.items():
        c = Configure.from_dict(_profile_name=profile_name, **conf)
        logging.info(str(c))
    return True

def get_configure(profile_name="default", path=".lamp") -> Configure:
    _, CONF_FILE = _get_configure_paths(path=path)
    try:
        with open(CONF_FILE, 'r') as f:
            dict_profile = yaml.safe_load(f)[profile_name]
        profile = Configure.from_dict(_profile_name=profile_name, **dict_profile)
    except Exception as exc:
        logging.info(f"""
                        [red]Can't get credential of profile [green]{profile_name}[/green].
                        Please run credential configure.
                        Configure credentials via MCP client tools
                        """)
        raise ValueError(f"Profile '{profile_name}' not found or invalid") from exc
    profile.warning_if_empty()
    return profile

def set_env(profile: Configure):
    envs_keys = ["DATABRICKS_TOKEN", "LAMP_ENVIRONMENT.CONF.DATABRICKS_HOST"]
    for keys in envs_keys:
        v = profile
        env_key_list = keys.split(".")
        for k in env_key_list:
            v = getattr(v, k)
        if v:
            os.environ[k] = v # type: ignore
        else:
            logging.info(f"""
                            [red]Can't get envvar {env_key_list[-1]}
                            """)
    os.environ.setdefault("MLFLOW_TRACKING_URI", "databricks")
    
    if LAMP_CLI_LOCAL_DEV:
        os.environ.setdefault("MLFLOW_TRACKING_URI", os.environ.get("DATABRICKS_HOST", ""))


def get_configure_and_set_env(profile_name="default", path=".lamp"):
    profile = get_configure(profile_name=profile_name, path=path)
    set_env(profile)
    return profile
