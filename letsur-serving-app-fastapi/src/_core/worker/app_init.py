import asyncio
import contextvars
from collections import defaultdict
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from functools import wraps
from inspect import iscoroutinefunction, signature
from typing import TYPE_CHECKING, Any, Callable, List, Literal, Optional, Set
from uuid import uuid4

from celery import Celery, Task
from celery._state import _task_stack
from celery.result import AsyncResult
from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.encoders import jsonable_encoder
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass as pydantic_dataclass
from starlette.datastructures import URL
from starlette.responses import JSONResponse, Response
from uvicorn._types import HTTPScope  # type: ignore

from src._core._assert import _assert
from src._core.contextvars import request_id_contextvars

from src._core.dataclasses._internal import InvocationInterface
from src._core.exceptions.base import LampApplicationError
from src._core.exceptions.handlers import get_exception_handlers
from src._core.logger import AccessLogger
from src._core.quota import (
    adecr_quota,
    rb_quota,
    should_rollback_quota,
)
from src._core.settings import app_settings
from src._core.utils import (
    get_request_context,
    set_request_context,
    set_quota_flag_to_route,
    where_proc_on,
)
from src._core.worker.middleware import (
    ExceptionRouteAppMiddleware,
    debug_response,
    error_response,
)
from src._core.worker.result_backend.dataclasses import (
    LetsurTask,
    LetsurTaskResult,
    LetsurTaskTime,
)
from src._core.worker.result_backend.s3 import LetsurS3Backend
from src._core.worker.utils import get_all_user_routers, is_async_route

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client, S3ServiceResource  # type: ignore

task_stacks = contextvars.ContextVar("task_stacks")
req_stacks = contextvars.ContextVar("req_stacks")

EXCEPTION_HANDLERS = get_exception_handlers()


class OptionalModel(BaseModel):
    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)

        for field in cls.model_fields.values():
            field.default = None

        cls.model_rebuild(force=True)


@pydantic_dataclass
class AsyncTask:
    tracking_url: str
    datetime_created: datetime = Field(
        init=False, default_factory=(lambda: datetime.now(tz=timezone.utc))
    )
    wait: int = Field(10, description="첫 요청 이후 최소 기대 대기 시간, 가장 빠른 task latency")
    timeout: int = Field(
        30, description="요청 이후 timeout만큼 시간이 지난 이후에도 task가 완료가 안되었다면 장애 상황으로 간주"
    )

    @classmethod
    def from_async_result(cls, result: AsyncResult, time: LetsurTaskTime):
        celery_backend: LetsurS3Backend = result.backend  # type: ignore
        url = celery_backend.get_public_url(task_id=result.task_id)
        return cls(tracking_url=url, wait=time.wait, timeout=time.timeout)


@dataclass
class RouteSpec:
    path: str
    endpoint: Callable
    methods: Set[str]
    responses: Optional[dict] = None
    kwargs: Optional[Any] = None


def set_current_task(func):
    """

    ::
        def make_func_to_task()
            def new_func()
                ...
                o: JSONResponse = asyncio.run(router_app(request))
                ...

    User defined endpoint 함수는 make_func_to_task에 의해 celery.task화 되며,
    비동기 실행 결과를 조작하는 로직이 래핑되어 있는 new_func로 래핑됩니다.

    new_func에서는 sync 결과와 async 결과를 동일하게 제공하기 위해,
    Task 실행 시 endpoint 함수를 직접 실행시키지 않고
    FastAPI 의 route.get_route_handler()를 활용하여 만든 request handler를 사용합니다.

    async invocations를 요청하였을 때의 Request를 모사한 Request를 hanlder 인자로 사용하여 마치  sync invocations 요청을 받았을 때와 같이 동작하도록 의도하였습니다.
    다만 def로 정의된 endpoint가 FastAPI handler에 의해 실행될 때 외부 threadpool에서 실행되게 됩니다.

    celery의 테스크 실행 중 접근 가능한 current_task는
    threading.local에 저장되어 있기 때문에, endpoint 실행 중에 current_task에 접근이 어렵습니다.

    해당 구조를 도식화 하면 다음과 같습니다.


    celery.task:
        (set current_task)
        FastAPI handler:
            endpoint (child thread):
            (empty current_task)

    해당 wrapper를 이용해서,
    celery.task 내에서 setting된 task 정보가 child thread인 endpoint 함수 내에서도 주입되도록 합니다.
    ServingLogger 사용 시 로그 내에 task_name과 task_id를 기록하기 위함 입니다.


    """
    if iscoroutinefunction(func):

        @wraps(func)
        async def wrapper(*args, **kwargs):  # type: ignore
            task: Task = task_stacks.get()
            request = req_stacks.get()
            task.request_stack.push(request)  # type: ignore
            _task_stack.push(task)
            try:
                o = await func(*args, **kwargs)
                return o
            finally:
                _task_stack.pop()
                task.request_stack.pop()  # type: ignore

    else:

        @wraps(func)
        def wrapper(*args, **kwargs):
            task: Task = task_stacks.get()
            request = req_stacks.get()
            task.request_stack.push(request)  # type: ignore
            _task_stack.push(task)
            try:
                o = func(*args, **kwargs)
                return o
            finally:
                _task_stack.pop()
                task.request_stack.pop()  # type: ignore

    return wrapper


def make_func_to_task(celery_app: Celery, route: APIRoute):
    route.dependant.call = set_current_task(route.dependant.call)
    router_app = route.get_route_handler()
    app = ExceptionRouteAppMiddleware(app=router_app, handlers=EXCEPTION_HANDLERS)

    # invocation을 기반으로 Worker 쪽에서 실행될 새로운 함수 정의
    def new_func(self: Task, scope: HTTPScope, body):
        # start
        self.backend.start_task(self.request.id)
        request_id_contextvars.set(self.request.id)
        exc = None
        request = Request(scope=scope)  # type: ignore
        request._url = URL(scope=scope)  # type: ignore
        request._body = body
        set_request_context(request)

        task_stacks.set(self)
        req_stacks.set(self.request)

        proc_name = where_proc_on()
        # access_logging 미들웨어에 대응
        AccessLogger().start_log(request, proc_name)

        loop = asyncio.get_event_loop()
        # finalize_quota 미들웨어에 대응.
        try:
            o: Response = loop.run_until_complete(app(request))
        except Exception as e:
            # Exception Handler에 걸리지 않은 Exception을 여기서 받는다.

            if app_settings.LETSUR_DEBUG:
                o = debug_response(request, e)
            else:
                o = error_response(request, e)
            exc = e
        if should_rollback_quota(request, o):
            rb_quota(request)

        # end
        if o.status_code >= 400:
            self.backend.error_task(
                self.request.id, result=LetsurTaskResult.from_response(o)
            )
        else:
            self.backend.end_task(
                self.request.id, result=LetsurTaskResult.from_response(o)
            )
        # access_logging 미들웨어에 대응
        AccessLogger().end_log(request, o, proc_name)

        if exc:
            raise exc

    new_func.__name__ = route.endpoint.__name__ + "_task"
    return celery_app.task(
        new_func, name=_get_route_full_module(route) + "_task", bind=True
    )


# Deprecated
# MLOP-372
def create_sync_endpoint(task, f, timeout=60, interval=1):
    """
    POST Invocations/sync

    #TODO
    override
    POST Invocations
    """

    @wraps(f)
    async def sync_func(*args, **kwargs):
        result = await run_in_threadpool(task.delay, *args, **kwargs)
        # TODO
        # Exception handling timeout
        ret = await run_in_threadpool(result.get, timeout=timeout, interval=interval)
        return jsonable_encoder(ret)

    sync_func.__name__ = f.__name__ + "_sync"
    sync_func.__annotations__ = f.__annotations__.copy()
    return sync_func


def create_async_post_endpoint(task: Task, f):
    """
    POST Invocations/async
    """
    scope_keys = HTTPScope.__annotations__.keys()
    letsur_task_time: LetsurTaskTime = getattr(f, LetsurTaskTime.attr_name)
    inferface: InvocationInterface = getattr(f, InvocationInterface.attr_name)
    use_quota = inferface.use_quota

    async def async_post_func(*args, **kwargs):
        request: Request = kwargs.get("_request")  # type: ignore
        ctx = get_request_context(request)
        ctx.is_task_async = True

        if use_quota:
            await adecr_quota(request)

        scope = HTTPScope(
            **{key: val for key, val in request.scope.items() if key in scope_keys}
        )
        body = await request.body()
        _assert(
            hasattr(request.state, "_letsur_id"),
            "_letsur_id must be set before creating a worker task",
        )
        task_id = getattr(request.state, "_letsur_id", str(uuid4()))

        await task.backend.init_task(task_id)
        # TODO
        # threadpool에서 실행하도록 돌렸으나, 여전히 CPU Blocking job,
        # thread cold start 이슈가 있음.
        ret: AsyncResult = task.apply_async((scope, body), task_id=task_id)

        return AsyncTask.from_async_result(ret, letsur_task_time)

    # Origin endpoint function의 interface 상속.
    inferface = InvocationInterface.from_object_for_generate(inferface)
    setattr(async_post_func, InvocationInterface.attr_name, inferface)

    async_post_func.__name__ = f.__name__ + "_async_post"
    o_sig = signature(f)
    n_sig = signature(async_post_func)

    o_params = list(o_sig.parameters.values())

    async_post_func.__signature__ = n_sig.replace(
        parameters=o_params, return_annotation=AsyncTask
    )
    async_post_func.__annotations__ = f.__annotations__
    async_post_func.__annotations__["return"] = AsyncTask

    return async_post_func


def generate_additional_responses(f):
    model_output = signature(f, follow_wrapped=False).return_annotation
    return {
        299: {
            "model": LetsurTask[model_output],
            "description": "schema of tracking_url",
        }
    }


# MLOP-372
# Deprecated
def create_async_get_endpoint(celery_app, f):
    """
    GET invocations/async
    """
    RET_CLASS = f.__annotations__["return"]
    time: LetsurTaskTime = getattr(f, LetsurTaskTime.attr_name, LetsurTaskTime())  # type: ignore

    class ModelOutput(RET_CLASS, OptionalModel):
        task: AsyncTask

    async def async_get_func(task_id: str):
        o = AsyncResult(id=task_id, app=celery_app)
        task = AsyncTask.from_async_result(o, time)
        if not o.ready():
            return ModelOutput(task=task)  # type: ignore

        if o.failed():
            raise o.result

        if o.ready():
            base_ret = o.result
            if isinstance(base_ret, JSONResponse):
                return base_ret.render()  # type: ignore
            elif isinstance(base_ret, BaseModel):
                ret = base_ret.model_dump()
            elif is_dataclass(base_ret):
                ret = asdict(base_ret)  # type: ignore
            else:
                try:
                    ret = dict(base_ret)
                except Exception:
                    ret = {"body": str(base_ret)}
            return ModelOutput(task=task, **ret)  # type: ignore

    async_get_func.__name__ = f.__name__ + "_async_get"
    async_get_func.__annotations__["return"] = ModelOutput
    return async_get_func


class InitAppWarning:
    RETURN_TYPE_HINT = "Endpoint Function must have return type hint."
    CELERY_RESULT_BACKEND = f"Only support {LetsurS3Backend.__module__+':'+LetsurS3Backend.__name__} as Celery ResultBackend"


def _get_route_full_module(route: APIRoute) -> str:
    return route.endpoint.__module__ + "." + route.endpoint.__name__


def init_app_for_async(celery_app: Celery, fast_app: Optional[FastAPI] = None):

    # 1
    # make router endpoints to task
    warning_func = defaultdict(list)
    tasks = {}

    routers = get_all_user_routers()

    for router in routers:
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            set_quota_flag_to_route(route)

    for router in routers:
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue
            if not is_async_route(route):
                continue

            tasks[_get_route_full_module(route)] = make_func_to_task(celery_app, route)

            # 0
            # check endpoint func
            if not route.endpoint.__annotations__.get("return"):
                warning_func["RETURN_TYPE_HINT"].append(_get_route_full_module(route))

    if tasks:
        # check celery_app_backend is LetsurS3
        if not isinstance(celery_app.backend, LetsurS3Backend):
            warning_func["CELERY_RESULT_BACKEND"].append(celery_app.backend.__class__)

    if warning_func:
        message = (
            InitAppWarning.RETURN_TYPE_HINT
            + "\n"
            + "\n".join(warning_func["RETURN_TYPE_HINT"])
            if warning_func.get("RETURN_TYPE_HINT")
            else ""
            + InitAppWarning.CELERY_RESULT_BACKEND
            + "\n"
            + str(warning_func["CELERY_RESULT_BACKEND"])
            if warning_func.get("CELERY_RESULT_BACKEND")
            else ""
        )

        raise LampApplicationError(message=message, extra=warning_func)

    if not fast_app:
        return

    # 2 create fastapi async router
    for router in routers:
        new_routes: List[RouteSpec] = []
        for route in router.routes:
            if not isinstance(route, APIRoute):
                continue

            if not is_async_route(route):
                continue

            path = route.path
            if router.prefix:
                path = route.path.split(router.prefix, maxsplit=1)[-1]

            # 2.1 sync api
            # MLOP-366 Deprecated
            # new_path_name = path + "/sync"
            # new_endpoint = create_sync_endpoint(
            #     tasks[_get_route_full_module(route)], route.endpoint
            # )
            # # kwargs = route.__dict__.copy()
            # # del kwargs['path']
            # # del kwargs['operation_id']
            # # del kwargs['methods']
            # # kwargs.pop("endpoint")
            # new_routes.append(
            #     RouteSpec(
            #         path=new_path_name,
            #         endpoint=new_endpoint,
            #         methods=route.methods,
            #         # TODO
            #         # kwargs=kwargs
            #     )
            # )

            # 2.2 async api get
            # MLOP-366 Deprecated
            # new_path_name = path + "/async"
            # new_endpoint = create_async_get_endpoint(celery_app, route.endpoint)
            # # kwargs = route.__dict__.copy()
            # # del kwargs['path']
            # # del kwargs['operation_id']
            # # del kwargs['methods']
            # # kwargs.pop("endpoint")
            # new_routes.append(
            #     RouteSpec(
            #         path=new_path_name,
            #         endpoint=new_endpoint,
            #         methods=["GET"],
            #         # TODO
            #         # kwargs=kwargs
            #     )
            # )

            # 2.3 async api post
            new_path_name = path + "/async"
            new_endpoint = create_async_post_endpoint(
                tasks[_get_route_full_module(route)], route.endpoint
            )
            # kwargs = route.__dict__.copy()
            # del kwargs['path']
            # del kwargs['operation_id']
            # del kwargs['methods']
            # kwargs.pop("endpoint")
            new_routes.append(
                RouteSpec(
                    path=new_path_name,
                    endpoint=new_endpoint,
                    methods=route.methods,
                    # TODO
                    # kwargs=kwargs
                    responses=generate_additional_responses(route.endpoint),
                )
            )

            # 3 delete unused sync route

        for nr in new_routes:
            router.add_api_route(
                path=nr.path,
                endpoint=nr.endpoint,
                methods=nr.methods,
                responses=nr.responses,
                # TODO
                #    **nr.kwargs
            )
