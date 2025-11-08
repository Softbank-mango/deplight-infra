from typing import Annotated, Dict, Generic, List, NoReturn, Optional, TypeVar

from fastapi import BackgroundTasks, Body, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, NameEmail
from pydantic.dataclasses import dataclass


### Letsur Headers
class _LetsurJwtHeadersModel(BaseModel):
    """
    Letsur Inhouse Cluster 서비스 매시 (ISTIO)에서 내려줄 수 있는 요청자 정보 Header들
    (https://github.com/letsur-dev/helm-charts/blob/8a8add8ef1e56682c5b9284ca1a2ed1ce205a347/charts/letsur-common-model/values.yaml#L159)
    """

    __pydantic_extra__: Dict[str, str]

    pid: Optional[str] = Field(alias="x-jwt-claim-pid", default=None)
    email: Optional[NameEmail] = Field(alias="x-jwt-claim-email", default=None)

    model_config = ConfigDict(extra="ignore")


async def _get_jwt_headers(req: Request) -> _LetsurJwtHeadersModel:
    headers = {key: val for key, val in req.headers.items()}
    return _LetsurJwtHeadersModel(**headers)  # type: ignore


LetsurJwtHeaders = Annotated[
    Optional[_LetsurJwtHeadersModel], Depends(_get_jwt_headers)
]


### Letsur Invocations Body for LAMP FE
ModelInputType = TypeVar("ModelInputType")
ModelOutputType = TypeVar("ModelOutputType")


class InferInputs(BaseModel, Generic[ModelInputType]):
    inputs: List[ModelInputType]


class InferOutputs(BaseModel, Generic[ModelOutputType]):
    predictions: List[ModelOutputType]


class LampBodyBaseModel(BaseModel):
    """
    lamp_invocation와 같이 사용.
    모델의 단일 입출력을 산정한다.
    """

    ...


@dataclass
class LampBodyDataClass:
    """
    dataclass 사용 시 해당 class 사용.
    """

    ...


### Letsur
T = TypeVar("T")
InlineBody = Annotated[T, Body()]
InlineEmbedBody = Annotated[T, Body(embed=True)]


async def _func_kwargs(req: Request) -> NoReturn:
    ...


Kwargs = Annotated[Optional[Dict], Depends(_func_kwargs)]


async def _req(req: Request) -> Request:
    return req


async def _res(res: Response) -> Response:
    return res


async def _bt(bt: BackgroundTasks) -> BackgroundTasks:
    return bt


_Request = Annotated[Optional[Request], Depends(_req)]
_Response = Annotated[Optional[Response], Depends(_res)]
_BackgroundTasks = Annotated[Optional[BackgroundTasks], Depends(_bt)]
