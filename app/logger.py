import sys
from pathlib import Path
from loguru import logger
from app.config import settings

def setup_logging() -> None:
    logger.remove()

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "autofeeder.log"

    # logger.add(
    #     sys.stdout,
    #     level=settings.LOG_LEVEL,
    #     serialize=True,
    #     enqueue=True,
    #     backtrace=True,
    #     diagnose=settings.DEBUG,
    # )

    logger.add(
        log_file,
        level=settings.LOG_LEVEL,
        serialize=True,
        enqueue=True,
        backtrace=True,
        diagnose=settings.DEBUG,
        rotation="10 MB",
        retention="14 days",
    )