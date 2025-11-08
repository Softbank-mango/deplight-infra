from inspect import isclass, isfunction
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .contextvars import request_id_contextvars
from .logger import AccessLogger
from .quota import arb_quota, should_rollback_quota
from .utils import set_request_context, where_proc_on


async def attach_id_to_request_and_response(request: Request, call_next):
    gen_id = str(uuid4())
    request.state._letsur_id = gen_id
    request_id_contextvars.set(gen_id)
    set_request_context(request)
    response = await call_next(request)
    return response


async def access_logging(request: Request, call_next):
    proc_name = where_proc_on()

    AccessLogger().start_log(request, proc_name)
    try:
        response = await call_next(request)
    except Exception as e:
        # handler 처리를 하지 않은 요청은 500 error 라고 생각하고 access log를 남긴다.
        AccessLogger().end_log(request, None, proc_name)
        raise e

    AccessLogger().end_log(request, response, proc_name)

    return response


async def finalize_quota(request: Request, call_next):
    try:
        response: Response = await call_next(request)
    except Exception as e:
        # Exception Handler에 걸리지 않은 Exception을 여기서 받는다.
        if should_rollback_quota(request):
            await arb_quota(request)
        raise e

    if should_rollback_quota(request, response):
        # Rollback
        await arb_quota(request)

    return response


BASE_MIDDLEWARES = [finalize_quota, access_logging, attach_id_to_request_and_response]
DEBUG_MIDDLEWARES = []


def include_middlewares(app: FastAPI, debug: bool = False):
    """
    먼저에 넣은 것이, 가장 먼저 실행된다.
    """
    # TODO
    # add settings.middlewares?

    if debug:
        for m in DEBUG_MIDDLEWARES:
            if isinstance(m, tuple):
                mid, args, kwargs = m
                app.add_middleware(mid, *args, **kwargs)
            if isclass(m):
                app.add_middleware(m)
            elif isfunction(m):
                app.add_middleware(BaseHTTPMiddleware, dispatch=m)

    for m in BASE_MIDDLEWARES:
        # TODO
        # consider not functional middleware
        app.add_middleware(BaseHTTPMiddleware, dispatch=m)
