import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.main import main_loop

MODULE = "app.main"


def _setup_api_client(mock_cls: MagicMock) -> AsyncMock:
    """Wire an async context manager so 'async with APIClient() as client' works."""
    api_client = AsyncMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=api_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
    return api_client


def _setup_session(mock_cls: MagicMock) -> AsyncMock:
    """Wire an async context manager so 'async with AsyncSessionLocal() as session' works."""
    session = AsyncMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
    return session


# ===========================================================================
# main_loop
# ===========================================================================

class TestMainLoop:

    # ------------------------------------------------------------------
    # Test 1 – run_cycle is called each iteration
    # Name: main_loop calls run_cycle
    # Description: Each pass through the while loop should call
    #              monitor.run_cycle() exactly once before sleeping.
    #              asyncio.sleep raising CancelledError stops the loop
    #              after the first iteration.
    # Steps: Patch sleep to raise CancelledError; run main_loop; catch
    #        CancelledError; verify run_cycle was called.
    # Expected: run_cycle called once.
    # ------------------------------------------------------------------
    async def test_run_cycle_called(self):
        with patch(f"{MODULE}.APIClient") as mock_api_cls, \
             patch(f"{MODULE}.AsyncSessionLocal") as mock_session_cls, \
             patch(f"{MODULE}.ReportMonitor") as mock_monitor_cls, \
             patch(f"{MODULE}.dispose_engine", AsyncMock()), \
             patch("asyncio.sleep", AsyncMock(side_effect=asyncio.CancelledError)):

            _setup_api_client(mock_api_cls)
            _setup_session(mock_session_cls)
            mock_monitor = AsyncMock()
            mock_monitor_cls.return_value = mock_monitor

            with pytest.raises(asyncio.CancelledError):
                await main_loop()

        mock_monitor.run_cycle.assert_called_once()

    # ------------------------------------------------------------------
    # Test 2 – Cycle errors are caught and do not crash the loop
    # Name: main_loop continues after a cycle exception
    # Description: If run_cycle raises, the loop should log the error and
    #              continue to the sleep — it must not crash the application.
    #              asyncio.sleep raising CancelledError ends the test.
    # Steps: Make run_cycle raise RuntimeError; patch sleep to raise
    #        CancelledError; verify logger.error called and sleep called.
    # Expected: logger.error called once; asyncio.sleep still called.
    # ------------------------------------------------------------------
    async def test_cycle_error_is_caught_and_logged(self):
        mock_sleep = AsyncMock(side_effect=asyncio.CancelledError)

        with patch(f"{MODULE}.APIClient") as mock_api_cls, \
             patch(f"{MODULE}.AsyncSessionLocal") as mock_session_cls, \
             patch(f"{MODULE}.ReportMonitor") as mock_monitor_cls, \
             patch(f"{MODULE}.dispose_engine", AsyncMock()), \
             patch(f"{MODULE}.logger") as mock_logger, \
             patch("asyncio.sleep", mock_sleep):

            _setup_api_client(mock_api_cls)
            _setup_session(mock_session_cls)
            mock_monitor = AsyncMock()
            mock_monitor.run_cycle = AsyncMock(side_effect=RuntimeError("boom"))
            mock_monitor_cls.return_value = mock_monitor

            with pytest.raises(asyncio.CancelledError):
                await main_loop()

        mock_logger.error.assert_called_once()
        mock_sleep.assert_called_once()

    # ------------------------------------------------------------------
    # Test 3 – dispose_engine is called on exit
    # Name: main_loop calls dispose_engine in finally block
    # Description: Whether the loop exits normally or via an exception,
    #              dispose_engine must be called to clean up the connection pool.
    # Steps: Let the loop exit via CancelledError; verify dispose_engine called.
    # Expected: dispose_engine called exactly once.
    # ------------------------------------------------------------------
    async def test_dispose_engine_called_on_exit(self):
        mock_dispose = AsyncMock()

        with patch(f"{MODULE}.APIClient") as mock_api_cls, \
             patch(f"{MODULE}.AsyncSessionLocal") as mock_session_cls, \
             patch(f"{MODULE}.ReportMonitor") as mock_monitor_cls, \
             patch(f"{MODULE}.dispose_engine", mock_dispose), \
             patch("asyncio.sleep", AsyncMock(side_effect=asyncio.CancelledError)):

            _setup_api_client(mock_api_cls)
            _setup_session(mock_session_cls)
            mock_monitor_cls.return_value = AsyncMock()

            with pytest.raises(asyncio.CancelledError):
                await main_loop()

        mock_dispose.assert_called_once()

    # ------------------------------------------------------------------
    # Test 4 – asyncio.sleep is called with POLLING_INTERVAL
    # Name: main_loop sleeps for POLLING_INTERVAL seconds
    # Description: The loop should wait settings.POLLING_INTERVAL seconds
    #              between cycles, not a hardcoded value.
    # Steps: Run one loop iteration; inspect the argument passed to sleep.
    # Expected: asyncio.sleep called with settings.POLLING_INTERVAL.
    # ------------------------------------------------------------------
    async def test_sleep_called_with_polling_interval(self):
        from app.config import settings
        mock_sleep = AsyncMock(side_effect=asyncio.CancelledError)

        with patch(f"{MODULE}.APIClient") as mock_api_cls, \
             patch(f"{MODULE}.AsyncSessionLocal") as mock_session_cls, \
             patch(f"{MODULE}.ReportMonitor") as mock_monitor_cls, \
             patch(f"{MODULE}.dispose_engine", AsyncMock()), \
             patch("asyncio.sleep", mock_sleep):

            _setup_api_client(mock_api_cls)
            _setup_session(mock_session_cls)
            mock_monitor_cls.return_value = AsyncMock()

            with pytest.raises(asyncio.CancelledError):
                await main_loop()

        mock_sleep.assert_called_once_with(settings.POLLING_INTERVAL)

    # ------------------------------------------------------------------
    # Test 5 – ReportMonitor is instantiated with the api_client and session
    # Name: main_loop wires api_client and session into ReportMonitor
    # Description: The monitor should receive the active APIClient instance
    #              and the current AsyncSession on every cycle.
    # Steps: Capture the args passed to ReportMonitor(); verify identity.
    # Expected: ReportMonitor called with (api_client, session).
    # ------------------------------------------------------------------
    async def test_monitor_receives_api_client_and_session(self):
        with patch(f"{MODULE}.APIClient") as mock_api_cls, \
             patch(f"{MODULE}.AsyncSessionLocal") as mock_session_cls, \
             patch(f"{MODULE}.ReportMonitor") as mock_monitor_cls, \
             patch(f"{MODULE}.dispose_engine", AsyncMock()), \
             patch("asyncio.sleep", AsyncMock(side_effect=asyncio.CancelledError)):

            api_client = _setup_api_client(mock_api_cls)
            session = _setup_session(mock_session_cls)
            mock_monitor_cls.return_value = AsyncMock()

            with pytest.raises(asyncio.CancelledError):
                await main_loop()

        mock_monitor_cls.assert_called_once_with(api_client, session)
