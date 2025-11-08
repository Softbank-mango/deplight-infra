from functools import cached_property
from hashlib import sha256
from typing import List, Literal, Optional, Tuple

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings

STAGES_TYPE = Literal["dev", "stg", "prd"]


class CoreSettings(BaseSettings):
    """
    중계서버가 넣어주길 기대하는 값들.
    """

    LAMP_STAGE: STAGES_TYPE = Field("dev", description="Serving 환경")
    LAMP_PROJECT_ID: str = Field(description="LAMP의 Project Id, Unique해야하며 필수 값")
    LETSUR_DEBUG: bool = Field(False, alias=AliasChoices("LETSUR_DEBUG", "DEBUG"), description="Debugging 모드. Logger와 DEBUG_MIDDLEWARES에 영향")  # type: ignore
    LAMP_PROJECT_NAME: str = "letsur-common-app"
    LAMP_MODEL_VERSION: str = "0"
    LETSUR_ML_PROJECT_NAME: str = Field(
        "letsur-common-app", description="AI Project Name"
    )

    LETSUR_APP_IS_LOCAL: bool = Field(False, description="local에서 실행하는 것인지 구분자")
    LETSUR_APP_IS_LOCALSTACK: bool = Field(
        False,
        description="local에서 실행 시 localstack을 활용하여 s3, sqs, redis 등을 aws 리소스를 쓰지 않기 위해 사용",
    )
    LETSUR_ADMIN_URL_HOST: str = Field(
        "api-dev-c1-admin.letsur.ai", description="Quota 측정 시 bypass하는 호스트"
    )
    LAMP_INVOCATION_USE_QUOTA: bool = Field(
        False, description="/invocations api에 대한 Quota 설정 인터페이스"
    )

    @computed_field
    @cached_property
    def APP_TITLE(self) -> str:
        return (
            self.LAMP_PROJECT_NAME
            or self.LETSUR_ML_PROJECT_NAME
            or self.LAMP_PROJECT_ID
        )

    @computed_field
    @cached_property
    def UNIQUE_FULL_NAME(self) -> str:
        return f"{self.LETSUR_ML_PROJECT_NAME}-{self.LAMP_PROJECT_ID}-{self.LAMP_MODEL_VERSION}"

    @computed_field
    @cached_property
    def QUOTA_KEY_FORMAT(self) -> str:
        return f"lamp-{self.LAMP_PROJECT_ID}-{self.LAMP_STAGE}-{{YYYYMM}}"

    @computed_field
    @cached_property
    def URL_ROOT_PATH(self) -> str:
        if self.LETSUR_APP_IS_LOCAL:
            return ""
        return f"/{self.LAMP_PROJECT_ID}"


app_settings = CoreSettings.model_validate({})


class RedisSettings(BaseSettings):
    LETSUR_REDIS_URL: Optional[
        str
    ] = "redis://mlops-240604-non-prd-serverless-cache-edlpej.serverless.apn2.cache.amazonaws.com:6379"


class CeleryCoreSettings(BaseSettings):
    # CELERY
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_DEFAULT_REGION: str = "ap-northeast-2"
    CELERY_BROKER_HOST: Optional[str] = None  # Localstack 용
    # CELERY_BROKER_URL: Optional[str] = None
    CELERY_S3_BUCKET: str = "letsur-api-async"
    CELERY_S3_DOMAIN: str = "api-async.letsur.ai"
    CELERY_WORKER_NUM: int = 1

    @computed_field
    @cached_property
    def CELERY_BROKER_URL(self) -> str:
        # AWS SQS
        if app_settings.LETSUR_APP_IS_LOCALSTACK and self.CELERY_BROKER_HOST:
            # LOCAL_STACK
            return "sqs://{aws_access_key}:{aws_secret_key}@{celery_broker_host}:4566".format(
                aws_access_key=self.AWS_ACCESS_KEY_ID,
                aws_secret_key=self.AWS_SECRET_ACCESS_KEY,
                celery_broker_host=self.CELERY_BROKER_HOST,
            )
        elif (
            app_settings.LETSUR_APP_IS_LOCAL
            and self.AWS_ACCESS_KEY_ID
            and self.AWS_SECRET_ACCESS_KEY
        ):
            # AWS SQS But with .env credential
            return "sqs://{aws_access_key}:{aws_secret_key}@".format(
                aws_access_key=self.AWS_ACCESS_KEY_ID,
                aws_secret_key=self.AWS_SECRET_ACCESS_KEY,
            )
        return "sqs://"

    @computed_field
    @cached_property
    def CELERY_S3_ENDPOINT_URL(self) -> Optional[str]:
        if app_settings.LETSUR_APP_IS_LOCALSTACK and self.CELERY_BROKER_HOST:
            return f"http://{self.CELERY_BROKER_HOST}:4566"
        return None

    @computed_field
    @cached_property
    def queue_name_prefix(self) -> str:
        return f"app-{app_settings.LAMP_PROJECT_ID}-{app_settings.LAMP_STAGE}-"


celery_settings = CeleryCoreSettings()
redis_settings = RedisSettings()
