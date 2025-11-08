from typing import Iterator

import httpx
from fastapi import Request, Response

from .utils import is_httpx_client_availiable

DefaultLimits = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20,
)
DefaultTimeout = httpx.Timeout(timeout=120)


def get_httpx_client() -> Iterator[httpx.Client]:
    with httpx.Client(limits=DefaultLimits, timeout=DefaultTimeout) as client:
        yield client
