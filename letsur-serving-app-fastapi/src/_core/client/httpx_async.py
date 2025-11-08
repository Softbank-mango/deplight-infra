from typing import Annotated, Iterator

import httpx
from fastapi import Depends, Request, Response

from src._core.logger import ServingLogger

from .httpx import DefaultLimits, DefaultTimeout

DefaultLimits = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20,
)
DefaultTimeout = httpx.Timeout(timeout=120)


async def aget_httpx_client() -> Iterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        limits=DefaultLimits, timeout=DefaultTimeout
    ) as client:
        yield client


async def get_httpx_client() -> Iterator[httpx.Client]:
    with httpx.Client(limits=DefaultLimits, timeout=DefaultTimeout) as client:
        yield client


HttpxAsyncClient = Annotated[httpx.AsyncClient, Depends(aget_httpx_client)]
HttpxSyncClient = Annotated[httpx.Client, Depends(get_httpx_client)]
