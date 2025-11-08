import sys
import json
import warnings
from functools import lru_cache
from importlib import import_module
from typing import List, Literal

from fastapi import APIRouter, Request
from fastapi.routing import APIRoute

from src._core.dataclasses._internal import InvocationInterface, RequestCTX
from src._core.logger import ServingLogger, AccessLogger

try:
    from src.settings import INSTALLED_ROUTERS
except ImportError as e:
    ServingLogger().warning("Can't get src.settings.INSTALLED_ROUTERS, set it empty")
    INSTALLED_ROUTERS = []


def get_module(path: str):
    try:
        m = import_module(path)
    except ModuleNotFoundError as e:
        p = import_module(path.rsplit(".", maxsplit=1)[0])
        m = getattr(p, path.rsplit(".", maxsplit=1)[1])
    return m


def get_all_user_routers() -> List[APIRouter]:
    routers = []
    for module_path in INSTALLED_ROUTERS:
        m = import_module(module_path)
        router = getattr(m, "router", None)
        if router and isinstance(router, APIRouter):
            routers.append(router)
        else:
            ServingLogger().debug(f"Can not import router class of {module_path}")

    return routers


def add_user_routers(app):
    for router in get_all_user_routers():
        # delete unsued sync route
        del_idx = []
        for idx, route in enumerate(router.routes):
            if not isinstance(route, APIRoute):
                warnings.warn(
                    f"API Route가 아닌 router가 존재합니다. {route}\n 유저 라우터에 추가하지 않습니다."
                )
                continue
            AccessLogger.add_router_endpoint(route.methods, route.path)
            set_quota_flag_to_route(route)
            if not is_sync_route(route):
                del_idx.append(idx)

        for idx in reversed(del_idx):
            del router.routes[idx]

        app.include_router(router)


def _get_route_interface(route: APIRoute) -> InvocationInterface:
    ret = getattr(route.endpoint, InvocationInterface.attr_name, None)
    assert ret, f"{route.endpoint}에 lamp_invocation decorator가 설정되지 않았습니다."
    return ret


def is_sync_route(route: APIRoute):
    interface = _get_route_interface(route)
    if interface._generated:
        # delete 되지 않도록.
        return True
    return interface.use_sync


def is_async_route(route: APIRoute):
    interface = _get_route_interface(route)
    return interface.use_async


def is_quota_count_route(route: APIRoute):
    interface = _get_route_interface(route)
    return interface.use_quota


def set_quota_flag_to_route(route: APIRoute):
    interface = _get_route_interface(route)
    if interface.use_quota is not None:
        # 이미 세팅된 케이스
        return

    if route.path == "/invocations":
        from .settings import app_settings

        interface.use_quota = app_settings.LAMP_INVOCATION_USE_QUOTA
    else:
        interface.use_quota = False


@lru_cache
def where_proc_on() -> Literal["app", "worker"]:
    if "celery" in sys.argv[0]:
        return "worker"
    else:
        return "app"


def check_setting_interface():
    routers = get_all_user_routers()
    for router in routers:
        for route in router.routes:
            if not isinstance(route, APIRoute):
                warnings.warn(
                    f"API Route가 아닌 router가 존재합니다. {route}\n lamp_incovations interface 검사를 하지 않습니다."
                )
                continue
            assert (
                _get_route_interface(route).use_quota is not None
            ), f" {route} Endpoint에 Quota 사용 유무가 설정이 되지 않았습니다."


def set_request_context(request: Request):
    x = getattr(request.state, RequestCTX.attr_name, None)

    # request context is already set
    if isinstance(x, RequestCTX):
        return

    if not x:
        y = RequestCTX()
        setattr(request.state, RequestCTX.attr_name, y)
    else:
        # if set the request context as string
        if isinstance(x, str):
            x = json.loads(x)

        assert isinstance(x, dict), f"RequestCTX is not a str or dict: {x}"

        y = RequestCTX(**x)
        setattr(request.state, RequestCTX.attr_name, y)


def get_request_context(request: Request) -> RequestCTX:
    return getattr(request.state, RequestCTX.attr_name)
