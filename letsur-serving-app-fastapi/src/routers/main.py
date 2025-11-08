from typing import Callable, Literal, Optional, TypedDict, Union

from fastapi import APIRouter, Request, Response

from src._core import ServingLogger
from src._core.dataclasses import (
    InlineBody,
    InlineEmbedBody,
    LetsurJwtHeaders,
    _Request,
    _Response,
    InferInputs,
    InferOutputs,
)
from src._core.decorators import lamp_invocation
from src._core.exceptions.base import LampApplicationError, LampValidationError
from src._core.quota import decr_quota
from src.dataclasses import ModelInput, ModelOutput

router = APIRouter()


@router.post("/invocations")
@lamp_invocation(
    use_sync=True,
    use_async=True,
    wait=5,
    timeout=10,
    use_lamp_test_ui=False,
)
def invocations(model_input: ModelInput, jwt_header: LetsurJwtHeaders) -> ModelOutput:
    ServingLogger().info("hello world")
    return ModelOutput()


# @router.post("/invocations_deprecated_example")
# @lamp_invocation(
#     # use_lamp_test_ui 필드는 Databricks Serving Spec때문에 강제된 것으로 다음 버전에서 deprecated됩니다.
#     # 직접 inputs, predictions Model을 wrapping해서 사용하시길 바랍니다.
#     # src._core.dataclass.base:InferInputs , InferOutputs 클래스를 사용하시면 편하게 개선할 수 있습니다.
#     use_lamp_test_ui=False,
# )
# def invocations_deprecated_example(model_input: InferInputs[ModelInput], jwt_header: LetsurJwtHeaders) -> InferOutputs[ModelOutput]:
#     ServingLogger().info("hello world")
#     return InferOutputs(predictions=[ModelOutput()])
