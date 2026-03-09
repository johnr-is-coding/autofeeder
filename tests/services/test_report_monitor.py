from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.models.schemas import IncomingReport
from app.domain.models.stored_report import StoredReport
from app.services.report_monitor import ReportChange, ReportChangeType, ReportMonitor
from app.utils.enums import ReportStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stored(
    slug: str = "test-slug",
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
    slug: str = "test-slug",
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

    def test_no_changes_returns_empty(self, monitor: ReportMonitor) -> None:
        stored = _make_stored()
        incoming = _make_incoming()
        assert monitor._detect_changes(stored, incoming) == []

    def test_report_date_changed_returns_new_report_date(self, monitor: ReportMonitor) -> None:
        stored = _make_stored(report_date=date(2024, 1, 1))
        incoming = _make_incoming(report_date=date(2024, 2, 1))
        changes = monitor._detect_changes(stored, incoming)
        assert len(changes) == 1
        assert changes[0].change_type == ReportChangeType.NEW_REPORT_DATE

    def test_status_changed_returns_status_changed(self, monitor: ReportMonitor) -> None:
        stored = _make_stored(report_status=ReportStatus.PRELIMINARY)
        incoming = _make_incoming(report_status=ReportStatus.FINAL)
        changes = monitor._detect_changes(stored, incoming)
        assert len(changes) == 1
        assert changes[0].change_type == ReportChangeType.STATUS_CHANGED

    def test_published_date_changed_returns_published_date_updated(self, monitor: ReportMonitor) -> None:
        stored = _make_stored(published_date=datetime(2024, 1, 1, 10, 0))
        incoming = _make_incoming(published_date=datetime(2024, 1, 2, 10, 0))
        changes = monitor._detect_changes(stored, incoming)
        assert len(changes) == 1
        assert changes[0].change_type == ReportChangeType.PUBLISHED_DATE_UPDATED

    def test_report_date_trumps_status_change(self, monitor: ReportMonitor) -> None:
        stored = _make_stored(report_date=date(2024, 1, 1), report_status=ReportStatus.PRELIMINARY)
        incoming = _make_incoming(report_date=date(2024, 2, 1), report_status=ReportStatus.FINAL)
        changes = monitor._detect_changes(stored, incoming)
        assert len(changes) == 1
        assert changes[0].change_type == ReportChangeType.NEW_REPORT_DATE

    def test_report_date_trumps_published_date_change(self, monitor: ReportMonitor) -> None:
        stored = _make_stored(report_date=date(2024, 1, 1), published_date=datetime(2024, 1, 1, 10, 0))
        incoming = _make_incoming(report_date=date(2024, 2, 1), published_date=datetime(2024, 2, 1, 10, 0))
        changes = monitor._detect_changes(stored, incoming)
        assert len(changes) == 1
        assert changes[0].change_type == ReportChangeType.NEW_REPORT_DATE

    def test_status_trumps_published_date_change(self, monitor: ReportMonitor) -> None:
        stored = _make_stored(report_status=ReportStatus.PRELIMINARY, published_date=datetime(2024, 1, 1, 10, 0))
        incoming = _make_incoming(report_status=ReportStatus.FINAL, published_date=datetime(2024, 1, 2, 10, 0))
        changes = monitor._detect_changes(stored, incoming)
        assert len(changes) == 1
        assert changes[0].change_type == ReportChangeType.STATUS_CHANGED

    def test_all_fields_differ_returns_only_one_change(self, monitor: ReportMonitor) -> None:
        stored = _make_stored(
            report_date=date(2024, 1, 1),
            report_status=ReportStatus.PRELIMINARY,
            published_date=datetime(2024, 1, 1, 10, 0),
        )
        incoming = _make_incoming(
            report_date=date(2024, 2, 1),
            report_status=ReportStatus.FINAL,
            published_date=datetime(2024, 2, 1, 10, 0),
        )
        assert len(monitor._detect_changes(stored, incoming)) == 1

    def test_change_carries_correct_stored_and_incoming(self, monitor: ReportMonitor) -> None:
        stored = _make_stored(report_date=date(2024, 1, 1))
        incoming = _make_incoming(report_date=date(2024, 2, 1))
        change = monitor._detect_changes(stored, incoming)[0]
        assert change.stored is stored
        assert change.incoming is incoming
        assert change.slug == stored.slug


# ---------------------------------------------------------------------------
# _dispatch
# ---------------------------------------------------------------------------

class TestDispatch:

    @pytest.fixture
    def monitor(self) -> ReportMonitor:
        return ReportMonitor(api_client=MagicMock(), session=MagicMock())

    async def test_calls_on_new_report_date(self, monitor: ReportMonitor) -> None:
        monitor._on_new_report_date = AsyncMock()
        change = ReportChange(
            slug="s",
            change_type=ReportChangeType.NEW_REPORT_DATE,
            stored=_make_stored(),
            incoming=_make_incoming(),
        )
        await monitor._dispatch(change)
        monitor._on_new_report_date.assert_awaited_once_with(change)

    async def test_calls_on_status_changed(self, monitor: ReportMonitor) -> None:
        monitor._on_status_changed = AsyncMock()
        change = ReportChange(
            slug="s",
            change_type=ReportChangeType.STATUS_CHANGED,
            stored=_make_stored(),
            incoming=_make_incoming(),
        )
        await monitor._dispatch(change)
        monitor._on_status_changed.assert_awaited_once_with(change)

    async def test_calls_on_published_date_updated(self, monitor: ReportMonitor) -> None:
        monitor._on_published_date_updated = AsyncMock()
        change = ReportChange(
            slug="s",
            change_type=ReportChangeType.PUBLISHED_DATE_UPDATED,
            stored=_make_stored(),
            incoming=_make_incoming(),
        )
        await monitor._dispatch(change)
        monitor._on_published_date_updated.assert_awaited_once_with(change)


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
        monitor._dispatch = AsyncMock()
        return monitor

    async def test_skips_slug_not_in_incoming_map(self) -> None:
        stored = _make_stored(slug="missing-slug")
        monitor = self._make_monitor(incoming_map={}, stored_reports=[stored])
        await monitor.run_cycle()
        monitor._dispatch.assert_not_awaited()

    async def test_dispatches_detected_change(self) -> None:
        stored = _make_stored(report_date=date(2024, 1, 1))
        incoming = _make_incoming(report_date=date(2024, 2, 1))
        monitor = self._make_monitor(
            incoming_map={"test-slug": incoming},
            stored_reports=[stored],
        )
        await monitor.run_cycle()
        monitor._dispatch.assert_awaited_once()
        change = monitor._dispatch.call_args[0][0]
        assert change.change_type == ReportChangeType.NEW_REPORT_DATE

    async def test_no_dispatch_when_no_changes(self) -> None:
        stored = _make_stored()
        incoming = _make_incoming()
        monitor = self._make_monitor(
            incoming_map={"test-slug": incoming},
            stored_reports=[stored],
        )
        await monitor.run_cycle()
        monitor._dispatch.assert_not_awaited()

    async def test_processes_multiple_stored_reports(self) -> None:
        stored_a = _make_stored(slug="a", report_date=date(2024, 1, 1))
        stored_b = _make_stored(slug="b", report_date=date(2024, 1, 1))
        incoming_a = _make_incoming(slug="a", report_date=date(2024, 2, 1))
        incoming_b = _make_incoming(slug="b", report_date=date(2024, 2, 1))
        monitor = self._make_monitor(
            incoming_map={"a": incoming_a, "b": incoming_b},
            stored_reports=[stored_a, stored_b],
        )
        await monitor.run_cycle()
        assert monitor._dispatch.await_count == 2

    async def test_partial_match_only_dispatches_matched_slugs(self) -> None:
        stored_tracked = _make_stored(slug="tracked", report_date=date(2024, 1, 1))
        stored_untracked = _make_stored(slug="untracked", report_date=date(2024, 1, 1))
        incoming_tracked = _make_incoming(slug="tracked", report_date=date(2024, 2, 1))
        monitor = self._make_monitor(
            incoming_map={"tracked": incoming_tracked},
            stored_reports=[stored_tracked, stored_untracked],
        )
        await monitor.run_cycle()
        assert monitor._dispatch.await_count == 1
