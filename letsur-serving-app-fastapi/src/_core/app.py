from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated, Any, Optional, Type

from boto3 import s3
from botocore.exceptions import ClientError
from fastapi import Depends, FastAPI, Header, Request, exceptions, responses, status

from src._core.exceptions import include_excpetion_hander
from src._core.exceptions.base import LampApplicationError
from src._core.logger import ServingLogger, initialize_logs
from src._core.middleware import include_middlewares
from src._core.settings import app_settings
from src._core.static import LIVENESS_PATH, READINESS_PATH
from src._core.tracing import trace_flush

from .utils import add_user_routers, check_setting_interface
from .worker.app_init import init_app_for_async
from .worker.utils import is_celery_app_need

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client, S3ServiceResource  # type: ignore

context = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_logs(app_settings.LAMP_STAGE, debug=app_settings.LETSUR_DEBUG)
    try:
        from src._version import version  # type: ignore

        ServingLogger().info(f"AppVersion: {version}")
    except ImportError:
        ServingLogger().warning("AppVersion Import Failed...")

    ## GET S3 Bucket For celery Result Backend
    if is_celery_app_need():
        from celery.backends.s3 import S3Backend

        from .worker.celery import celery_app

        celery_backend: S3Backend = celery_app.backend
        s3_resource: S3ServiceResource = celery_backend._s3_resource
        bucket = s3_resource.Bucket(name=celery_backend.bucket_name)
        try:
            bucket.meta.client.head_bucket(Bucket=celery_backend.bucket_name)
        except ClientError as e:
            if (
                e.response["Error"]["Code"] == "404"
                and app_settings.LETSUR_APP_IS_LOCALSTACK
            ):
                # Create Bucket
                bucket.meta.client.create_bucket(
                    Bucket=celery_backend.bucket_name,
                    CreateBucketConfiguration={
                        "LocationConstraint": celery_backend.aws_region
                    },
                )
            elif (
                e.response["Error"]["Code"] == "403"
                and app_settings.LETSUR_APP_IS_LOCALSTACK
            ):
                # Can not Access S3 bucket, object
                ServingLogger().warning("\n".join(e.args))
            else:
                raise LampApplicationError(
                    message="\n".join(e.args), extra=e.response
                ) from e

    if app_settings.LETSUR_DEBUG:
        import asyncio

        from .debug import monitor_event_loop_lag

        loop = asyncio.get_running_loop()
        loop.create_task(monitor_event_loop_lag(loop))

    yield context

    trace_flush()
    ServingLogger().info("Do langfuse flush")


app = FastAPI(
    title=app_settings.APP_TITLE,
    lifespan=lifespan,
    debug=app_settings.LETSUR_DEBUG,
    root_path=app_settings.URL_ROOT_PATH,
)

include_middlewares(app, debug=app_settings.LETSUR_DEBUG)
include_excpetion_hander(app)
if is_celery_app_need():
    from .worker.celery import celery_app

    init_app_for_async(celery_app=celery_app, fast_app=app)
add_user_routers(app)
check_setting_interface()


@app.get(LIVENESS_PATH, include_in_schema=True if app_settings.LETSUR_DEBUG else False)
async def _liveness():
    return True


@app.get(READINESS_PATH, include_in_schema=True if app_settings.LETSUR_DEBUG else False)
async def _readiness():
    return True
