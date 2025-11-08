import logging
from dataclasses import dataclass
from functools import partial
from urllib.parse import quote

from celery import Celery
from celery.app.log import TaskFormatter
from celery.signals import (
    after_setup_logger,
    after_setup_task_logger,
    worker_process_init,
    worker_shutting_down,
)

from src._core.logger import (
    ServingLogger,
    _initialize_logger,
    _root_log_type_for_env,
    _serving_log_type_for_env,
    initialize_access_logger,
    root_log_format_str,
    set_formatter_timestamp_to_iso,
)
from src._core.settings import app_settings, celery_settings
from src._core.tracing import langfuse_init, trace_flush
from src._core.utils import check_setting_interface
from src._core.worker.app_init import init_app_for_async
from src._core.worker.utils import is_celery_app_need

safequote = partial(quote, safe="")


@dataclass(frozen=True, repr=True)
class CeleryConfig:
    broker_transport = "sqs"
    broker_transport_options = {
        # Long Polling
        "wait_time_seconds": 20,
        # Time sleep if no message
        "polling_interval": 1,
        "visibility_timeout": 600,
        "queue_name_prefix": celery_settings.queue_name_prefix,
        "region": celery_settings.AWS_DEFAULT_REGION,
    }
    broker_url = celery_settings.CELERY_BROKER_URL
    s3_access_key_id = celery_settings.AWS_ACCESS_KEY_ID
    s3_secret_access_key = celery_settings.AWS_SECRET_ACCESS_KEY
    s3_bucket = celery_settings.CELERY_S3_BUCKET
    s3_base_path = f"{app_settings.LAMP_STAGE}/"
    s3_region = celery_settings.AWS_DEFAULT_REGION
    s3_endpoint_url = celery_settings.CELERY_S3_ENDPOINT_URL
    s3_domain = celery_settings.CELERY_S3_DOMAIN
    result_backend = "s3://"
    task_serializer = "json"
    result_serializer = "json"
    accept_content = [
        "application/json",
        # "application/x-python-serialize"
    ]
    result_accept_content = [
        "application/json",
        # "application/x-python-serialize"
    ]
    task_track_started = True
    override_backends = {"s3": "src._core.worker.result_backend.s3.LetsurS3Backend"}
    task_ignore_result = True

    worker_log_format = root_log_format_str
    worker_task_log_format = "[%(asctime)s][%(levelname)s][TASK][%(processName)s][%(task_name)s][%(task_id)s] %(message)s"
    worker_concurrency = celery_settings.CELERY_WORKER_NUM


celery_serving_log_format = "[%(asctime)s][%(levelname)s][SERVING][%(processName)s][%(task_name)s][%(task_id)s][:%(lineno)s] %(message)s"

celery_app = Celery(
    app_settings.UNIQUE_FULL_NAME,
)
celery_app.config_from_object(
    CeleryConfig(),
)

if not is_celery_app_need():
    exit()


def initialize_serving_logger_for_worker(env_type: str, debug: bool):
    log_level = _serving_log_type_for_env[env_type] if not debug else "DEBUG"
    serving_logger = ServingLogger().get_logger()
    _initialize_logger(
        serving_logger, log_level, TaskFormatter(celery_serving_log_format)
    )
    serving_logger.propagate = False


@after_setup_logger.connect
def setup_worker_logger(
    logger: logging.Logger, loglevel, logfile, format, colorize, **kwargs
):
    log_level = _root_log_type_for_env[app_settings.LAMP_STAGE]
    logger.setLevel(log_level)


@after_setup_task_logger.connect
def setup_task_loggers(logger: logging.Logger, loglevel, **kwargs):
    # 원본 format
    # '[%(asctime)s: %(levelname)s/%(processName)s] %(task_name)s[%(task_id)s]: %(message)s'

    set_formatter_timestamp_to_iso()

    # 우리 포맷 (AccessLog로 대체)

    # initialize_root_logger(app_settings.LAMP_STAGE, app_settings.LETSUR_DEBUG)
    initialize_serving_logger_for_worker(
        env_type=app_settings.LAMP_STAGE, debug=app_settings.LETSUR_DEBUG
    )
    initialize_access_logger(init_from_worker=True)

    logger.level = logging.WARNING
    logger.propagate = False


@worker_shutting_down.connect
def worker_shutting_down_handler(sig, how, exitcode, **kwargs):
    trace_flush()


@worker_process_init.connect
def init_worker(**kwargs):
    langfuse_init()


init_app_for_async(celery_app)
check_setting_interface()
