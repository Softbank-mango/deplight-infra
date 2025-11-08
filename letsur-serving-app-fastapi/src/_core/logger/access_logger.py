import logging
import time

from typing import Optional, Any
from fastapi import Request, Response

from .logger_base import LoggerBase
from .logger_utils import (
    _get_task_id,
    _get_client_addr_from_header,
    _convert_time_to_utc_iso8601_str,
)

from src._core.dataclasses._internal import RequestCTX
from src._core.settings import app_settings
from src._core._assert import _assert

_invocation_logger_process_types = {"app", "worker"}

# utils에서 가져올 수 없기 때문에 (circular error 의 위험) 직접 method 사용
def _get_request_context(request: Request) -> RequestCTX:
    return getattr(request.state, RequestCTX.attr_name)


class InvocationAccessLogger(LoggerBase):
    logger_name = "letsur.invocation"
    logger = logging.getLogger(logger_name)
    log_message_format = (
        "{proc_name}\t{flow_name}\t{use_quota}\t"
        "{request_time}\t{task_start_time}\t{task_end_time}\t{client_addr}\t"
        "{request_method}\t{status_code}\t{hostname}\t{uri_path}\t{task_id}\t"
        "{total_latency}\t{invocation_time}"
    )

    nil = "-"

    @staticmethod
    def _get_flow_name(
        ctx: RequestCTX, proc_name: str, is_start: bool, in_error: bool = False
    ) -> str:
        # FLOW_NAME = ["START", "END", "TASK_CREATED", "TASK_RECEIVED"]
        #
        # sync task:
        # app:
        #    START -> END
        #
        # Worker task:
        # app:
        #    START -> TASK_CREATED
        # worker:
        #    TASK_RECEIVED -> END
        is_worker = proc_name == "worker"
        if is_start:
            return "START(TASK_RECEIVED)" if is_worker else "START"
        else:
            # end 상황에서, 실제로 END LOG가 발생하는 경우
            # 1. 모든 error 상황 -> 어떠한 요청이든 error가 발생하면 error를 response 하고 마무리한다.
            # 2. worker 에서 찍는 end log는 무조건 마무리 상황이다.
            # 3. ctx.is_task_async flag가 false인 경우는 app server에서 직접 task를 수행하고 있는 case로 end log 필요
            if in_error or is_worker or not ctx.is_task_async:
                return "END"
            else:
                # ctx.is_task_async == True && is_worker == False && in_error == False
                return "END(TASK_CREATED)"

    def start_log(self, request: Request, proc_name: str):
        task_id = _get_task_id(request)
        if task_id is None:
            _assert(False, "task_id must be set before executing the start_log")
            task_id = self.nil

        _assert(
            proc_name in _invocation_logger_process_types,
            f"{proc_name} not in {_invocation_logger_process_types}",
        )
        ctx = _get_request_context(request)

        _kwargs = {
            "proc_name": proc_name,
            "flow_name": self._get_flow_name(
                ctx=ctx, proc_name=proc_name, is_start=True
            ),
            "use_quota": self.nil,
            "request_time": _convert_time_to_utc_iso8601_str(ctx._request_time_ts),
            "task_start_time": _convert_time_to_utc_iso8601_str(
                ctx._task_start_time_ts  # type: ignore
            ),
            "task_end_time": self.nil,
            "client_addr": _get_client_addr_from_header(request.headers),
            "request_method": request.method,
            "status_code": self.nil,
            "hostname": request.url.hostname,
            "uri_path": request.url.path,
            "task_id": task_id,
            "total_latency": self.nil,
            "invocation_time": self.nil,
        }

        # 반드시 남아야하는 로그이므로 critical level 로 남긴다.
        self.logger.critical(self.log_message_format.format(**_kwargs))

    def end_log(self, request: Request, response: Optional[Response], proc_name: str):
        task_id = _get_task_id(request)
        if task_id is None:
            _assert(False, "task_id must be set before executing the start_log")
            task_id = self.nil

        _assert(
            proc_name in _invocation_logger_process_types,
            f"{proc_name} not in {_invocation_logger_process_types}",
        )
        ctx = _get_request_context(request)
        in_error_state = not response or response.status_code >= 400

        _kwargs = {
            "proc_name": proc_name,
            "flow_name": self._get_flow_name(
                ctx=ctx, proc_name=proc_name, is_start=False, in_error=in_error_state
            ),
            "use_quota": str(ctx.is_quota_endpoint).lower(),
            "request_time": _convert_time_to_utc_iso8601_str(ctx._request_time_ts),
            "task_start_time": _convert_time_to_utc_iso8601_str(
                ctx._task_start_time_ts  # type: ignore
            ),
            "task_end_time": _convert_time_to_utc_iso8601_str(ctx._task_end_time_ts),  # type: ignore
            "client_addr": _get_client_addr_from_header(request.headers),
            "request_method": request.method,
            "status_code": response.status_code
            if response
            else 500,  # response 가 없다면 error 상황이므로 모두 500으로 처리한다.
            "hostname": request.url.hostname,
            "uri_path": request.url.path,
            "task_id": task_id,
            "total_latency": ctx._task_end_time_ts - ctx._request_time_ts,  # type: ignore
            "invocation_time": ctx._task_end_time_ts - ctx._task_start_time_ts,  # type: ignore
        }

        # 반드시 남아야하는 로그이므로 critical level 로 남긴다.
        self.logger.critical(self.log_message_format.format(**_kwargs))


class AccessLogger(LoggerBase):
    logger_name = "letsur.access"
    logger = logging.getLogger(logger_name)
    invocation_logger = InvocationAccessLogger()
    log_message_format_str = '%s - "%s %s %s HTTP/%s" %d %s %.5f'
    router_endpoints: dict[str, Any] = {}
    excluded_router_endpoints: dict[str, Any] = {}

    @classmethod
    def get_path_idx_from_format(cls) -> int:
        return 3

    @classmethod
    def get_status_code_idx_from_format(cls) -> int:
        return 5

    @classmethod
    def add_router_endpoint(cls, methods: set[str], router_endpoint: str):
        if router_endpoint in cls.excluded_router_endpoints:
            return

        for m in methods:
            if m not in cls.router_endpoints:
                cls.router_endpoints[m] = set()
            cls.router_endpoints[m].add(router_endpoint)
            cls.router_endpoints[m].add(app_settings.URL_ROOT_PATH + router_endpoint)

    def _access_log(self, request: Request, response: Optional[Response]):
        ctx = _get_request_context(request)
        args = [
            _get_client_addr_from_header(request.headers),
            request.method,
            request.url.hostname,
            request.url.path,
            request.scope["http_version"],
            response.status_code if response else 500,
            _get_task_id(request),
            ctx._task_end_time_ts - ctx._task_start_time_ts,  # type: ignore
        ]
        self.logger.info(self.log_message_format_str, *args)

    def _is_registered_endpoint(self, request: Request, proc_name: str) -> bool:
        # worker 에서 진행하는 모든 task는 registered endpoint로 취급한다.
        return proc_name == "worker" or request.url.path in self.router_endpoints.get(
            request.method, []
        )

    def start_log(self, request: Request, proc_name: str):
        _assert(self.invocation_logger is not None)
        ctx = _get_request_context(request)
        ctx._task_start_time_ts = time.time()

        if self._is_registered_endpoint(request, proc_name):
            self.invocation_logger.start_log(request, proc_name)

        # do not log at start if the endpoint is not in router

    def end_log(self, request: Request, response: Optional[Response], proc_name: str):
        _assert(self.invocation_logger is not None)
        ctx = _get_request_context(request)
        ctx._task_end_time_ts = time.time()

        if self._is_registered_endpoint(request, proc_name):
            self.invocation_logger.end_log(request, response, proc_name)
        else:
            self._access_log(request, response)
