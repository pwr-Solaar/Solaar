import logging


class CustomLogger(logging.Logger):
    """Logger, that avoids unnecessary string computations.

    Does not compute messages for disabled log levels.
    """

    def debug(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.DEBUG):
            super().debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.INFO):
            super().info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.WARNING):
            super().warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.ERROR):
            super().error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        if self.isEnabledFor(logging.CRITICAL):
            super().critical(msg, *args, **kwargs)
