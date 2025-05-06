import logging
import sys

from loguru import logger as log

log.remove()
log.add(sys.stderr, level="DEBUG")
log.add(
    "discord.log",
    rotation="32 MB",  # Rotate at 32 MiB
    retention=5,  # Keep 5 files
    compression="zip",
    level="DEBUG",
)


class InterceptHandler(logging.Handler):
    def emit(self, record):
        level = record.levelname
        frame, depth = sys._getframe(1), 1
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        log.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


logging.basicConfig(handlers=[InterceptHandler()], level=logging.DEBUG)
logging.getLogger("discord").setLevel(logging.DEBUG)
logging.getLogger("discord.http").setLevel(logging.INFO)
