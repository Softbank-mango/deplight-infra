from contextvars import ContextVar

from typing_extensions import Optional

request_id_contextvars: ContextVar[Optional[str]] = ContextVar(
    "request_id", default=None
)


def get_current_request_id():
    return request_id_contextvars.get()
