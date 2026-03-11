import sys
from loguru import logger
from app.config import settings

def setup_logging() -> None:
    logger.remove()
    logger.add(
        sys.stdout, 
        level=settings.LOG_LEVEL,
        format="[{time:HH:mm:ss}] >> {name}:{line} >> {level}: {message} >> {extra}",
        enqueue=True,
        backtrace=True,
        diagnose=settings.DEBUG
    )