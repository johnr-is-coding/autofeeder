import asyncio
import sys
import typer
from loguru import logger

from app.config import settings
from app.infrastructure.api_client import APIClient
from app.infrastructure.database import AsyncSessionLocal, dispose_engine
from app.logger import setup_logging
from app.services.report_monitor import ReportMonitor

setup_logging()

app = typer.Typer()

async def main_loop():
    """
    Main loop of the AutoFeeder application
    """
    logger.info(f"Starting {settings.APP_NAME}({settings.APP_VERSION}) in {settings.ENV} mode")

    try:
        async with APIClient() as api_client:
            while True:
                try:
                    async with AsyncSessionLocal() as session:
                        monitor = ReportMonitor(api_client, session)
                        await monitor.run_cycle()
                except Exception as e:
                    logger.error("Polling cycle failed", error=str(e))

                await asyncio.sleep(settings.POLLING_INTERVAL)
    finally:
        await dispose_engine()


@app.command()
def run() -> None:
    """
    Start AutoFeeder application
    """
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Exiting gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    app()