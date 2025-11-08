from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone
from starlette.datastructures import Headers
from fastapi import Request


def _get_task_id(request: Request) -> Optional[str]:
    return getattr(request.state, "_letsur_id")


def _get_client_addr_from_header(headers: Headers):
    return (
        headers["x-forwarded-for"].split(",")[0]
        if headers.get("x-forwarded-for")
        else "internal"
    )


def _convert_time_to_utc_iso8601_str(current_time: float) -> str:
    return (
        datetime.fromtimestamp(current_time, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )
