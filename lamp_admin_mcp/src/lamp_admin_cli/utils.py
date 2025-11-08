import inspect
import os
import logging
import typing as t
from datetime import datetime
from functools import lru_cache, update_wrapper
from pathlib import Path

import yaml
from packaging.version import Version, parse

logger = logging.getLogger(__name__)

@lru_cache
def _get_configure_paths(path=".lamp"):
    CONF_DIR = Path.home().joinpath(path)
    CONF_FILE = CONF_DIR.joinpath('credentials')
    return CONF_DIR, CONF_FILE

@lru_cache
def _get_log_paths(path=".lamp"):
    CONF_DIR = Path.home().joinpath(path)
    CONF_FILE = CONF_DIR.joinpath('log')
    return CONF_DIR, CONF_FILE
    

def _configure_init(path=".lamp"):
    CONF_DIR, CONF_FILE = _get_configure_paths(path=path)
    CONF_DIR.mkdir(exist_ok=True)
    CONF_FILE.touch()
    return CONF_DIR, CONF_FILE

def _log_init():
    LOG_DIR, LOG_FILE = _get_log_paths(path=".lamp")
    LOG_DIR.mkdir(exist_ok=True)
    LOG_FILE.touch()
    LOCAL_LOG_DIR = Path(f'./log')
    LOCAL_LOG_FILE = LOCAL_LOG_DIR.joinpath(datetime.now().strftime("%Y%m%d"))
    LOCAL_LOG_DIR.mkdir(exist_ok=True)
    LOCAL_LOG_FILE.touch()
    return LOG_FILE, LOCAL_LOG_FILE


def masking_password(val):
    l = len(val)
    s = l - ( l // 3)
    return ('*' * (s)) + val[s:]

def get_project_dir():
    return Path.cwd()

def is_serving_app_dir(path: Path) -> bool:
    x = path / Path(".copier")
    y = path / Path(".env.core")
    return x.exists() and x.is_dir() and y.exists() and y.is_file()


def get_serving_app_version(path: Path) -> Version:
    """
    # .copier-answers.yaml
    LAMP_PROJECT_NAME: qa-model
    LETSUR_ML_PROJECT_NAME: qa-model
    _commit: v0.3.1
    _src_path: https://github.com/letsur-dev/letsur-serving-app-fastapi.git
    
    
    path: Project Dir path
    """
    x = path / Path(".copier") / Path(".copier-answers.yaml")
    assert x.exists() and x.is_file(), ".copier-answers.yaml 파일이 없습니다."
    
    with open(x, mode="r") as f:
        ans = yaml.safe_load(f)
    return parse(ans.get("_commit", "v0.1.0"))
    
    

def set_last_ctx(func):
    # No-op in MCP-only branch
    return func


# Click-related helpers removed in MCP-only branch
