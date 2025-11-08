from asyncio import iscoroutinefunction
from functools import wraps
from traceback import format_exception

from langfuse.decorators import langfuse_context, observe

from src._core.contextvars import get_current_request_id
from src._core.logger.serving_logger import ServingLogger


def langfuse_exception_handling_decorator(func):
    @observe(capture_input=False, capture_output=False)
    def handling_error(e: Exception):
        langfuse_context.update_current_observation(
            status_message="".join(format_exception(e)),
            tags=["ERROR"],
            level="ERROR",
            metadata={"serving_request_id": get_current_request_id()},
        )
        ServingLogger().info(f"Update Span For Error {e}:{get_current_request_id()}")

    if iscoroutinefunction(func):

        @observe(capture_input=False, capture_output=False)
        @wraps(func)
        async def wrapper(*args, **kwargs):  # type: ignore
            langfuse_context.update_current_trace(
                metadata={"serving_request_id": get_current_request_id()}
            )
            try:
                o = await func(*args, **kwargs)
            except Exception as e:
                handling_error(e)
                raise
            return o

    else:

        @observe(capture_input=False, capture_output=False)
        @wraps(func)
        def wrapper(*args, **kwargs):
            langfuse_context.update_current_trace(
                metadata={"serving_request_id": get_current_request_id()}
            )
            try:
                o = func(*args, **kwargs)
            except Exception as e:
                handling_error(e)
                raise
            return o

    return wrapper
