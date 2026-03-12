from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.models.schemas import IncomingReport
from app.domain.models.stored_report import StoredReport
from app.infrastructure import api_client
from app.services.report_monitor import ReportChange, ReportMonitor
from app.utils.enums import MarketType, ReportStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stored(
    slug: str = "1234",
    report_date: date = date(2024, 1, 1),
    published_date: datetime = datetime(2024, 1, 1, 10, 0),
    report_status: ReportStatus = ReportStatus.PRELIMINARY,
) -> MagicMock:
    stored = MagicMock(spec=StoredReport)
    stored.slug = slug
    stored.report_date = report_date
    stored.published_date = published_date
    stored.report_status = report_status
    return stored


def _make_incoming(
    slug: str = "1234",
    report_date: date = date(2024, 1, 1),
    published_date: datetime = datetime(2024, 1, 1, 10, 0),
    report_status: ReportStatus = ReportStatus.PRELIMINARY,
) -> MagicMock:
    incoming = MagicMock(spec=IncomingReport)
    incoming.slug = slug
    incoming.report_date = report_date
    incoming.published_date = published_date
    incoming.report_status = report_status
    return incoming


# ---------------------------------------------------------------------------
# _detect_changes
# ---------------------------------------------------------------------------

class TestDetectChanges:

    @pytest.fixture
    def monitor(self) -> ReportMonitor:
        return ReportMonitor(api_client=MagicMock(), session=MagicMock())

    def test_detects_report_date_change(self, monitor: ReportMonitor) -> None:
        stored = _make_stored(report_date=date(2024, 1, 1))
        incoming = _make_incoming(report_date=date(2024, 2, 1))
        assert monitor._detect_changes(stored, incoming)

    def test_detects_published_date_change(self, monitor: ReportMonitor) -> None:
        stored = _make_stored(published_date=datetime(2024, 1, 1, 10, 0, 0))
        incoming = _make_incoming(published_date=datetime(2024, 1, 2, 10, 0, 0))
        assert monitor._detect_changes(stored, incoming)

    def test_detects_report_status_change(self, monitor: ReportMonitor) -> None:
        stored = _make_stored(report_status=ReportStatus.PRELIMINARY)
        incoming = _make_incoming(report_status=ReportStatus.FINAL)
        assert monitor._detect_changes(stored, incoming)

    def test_no_changes_returns_false(self, monitor: ReportMonitor) -> None:
        stored = _make_stored()
        incoming = _make_incoming()
        assert not monitor._detect_changes(stored, incoming)


# ---------------------------------------------------------------------------
# _get_changes
# ---------------------------------------------------------------------------

class TestGetChanges:

    @pytest.fixture
    def monitor(self) -> ReportMonitor:
        return ReportMonitor(api_client=MagicMock(), session=MagicMock())

    def test_detects_change_for_matching_slug(self, monitor: ReportMonitor) -> None:
        stored = _make_stored(report_date=date(2024, 1, 1))
        incoming = _make_incoming(report_date=date(2024, 2, 1))
        incoming_map = {stored.slug: incoming}
        changes = monitor._get_changes(stored_reports=[stored], incoming_map=incoming_map)
        
        change = changes[0]
        assert len(changes) == 1
        assert change.slug == stored.slug
        assert change.stored is stored
        assert change.incoming is incoming

    def test_incoming_report_not_in_map_returns_empty(self, monitor: ReportMonitor) -> None:
        stored = _make_stored()
        incoming_map = {"other-slug": _make_incoming()}
        changes = monitor._get_changes(stored_reports=[stored], incoming_map=incoming_map)
        assert changes == []

    def test_no_incoming_reports_returns_empty(self, monitor: ReportMonitor) -> None:
        stored = _make_stored()
        changes = monitor._get_changes(stored_reports=[stored], incoming_map={})
        assert changes == []


# ---------------------------------------------------------------------------
# run_cycle
# ---------------------------------------------------------------------------

class TestRunCycle:

    def _make_monitor(
        self,
        incoming_map: dict,
        stored_reports: list,
    ) -> ReportMonitor:
        api_client = MagicMock()
        api_client.fetch_current_reports = AsyncMock(return_value=incoming_map)
        monitor = ReportMonitor(api_client=api_client, session=MagicMock())
        monitor._load_stored_reports = AsyncMock(return_value=stored_reports)
        monitor._generate_reports = AsyncMock(return_value=[])
        monitor._upsert_reports = AsyncMock()
        monitor._upsert_stored_report = AsyncMock()
        return monitor
    
    async def test_no_changes_detected(self) -> None:
        stored = _make_stored()
        incoming = _make_incoming()
        monitor = self._make_monitor(incoming_map={stored.slug: incoming}, stored_reports=[stored])
        
        await monitor.run_cycle()
        
        monitor._generate_reports.assert_not_called()
        monitor._upsert_reports.assert_not_called()
        monitor._upsert_stored_report.assert_not_called()

    async def test_changes_detected_and_processed(self) -> None:
        stored = _make_stored(report_date=date(2024, 1, 1))
        incoming = _make_incoming(report_date=date(2024, 2, 1))
        monitor = self._make_monitor(incoming_map={stored.slug: incoming}, stored_reports=[stored])
        
        await monitor.run_cycle()
        
        monitor._generate_reports.assert_called_once_with(stored.slug, stored.market_type)
        monitor._upsert_reports.assert_called_once()
        monitor._upsert_stored_report.assert_called_once_with(incoming)
        