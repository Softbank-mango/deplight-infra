import traceback
from types import FunctionType
from typing import Dict

from fastapi import FastAPI, exceptions, responses
from fastapi.encoders import jsonable_encoder

from src._core import ServingLogger
from src._core.exceptions.base import LampApplicationError, LampValidationError
from src._core.utils import get_module

try:
    from src.settings import EXCEPTION_HANDLERS as _USER_EXCEPTION_HANDLERS
except ImportError as e:
    ServingLogger().warning("Can't get src.settings.EXCEPTION_HANDLERS, set it empty")
    _USER_EXCEPTION_HANDLERS = {}

# @app.middleware("http")
# async def exception_handler(request, call_next):
#     try:
#         return await call_next(request)
#     except Exception as exc:
#         ServingLogger().error(exc.with_traceback())
#         return responses.JSONResponse(
#             content={"detail": str(exc), "extra": ""}, status_code=500
#         )


def log_traceback():
    tb = traceback.format_exc()
    ServingLogger().error(tb)


async def lamp_error_exception_handler(request, exc: LampApplicationError):
    log_traceback()
    return responses.PlainTextResponse(content=str(exc), status_code=500)


async def lamp_validation_error_exception_hander(request, exc: LampValidationError):
    return responses.JSONResponse(
        content={"message": exc.message, "extra": jsonable_encoder(exc.extra)},
        status_code=exc.status_code,
    )


async def req_valid_exception_hander(request, exc: exceptions.RequestValidationError):
    return await lamp_validation_error_exception_hander(
        request,
        LampValidationError(
            message=exc.errors()[0]["type"],
            extra=jsonable_encoder(exc.errors(), include=("type", "msg", "loc")),
        ),
    )


BASE_EXCEPTIONS_HANDLERS = {
    LampApplicationError: lamp_error_exception_handler,
    LampValidationError: lamp_validation_error_exception_hander,
    exceptions.RequestValidationError: req_valid_exception_hander,
}


def include_excpetion_hander(app: FastAPI):
    app.exception_handlers.update(BASE_EXCEPTIONS_HANDLERS)

    # User Exception Handler
    USER_EXCEPTION_HANDLERS = _get_user_exception_handlers()
    app.exception_handlers.update(USER_EXCEPTION_HANDLERS)


def get_exception_handlers() -> dict:
    EXCEPTION_HANDLERS = BASE_EXCEPTIONS_HANDLERS.copy()
    EXCEPTION_HANDLERS.update(_get_user_exception_handlers())
    return EXCEPTION_HANDLERS


def _get_user_exception_handlers() -> Dict[Exception, FunctionType]:
    user_exception_handlers = {}
    for key, val in _USER_EXCEPTION_HANDLERS.items():
        _key = None
        if isinstance(key, Exception):
            _key = key
        elif isinstance(key, str):
            _key = get_module(key)
        else:
            raise ValueError(f"Can not get such Exception {key}: {val}")

        if isinstance(val, str):
            user_exception_handlers[_key] = get_module(val)
        elif isinstance(val, FunctionType):
            user_exception_handlers[_key] = val
        else:
            raise ValueError(f"Can not get such Exception Hanlder {key}: {val}")
    return user_exception_handlers
