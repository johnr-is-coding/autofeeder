import asyncio
import sys
from uuid import uuid4
import typer
from loguru import logger

from app.config import settings
from app.logger import setup_logging
from app.infrastructure.api_client import APIClient
from app.infrastructure.database import AsyncSessionLocal, dispose_engine
from app.services.report_monitor import ReportMonitor
from app.utils.exceptions import AppRuntimeError, DatabaseError, ServiceError

setup_logging()

app = typer.Typer()

async def main_loop():
    """
    Main loop of the AutoFeeder application
    """
    logger.info(
        "Service starting",
        event="service_start",
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        env=settings.ENV,
    )
    consecutive_failures = 0

    try:
        async with APIClient() as api_client:
            while True:
                cycle_id = str(uuid4())
                try:
                    async with AsyncSessionLocal() as session:
                        monitor = ReportMonitor(api_client, session)
                        logger.info(
                            "Polling cycle started",
                            event="polling_cycle_start",
                            cycle_id=cycle_id,
                        )
                        await monitor.run_cycle()
                        logger.info(
                            "Polling cycle completed",
                            event="polling_cycle_complete",
                            cycle_id=cycle_id,
                        )
                    consecutive_failures = 0
                except (ServiceError, DatabaseError) as e:
                    consecutive_failures += 1
                    logger.exception(
                        "Polling cycle failed",
                        event="polling_cycle_failed",
                        cycle_id=cycle_id,
                        error=str(e),
                        error_type=type(e).__name__,
                        failures=consecutive_failures,
                        max_failures=settings.POLLING_MAX_RETRIES,
                    )
                    if consecutive_failures >= settings.POLLING_MAX_RETRIES:
                        raise AppRuntimeError(
                            f"Polling failed {consecutive_failures} consecutive times"
                        ) from e
                    logger.warning(
                        "Retrying polling cycle after backoff",
                        event="polling_cycle_retry",
                        cycle_id=cycle_id,
                        retry_attempt=consecutive_failures,
                        backoff_seconds=settings.POLLING_RETRY_BACKOFF,
                    )
                    await asyncio.sleep(settings.POLLING_RETRY_BACKOFF)
                    continue

                await asyncio.sleep(settings.POLLING_INTERVAL)
    finally:
        logger.info("Disposing database engine", event="db_engine_dispose_start")
        await dispose_engine()
        logger.info("Service stopped", event="service_stop")


@app.command()
def run() -> None:
    """
    Start AutoFeeder application
    """
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received", event="service_interrupt")
        sys.exit(0)
    except Exception as e:
        logger.critical(
            "Fatal runtime error",
            event="service_fatal",
            error=str(e),
            error_type=type(e).__name__,
        )
        sys.exit(1)

if __name__ == "__main__":
    app()