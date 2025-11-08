import typing
import inspect
import html
import traceback

from typing import Callable, Any, Coroutine
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse, HTMLResponse
from starlette.exceptions import HTTPException
from starlette.types import (
    HTTPExceptionHandler,
)
from starlette._utils import is_async_callable  # type: ignore
from starlette.concurrency import run_in_threadpool
from starlette._exception_handler import (
    ExceptionHandlers,  # type: ignore
    StatusHandlers,  # type: ignore
    _lookup_exception_handler,  # type: ignore
)
from starlette.middleware.errors import (
    LINE,
    STYLES,
    TEMPLATE,
    FRAME_TEMPLATE,
    CENTER_LINE,
    JS,
)

RouteApp = Callable[[Request], Coroutine[Any, Any, Response]]


def wrap_route_app_handling_exceptions(app: RouteApp, conn: Request) -> RouteApp:
    exception_handlers: ExceptionHandlers
    status_handlers: StatusHandlers

    try:
        exception_handlers, status_handlers = conn.scope["starlette.exception_handlers"]
    except KeyError:
        exception_handlers, status_handlers = {}, {}

    async def wrapped_app(request: Request) -> Response:
        try:
            return await app(request)
        except Exception as exc:
            handler = None

            if isinstance(exc, HTTPException):
                handler = status_handlers.get(exc.status_code)

            if handler is None:
                handler = _lookup_exception_handler(exception_handlers, exc)

            if handler is None:
                raise exc

            handler = typing.cast(HTTPExceptionHandler, handler)
            if is_async_callable(handler):
                response = await handler(conn, exc)
            else:
                response = await run_in_threadpool(handler, conn, exc)
            return response  # type: ignore

    return wrapped_app


class ExceptionRouteAppMiddleware:
    def __init__(
        self,
        app: RouteApp,
        handlers: typing.Mapping[
            typing.Any, typing.Callable[[Request, Exception], Response]
        ]
        | None = None,
        debug: bool = False,
    ) -> None:
        self.app = app
        self.debug = debug  # TODO: We ought to handle 404 cases if debug is set.
        self._status_handlers: StatusHandlers = {}
        self._exception_handlers: ExceptionHandlers = {
            HTTPException: self.http_exception,
        }
        if handlers is not None:
            for key, value in handlers.items():
                self.add_exception_handler(key, value)

    def add_exception_handler(
        self,
        exc_class_or_status_code: int | type[Exception],
        handler: typing.Callable[[Request, Exception], Response],
    ) -> None:
        if isinstance(exc_class_or_status_code, int):
            self._status_handlers[exc_class_or_status_code] = handler
        else:
            assert issubclass(exc_class_or_status_code, Exception)
            self._exception_handlers[exc_class_or_status_code] = handler

    async def __call__(self, request: Request) -> Response:

        request.scope["starlette.exception_handlers"] = (
            self._exception_handlers,
            self._status_handlers,
        )
        return await wrap_route_app_handling_exceptions(self.app, request)(request)

    def http_exception(self, request: Request, exc: Exception) -> Response:
        assert isinstance(exc, HTTPException)
        if exc.status_code in {204, 304}:
            return Response(status_code=exc.status_code, headers=exc.headers)
        return PlainTextResponse(
            exc.detail, status_code=exc.status_code, headers=exc.headers
        )


### starlette.middleware.errors


def format_line(index: int, line: str, frame_lineno: int, frame_index: int) -> str:
    values = {
        # HTML escape - line could contain < or >
        "line": html.escape(line).replace(" ", "&nbsp"),
        "lineno": (frame_lineno - frame_index) + index,
    }

    if index != frame_index:
        return LINE.format(**values)
    return CENTER_LINE.format(**values)


def generate_frame_html(frame: inspect.FrameInfo, is_collapsed: bool) -> str:
    code_context = "".join(
        format_line(
            index,
            line,
            frame.lineno,
            frame.index,  # type: ignore[arg-type]
        )
        for index, line in enumerate(frame.code_context or [])
    )

    values = {
        # HTML escape - filename could contain < or >, especially if it's a virtual
        # file e.g. <stdin> in the REPL
        "frame_filename": html.escape(frame.filename),
        "frame_lineno": frame.lineno,
        # HTML escape - if you try very hard it's possible to name a function with <
        # or >
        "frame_name": html.escape(frame.function),
        "code_context": code_context,
        "collapsed": "collapsed" if is_collapsed else "",
        "collapse_button": "+" if is_collapsed else "&#8210;",
    }
    return FRAME_TEMPLATE.format(**values)


def generate_html(exc: Exception, limit: int = 7) -> str:
    traceback_obj = traceback.TracebackException.from_exception(
        exc, capture_locals=True
    )

    exc_html = ""
    is_collapsed = False
    exc_traceback = exc.__traceback__
    if exc_traceback is not None:
        frames = inspect.getinnerframes(exc_traceback, limit)
        for frame in reversed(frames):
            exc_html += generate_frame_html(frame, is_collapsed)
            is_collapsed = True

    # escape error class and text
    error = (
        f"{html.escape(traceback_obj.exc_type.__name__)}: "
        f"{html.escape(str(traceback_obj))}"
    )

    return TEMPLATE.format(styles=STYLES, js=JS, error=error, exc_html=exc_html)


def generate_plain_text(exc: Exception) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def debug_response(request: Request, exc: Exception) -> Response:
    accept = request.headers.get("accept", "")

    if "text/html" in accept:
        content = generate_html(exc)
        return HTMLResponse(content, status_code=500)
    content = generate_plain_text(exc)
    return PlainTextResponse(content, status_code=500)


def error_response(request: Request, exc: Exception) -> Response:
    return PlainTextResponse("Internal Server Error", status_code=500)
