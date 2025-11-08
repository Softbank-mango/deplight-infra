import asyncio
import threading
import time
import typing

import httpx
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from uvicorn import Config, Server

from src._core.app import app as _app
from src._core.logger import ServingLogger


async def log_req_and_res_for_test(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    request_info = {
        "letsur_id": request.headers.get("_letsur_id"),
        "url": request.url,
        "start_time": start_time,
        "process_time": process_time,
    }
    ServingLogger().info(f"{request_info}")
    return response


@pytest.fixture(autouse=True, scope="session")
def app():
    _app.user_middleware = []
    _app.add_middleware(BaseHTTPMiddleware, dispatch=log_req_and_res_for_test)
    _app.middleware_stack = _app.build_middleware_stack()
    return _app


@pytest.fixture(autouse=True)
def testname(request):
    return request.node.name


@pytest.fixture
def anyio_backend():
    return ("asyncio", {"use_uvloop": True})


@pytest.fixture(scope="session")
def client(app):
    """
    Server를 직접 실행하지 않고 app 코드를 실행하는 용도.
    """
    with TestClient(app) as _client:
        yield _client


class TestServer(Server):
    @property
    def url(self) -> httpx.URL:
        protocol = "https" if self.config.is_ssl else "http"
        return httpx.URL(f"{protocol}://{self.config.host}:{self.config.port}/")

    def install_signal_handlers(self) -> None:
        # Disable the default installation of handlers for signals such as SIGTERM,
        # because it can only be done in the main thread.
        pass  # pragma: nocover

    async def serve(self, sockets=None):
        self.restart_requested = asyncio.Event()

        loop = asyncio.get_event_loop()
        tasks = {
            loop.create_task(super().serve(sockets=sockets)),
            loop.create_task(self.watch_restarts()),
        }
        await asyncio.wait(tasks)

    async def restart(self) -> None:  # pragma: no cover
        # This coroutine may be called from a different thread than the one the
        # server is running on, and from an async environment that's not asyncio.
        # For this reason, we use an event to coordinate with the server
        # instead of calling shutdown()/startup() directly, and should not make
        # any asyncio-specific operations.
        self.started = False
        self.restart_requested.set()
        while not self.started:
            await asyncio.sleep(0.2)

    async def watch_restarts(self) -> None:  # pragma: no cover
        while True:
            if self.should_exit:
                return

            try:
                await asyncio.wait_for(self.restart_requested.wait(), timeout=0.1)
            except asyncio.TimeoutError:
                continue

            self.restart_requested.clear()
            await self.shutdown()
            await self.startup()


def serve_in_thread(server: TestServer) -> typing.Iterator[TestServer]:
    thread = threading.Thread(target=server.run)
    thread.start()
    try:
        while not server.started:
            time.sleep(1e-3)
        yield server
    finally:
        server.should_exit = True
        thread.join()


@pytest.fixture(scope="session")
def server(app) -> typing.Iterator[TestServer]:
    """
    Test 실행 시 쓰는 Uvicorn Server -> 직접 통신 127.0.0.1:8100
    """
    config = Config(app=app, loop="asyncio", lifespan="off", port=8100)
    server = TestServer(config=config)
    yield from serve_in_thread(server)
