import sys
import importlib
import json
import os

from typing import Optional

from fastapi import FastAPI

from dotenv import load_dotenv
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent.parent.resolve()


def import_module_from_path(path: Path):
    try:
        module_path = path.relative_to(PROJECT_DIR).with_suffix("")
        module_name = ".".join(module_path.parts)
        return importlib.import_module(module_name)
    except Exception as e:
        print(f"[!] Failed to import {path}: {e}")
        return e


def get_description(path: Path) -> str:
    return path.read_text()


def write_openapi(path: Path, openapi: dict, indent=2):
    with open(path, "w") as f:
        json.dump(openapi, f, indent=indent, ensure_ascii=False)


def get_openapi_dict(description: Optional[str] = None) -> dict:

    # .env .env.core resolve
    sys.path.append(str(PROJECT_DIR))

    env_path = PROJECT_DIR.joinpath(".env").resolve()
    core_env_path = PROJECT_DIR.joinpath(".env.core").resolve()

    load_dotenv(core_env_path)
    load_dotenv(env_path)

    # Issue-#45
    # LETSUR_DEBUG = False
    os.environ["LETSUR_DEBUG"] = "False"

    app_path = PROJECT_DIR.joinpath("src/_core/app.py")

    app_module = import_module_from_path(app_path)

    if isinstance(app_module, Exception):
        raise ValueError(
            f"App Init에 실패하였습니다. .env, .env.core 파일을 확인해주세요.\n{app_module}"
        )

    app: FastAPI = app_module.app

    if description:
        app.description = description

    return app.openapi()
