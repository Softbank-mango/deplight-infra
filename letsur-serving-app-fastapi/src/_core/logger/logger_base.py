import logging


class LoggerBase:
    logger_name: str
    logger: logging.Logger

    def get_logger(self):
        return self.logger

    def debug(self, message: str, stack_level: int = 0):
        self.logger.debug(message, stacklevel=2 + stack_level)

    def info(self, message: str, stack_level: int = 0):
        self.logger.info(message, stacklevel=2 + stack_level)

    def warning(self, message: str, stack_level: int = 0):
        self.logger.warning(message, stacklevel=2 + stack_level)

    def error(self, message: str, stack_level: int = 0):
        self.logger.error(message, stacklevel=2 + stack_level)

    def critical(self, message: str, stack_level: int = 0):
        self.logger.critical(message, stacklevel=2 + stack_level)
