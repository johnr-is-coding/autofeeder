# conftest.py
import pytest
from loguru import logger
from app.logger import setup_logging

@pytest.fixture(autouse=True, scope="session")
def configure_logging():
    setup_logging()
    yield
    logger.complete()  # flush the enqueue'd background thread before exit
