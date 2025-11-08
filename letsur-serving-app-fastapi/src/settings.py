from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class ModelSettings(BaseSettings):
    ...


settings = ModelSettings()


INSTALLED_ROUTERS = [
    "src.routers.main",
]

"""
BASE_EXCEPTIONS_HANDLERS = {
    LampApplicationError: src._core._exceptions.handler.lamp_error_exception_handler,
    LampValidationError: src._core._exceptions.handler.lamp_validation_error_exception_hander,
    exceptions.RequestValidationError: src._core._exceptions.handler.req_valid_exception_hander,
}
"""

EXCEPTION_HANDLERS = {
    # "httpx.ConnectError": "src.exceptions.httpx_Invalid_url_error_handler"
}
