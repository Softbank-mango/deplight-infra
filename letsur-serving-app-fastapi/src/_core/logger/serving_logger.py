import logging
from .logger_base import LoggerBase

from src._core.settings import app_settings


class ServingLogger(LoggerBase):
    logger_name = app_settings.UNIQUE_FULL_NAME
    logger = logging.getLogger(logger_name)
