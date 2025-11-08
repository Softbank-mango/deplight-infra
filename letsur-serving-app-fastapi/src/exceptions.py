"""
from httpx import ConnectError, RequestError

from src._core.exceptions.base import LampValidationError
from src._core.exceptions.handlers import log_traceback


async def httpx_Invalid_url_error_handler(request, exc: ConnectError):
    log_traceback()
    raise LampValidationError(message="hi")
"""
