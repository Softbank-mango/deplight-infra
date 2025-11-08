import json
from datetime import datetime, timezone
from typing import Dict, Generic, Literal, Mapping, Optional, TypeVar, ClassVar

from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass
from starlette.responses import JSONResponse, Response

LetsurTaskState = Literal["START", "END", "ERROR"]

ModelOutputType = TypeVar("ModelOutputType")


@dataclass
class LetsurTaskResult(Generic[ModelOutputType]):
    status_code: int
    header: Optional[Mapping[str, str]]
    body: Optional[ModelOutputType | dict | bytes]

    @classmethod
    def from_response(cls, response: Response):
        try:
            body = json.loads(response.body)
        except (json.JSONDecodeError, TypeError):
            body = response.body
        return cls(status_code=response.status_code, header=response.headers, body=body)


@dataclass
class LetsurTaskTime:
    attr_name: ClassVar = "_ls_task_time"

    wait: int = Field(10, description="첫 요청 이후 최소 기대 대기 시간 (sec), 가장 빠른 task latency")
    timeout: int = Field(
        30,
        description="요청 이후 timeout만큼 시간 (sec)이 지난 이후에도 task가 완료가 안되었다면 client에선 장애 상황으로 간주",
    )


class LetsurTask(BaseModel, Generic[ModelOutputType]):
    state: LetsurTaskState
    datetime_updated: datetime = Field(
        default_factory=(lambda: datetime.now(tz=timezone.utc))
    )
    result: Optional[LetsurTaskResult[ModelOutputType]] = None
