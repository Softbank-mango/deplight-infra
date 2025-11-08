import logging
import sys

from src._core._assert import _assert
from src._core.static import ACCESS_LOG_VERSION as _ACCESS_LOG_VERSION
from src._core.static import LIVENESS_PATH as _LIVENESS_PATH
from src._core.static import READINESS_PATH as _READINESS_PATH

from .access_logger import AccessLogger, InvocationAccessLogger
from .logger_utils import _convert_time_to_utc_iso8601_str
from .serving_logger import ServingLogger

_serving_log_type_for_env = {
    "dev": "DEBUG",
    "stg": "INFO",
    "prd": "INFO",
    # "local": "DEBUG",
}

_root_log_type_for_env = {
    "dev": "INFO",
    "stg": "WARNING",
    "prd": "WARNING",
    # "local": "DEBUG",
}

root_log_format_str = "[%(asctime)s][%(levelname)s][%(name)s][%(processName)s][%(threadName)s][%(pathname).30s:%(lineno)s] %(message)s"


def _initialize_logger(
    logger: logging.Logger, log_level: str, log_format: logging.Formatter
) -> None:
    logger.setLevel(level=log_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(log_format)
    logger.addHandler(handler)


def set_formatter_timestamp_to_iso():
    # Formatter에 몽키패치할 method
    def _format_logging_iso_time(self, record: logging.LogRecord, datefmt=None) -> str:
        # python의 isoformat 은 Z 형태의 형태를 지원하지 않아 수동으로 변경.
        return _convert_time_to_utc_iso8601_str(record.created)

    logging.Formatter.formatTime = _format_logging_iso_time


class EndpointFilter(logging.Filter):
    _liveness_path = _LIVENESS_PATH.lstrip("/")
    _readiness_path = _READINESS_PATH.lstrip("/")

    def filter(self, record: logging.LogRecord) -> bool:
        """
        /readiness, /liveness filter
        """
        status_code = record.args[AccessLogger.get_status_code_idx_from_format()]  # type: ignore
        path = record.args[AccessLogger.get_path_idx_from_format()]  # type: ignore

        return not (
            (status_code == 200)
            and (self._readiness_path in path or self._liveness_path in path)  # type: ignore
        )


def initialize_access_logger(init_from_worker: bool = False):
    dummy_level = "INFO"  # access log는 level을 받지 않음
    access_log_format_str = "[%(asctime)s][ACCESS]{version} %(message)s"

    if not init_from_worker:
        default_access_logger = logging.getLogger("uvicorn.access")
        if default_access_logger.handlers:
            default_access_logger.removeHandler(default_access_logger.handlers[0])

    # 원천 데이터 수집이 필요한 log는 [v1] 과 같이 대괄호로 version 표시
    invocation_access_logger = InvocationAccessLogger().get_logger()
    invocation_access_logger_format = logging.Formatter(
        access_log_format_str.format(version=f"[{_ACCESS_LOG_VERSION}]")
    )
    _initialize_logger(
        invocation_access_logger, dummy_level, invocation_access_logger_format
    )
    invocation_access_logger.propagate = False

    # 원천 데이터 수집이 필요한 log는 (v1) 과 같이 괄호로 version 표시
    access_logger = AccessLogger().get_logger()
    access_logger.addFilter(EndpointFilter())
    access_formatter = logging.Formatter(
        access_log_format_str.format(version=f"({_ACCESS_LOG_VERSION})")
    )
    _initialize_logger(access_logger, dummy_level, access_formatter)
    access_logger.propagate = False


def initialize_serving_logger(env_type: str, debug: bool):
    log_level = _serving_log_type_for_env[env_type] if not debug else "DEBUG"
    serving_log_format_str = (
        "[%(asctime)s][%(levelname)s][SERVING][%(pathname).30s:%(lineno)s] %(message)s"
    )
    serving_logger = ServingLogger().get_logger()
    serving_formatter = logging.Formatter(serving_log_format_str)
    _initialize_logger(serving_logger, log_level, serving_formatter)
    serving_logger.propagate = False


def initialize_root_logger(env_type: str, debug: bool):
    log_level = _root_log_type_for_env[env_type]
    root_logger = logging.getLogger()
    _initialize_logger(root_logger, log_level, logging.Formatter(root_log_format_str))


def initialize_logs(env_type: str, debug: bool = False):
    _assert(
        env_type in _serving_log_type_for_env, f"{env_type} is not a valid env type"
    )

    set_formatter_timestamp_to_iso()

    initialize_root_logger(env_type, debug)
    initialize_access_logger()
    initialize_serving_logger(env_type, debug)

    # k8s에서 service할 겨우 stdout 로 충분할 듯.
    # 만약 S3등에 추가 logging을 하고 싶다면 아래와 같이.
    # file_handler = logging.handlers.TimedRotatingFileHandler(f'{log_dir}', when='midnight', interval=1, backupCount=1)
    # file_handler.setFormatter(log_format)
    # logger.addHandler(file_handler)
