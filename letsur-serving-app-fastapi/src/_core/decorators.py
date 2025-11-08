import warnings
from asyncio import iscoroutinefunction
from collections import OrderedDict
from functools import wraps
from inspect import Parameter, isclass, signature
from typing import Annotated

# from uvicorn._types import HTTPScope
from fastapi import BackgroundTasks, Request, Response

from src._core.exceptions.base import LampApplicationError
from src._core.tracing import IS_LANGFUSE_INSTALLED

from .dataclasses._internal import InvocationInterface
from .dataclasses.base import (
    InferInputs,
    InferOutputs,
    LampBodyBaseModel,
    LampBodyDataClass,
    _BackgroundTasks,
    _Request,
    _Response,
)
from .quota import adecr_quota, decr_quota

if IS_LANGFUSE_INSTALLED:
    from .tracing import langfuse_exception_handling_decorator


def lamp_invocation(
    use_sync: bool = True,
    use_async: bool = True,
    wait: int = 10,
    timeout: int = 30,
    use_observe: bool = False,
    use_lamp_test_ui: bool = False,
    # use_quota: bool = False,
):
    """
    endpoint 작성에 도움을 주는 decorator

    Example:
    ::
        @router.post("/invocations")
        @lamp_invocation(
            use_lamp_test_ui=False,
            use_sync=True,
            use_async=True,
            wait=5,
            timeout=10,
        )
        def invocations(
            model_input: ModelInput, jwt_header: LetsurJwtHeaders
        ) -> ModelOutput:
            ...

    Args:
        use_lamp_test_ui (bool, optional): Defaults to False. \n
            LAMP에서 사용 시 구 serving cluster인 databricks, mlflow의 입출력 방식과 호환을 맞추기 위한 flag. \n
            LampBodyBaseModel | LampBodyDataClass를 상속 받아 만든 ModelInput, ModelOutput를 endpoint 함수의 타입 힌트로 사용하고, \n
            이 flag를 True로 할 시 실제 API Server에선 ModeInput, ModelOutput을 wrapping한 InferInputs | InferOutputs를 입출력으로 쓴다..
            ### Deprecated 예정
        use_sync (bool, optional): Defaults to True. \
            원 endpoint를 sync 방식으로 제공할지 말지 결정하는 flag.
        use_async (bool, optional): Defaults to True. \
            원 endpoint를 async 방식으로 제공할지 말지 결정하는 flag.
        wait (int, optional): Defaults to 10. \
            async 방식으로 제공할 때 함수의 실행 완료 최소 시간.
        timeout (int, optional): Defaults to 30. \
            async 방식으로 제공할 때 client에게 최대로 기다릴 수 있도록 제공하는 시간.
        use_quota (bool, optional): Defaults to False \
            해당 API 사용으로 모델 사용량을 차감할지 말지 결정하는 Flag, 사용량을 총 사용 시 사용이 불가능해질 수 있음.
        use_observe (bool, optional): Defaults to False \
            langfuse가 설치 / 환경변수가 세팅된 App에서만 동작. 해당 함수를 Observe하여 Trace를 만듭니다.
    """

    # use_quota = True

    def setting_decorator(func):
        setattr(
            func,
            InvocationInterface.attr_name,
            InvocationInterface(
                use_sync=use_sync,
                use_async=use_async,
                # use_quota=use_quota,
            ),
        )
        if use_async:
            from src._core.worker.result_backend.dataclasses import LetsurTaskTime

            setattr(
                func,
                LetsurTaskTime.attr_name,
                LetsurTaskTime(wait=wait, timeout=timeout),
            )

        # User Invocation 함수에 Request, Response Args를 별도로 삽입.
        o_sig = signature(func)
        func.__annotations__["_request"] = Request
        func.__annotations__["_response"] = Response
        func.__annotations__["_background_tasks"] = BackgroundTasks
        # kwargs 내 _request, _response가 Request, Response 객체
        if iscoroutinefunction(func):

            @wraps(func)
            async def wrapper(*args, _request: _Request = None, _response: _Response = None, _background_tasks: _BackgroundTasks = None, **kwargs):  # type: ignore
                o = await func(*args, **kwargs)
                return o

        else:

            @wraps(func)
            def wrapper(*args, _request: _Request = None, _response: _Response = None, _background_tasks: _BackgroundTasks = None, **kwargs):  # type: ignore
                o = func(*args, **kwargs)
                return o

        n_sig = signature(wrapper, follow_wrapped=False)
        n_params = list(n_sig.parameters.values())
        n_params = n_params[1:4]  # KEYWORD_ONLY
        arg_stack = []
        kwargs_stack = []
        # What we want
        # _request, _Response kw를 KEYWORD_ONLY에 넣기.
        # 순서

        for _, v in o_sig.parameters.items():
            if v.kind in (
                Parameter.POSITIONAL_ONLY,
                Parameter.POSITIONAL_OR_KEYWORD,
                Parameter.VAR_POSITIONAL,
            ):
                arg_stack.append(v)
            elif v.kind in (Parameter.VAR_KEYWORD, Parameter.KEYWORD_ONLY):
                kwargs_stack.append(v)

        arg_stack.extend(n_params)
        arg_stack.extend(kwargs_stack)

        wrapper.__signature__ = n_sig.replace(parameters=arg_stack)  # type: ignore
        wrapper.__annotations__ = func.__annotations__

        return wrapper

    def quota_decorator(func):
        i: InvocationInterface = getattr(func, InvocationInterface.attr_name)
        if iscoroutinefunction(func):

            @wraps(func)
            async def wrapper(*args, **kwargs):  # type: ignore
                request: Request = kwargs.get("_request")  # type: ignore
                if i.use_quota:
                    await adecr_quota(request)
                o = await func(*args, **kwargs)
                return o

        else:

            @wraps(func)
            def wrapper(*args, **kwargs):
                request: Request = kwargs.get("_request")  # type: ignore
                if i.use_quota:
                    decr_quota(request)
                o = func(*args, **kwargs)
                return o

        return wrapper

    def lamp_test_ui_decorator(func):
        input_key = None
        o_sig = signature(func)
        o_params = OrderedDict(o_sig.parameters.items())
        return_val = o_sig.return_annotation
        for key, val in func.__annotations__.items():
            if isinstance(val, Annotated):  # type: ignore
                # TODO
                # Get Depend?
                continue
            elif isclass(val) and (
                issubclass(val, LampBodyBaseModel) or issubclass(val, LampBodyDataClass)
            ):
                if key == "return":
                    func.__annotations__[key] = InferOutputs[val]
                    return_val = InferOutputs[val]
                elif input_key is None:
                    func.__annotations__[key] = InferInputs[val]
                    o_params[key] = o_params[key].replace(annotation=InferInputs[val])
                    input_key = key
                elif input_key:
                    raise ValueError("Only one Lamp Body args supported")

        func.__signature__ = o_sig.replace(
            parameters=tuple(o_params.values()), return_annotation=return_val
        )

        if iscoroutinefunction(func):

            @wraps(func)
            async def wrapper(*args, **kwargs):  # type: ignore
                kwargs[input_key] = kwargs[input_key].inputs[0]  # type: ignore
                o = await func(*args, **kwargs)
                return InferOutputs(predictions=[o])

        else:

            @wraps(func)
            def wrapper(*args, **kwargs):
                kwargs[input_key] = kwargs[input_key].inputs[0]  # type: ignore
                o = func(*args, **kwargs)
                return InferOutputs(predictions=[o])

        return wrapper

    def decorator(func):
        decorators = [setting_decorator, quota_decorator]

        # if use_quota:
        #     decorators.append(quota_decorator)

        if use_lamp_test_ui:
            warnings.warn(
                "Defrecated Warning::\n'use_lamp_test_ui=True' 필드는 다음 마이너 버전 업데이트 (version > v0.3.0) 부터 제거됩니다.",
                stacklevel=2,
            )
            decorators.append(lamp_test_ui_decorator)

        if use_observe:
            if IS_LANGFUSE_INSTALLED:
                decorators.append(langfuse_exception_handling_decorator)
            else:
                raise LampApplicationError(
                    "'use_observe=True' : langfuse package 모듈 임포트가 실패하여 observe 기능을 사용할 수 없습니다."
                )

        ret = func
        for dec in decorators:
            ret = dec(ret)

        return ret

    return decorator
