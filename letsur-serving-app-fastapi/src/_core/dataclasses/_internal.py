from dataclasses import asdict
import time
from typing import ClassVar, Optional

from pydantic import Field, RootModel
from pydantic.dataclasses import dataclass


@dataclass
class InvocationInterface:
    """
    lamp_invocation annotate로 sync, async interface 노출 시 사용.
    """

    attr_name: ClassVar = "_ls_invocation_interface"

    use_sync: bool = True
    use_async: bool = True
    # 코드 레벨에서 정해지지 않고 App init 때 정해지기에
    # Assertion을 위해 None으로 Default 값을 바꿈.
    # use_quota: bool = False
    use_quota: Optional[bool] = None

    _generated: bool = False

    @classmethod
    def from_object_for_generate(
        cls, obj: "InvocationInterface"
    ) -> "InvocationInterface":
        d = obj.to_dict()
        d["_generated"] = True
        return cls(**d)

    def to_dict(self):
        return asdict(self)


@dataclass
class RequestCTX:
    """
    Request에 달려서 Quota를 Check하였는지 안했는지 확인하는 용도.
    +
    Letsur에서 다루는 Reqeust 정보.
    """

    attr_name: ClassVar = "_ls_requestctx"

    # For task
    is_task_async: bool = False

    # FOR QUOTA
    is_quota_endpoint: bool = False
    decr_quota: bool = (
        False  # admin url 등을 통해 들어온 요청등은 endpoint는 true여도 decr은 false일 수 있다.
    )
    already_rollback: bool = False

    ## Timestamps of requests
    # 처음 request를 받은 시간 (timestamp)
    _request_time_ts: float = Field(default_factory=lambda: time.time())

    # Task 관련. 여기서 task는 celery 의 task 뿐만 아니라 fastapi 에서 실행하는 job 역시 task의 일부이다.
    # task를 시작하는 시간 (task receive, 혹은 middleware 실행 등에 의해서 request_time 후)
    _task_start_time_ts: Optional[float] = None
    # task가 끝나는 시간
    _task_end_time_ts: Optional[float] = None

    def __json__(self):
        return RootModel[RequestCTX](**self.__dict__).model_dump_json()
