import sys
from loguru import logger
from app.config import settings

def setup_logging() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        serialize=True,
        enqueue=True,
        backtrace=True,
        diagnose=settings.DEBUG,
    )