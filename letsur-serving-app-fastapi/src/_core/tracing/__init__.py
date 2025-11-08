import warnings
import logging
from packaging.version import Version

from src._core.settings import app_settings
from pydantic import ValidationError

IS_LANGFUSE_INSTALLED = None
configure_kwargs = {}
try:
    from langfuse import __version__ as langfuse_version
    from langfuse.decorators import langfuse_context, observe
    from .settings import LangfuseSettings

    langfuse_setting = LangfuseSettings.model_validate({})
    langfuse_version = Version(langfuse_version)

    IS_LANGFUSE_INSTALLED = True
    # TODO
    # LOGGING 관련된 DEBUG는 좀 분리가 필요할지도.
    # if app_settings.LETSUR_DEBUG:
    #     configure_kwargs["debug"] = True

    if langfuse_version >= Version("2.59.7"):
        env = "local" if app_settings.LETSUR_APP_IS_LOCAL else app_settings.LAMP_STAGE
        configure_kwargs["environment"] = env

    if configure_kwargs:
        langfuse_context.configure(**configure_kwargs)

    from .decorators import langfuse_exception_handling_decorator

except ImportError:
    IS_LANGFUSE_INSTALLED = False
    warnings.warn("Langfuse Import 실패. Trace, observe 기능 사용이 불가능합니다.")
except ValidationError as e:
    IS_LANGFUSE_INSTALLED = False
    warnings.warn("Langfuse 환경변수 주입이 실패하였습니다. Trace, observe 기능 사용이 불가능합니다.")
    logging.getLogger(__name__).error("Langfuse 설정 검증 실패: %s", e)


def trace_flush():
    if IS_LANGFUSE_INSTALLED:
        langfuse_context.flush()
    return


def langfuse_init():
    if IS_LANGFUSE_INSTALLED:
        langfuse_context.configure(**configure_kwargs)
    return
