import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.agg_models import LatestReport
from app.services.report_monitor import ReportChange, ReportChangeType, ReportMonitor
from app.utils.enums import ReportStatusOptions


# ===========================================================================
# Shared helpers
# ===========================================================================

BASE_DATA = {
    "slug_id": "1281",
    "report_date": "01/15/2024",
    "published_date": "01/15/2024 10:00:00",
    "report_status": "Final",
    "market_types": ["Auction Livestock"],
    "hasCorrectionsInLastThreeDays": False,
}


def make_report(**overrides) -> LatestReport:
    return LatestReport(**{**BASE_DATA, **overrides})


@pytest.fixture
def stored() -> LatestReport:
    return make_report()


@pytest.fixture
def incoming() -> LatestReport:
    return make_report()


@pytest.fixture
def monitor() -> ReportMonitor:
    return ReportMonitor(api_client=AsyncMock(), session=AsyncMock())


# ===========================================================================
# ReportChangeType
# ===========================================================================

class TestReportChangeType:

    # ------------------------------------------------------------------
    # Test 1 – NEW_REPORT_DATE value
    # Name: NEW_REPORT_DATE string value
    # Description: Enum member should have the expected string value.
    # Steps: Access ReportChangeType.NEW_REPORT_DATE.value
    # Expected: "new_report_date"
    # ------------------------------------------------------------------
    def test_new_report_date_value(self):
        assert ReportChangeType.NEW_REPORT_DATE.value == "new_report_date"

    # ------------------------------------------------------------------
    # Test 2 – PUBLISHED_DATE_UPDATED value
    # Name: PUBLISHED_DATE_UPDATED string value
    # Description: Enum member should have the expected string value.
    # Steps: Access ReportChangeType.PUBLISHED_DATE_UPDATED.value
    # Expected: "published_date_updated"
    # ------------------------------------------------------------------
    def test_published_date_updated_value(self):
        assert ReportChangeType.PUBLISHED_DATE_UPDATED.value == "published_date_updated"

    # ------------------------------------------------------------------
    # Test 3 – STATUS_CHANGED value
    # Name: STATUS_CHANGED string value
    # Description: Enum member should have the expected string value.
    # Steps: Access ReportChangeType.STATUS_CHANGED.value
    # Expected: "status_changed"
    # ------------------------------------------------------------------
    def test_status_changed_value(self):
        assert ReportChangeType.STATUS_CHANGED.value == "status_changed"

    # ------------------------------------------------------------------
    # Test 4 – Exactly three members
    # Name: ReportChangeType has exactly three members
    # Description: No extra or missing members should exist.
    # Steps: Collect all member values; compare to expected set.
    # Expected: {"new_report_date", "published_date_updated", "status_changed"}
    # ------------------------------------------------------------------
    def test_exactly_three_members(self):
        members = {m.value for m in ReportChangeType}
        assert members == {"new_report_date", "published_date_updated", "status_changed"}


# ===========================================================================
# ReportChange
# ===========================================================================

class TestReportChange:

    # ------------------------------------------------------------------
    # Test 5 – Dataclass stores all fields
    # Name: ReportChange stores slug, change_type, stored, incoming
    # Description: All four fields should be accessible after construction.
    # Steps: Construct ReportChange; inspect each attribute.
    # Expected: Attributes match the values passed in.
    # ------------------------------------------------------------------
    def test_stores_all_fields(self, stored, incoming):
        change = ReportChange(
            slug="test-slug",
            change_type=ReportChangeType.NEW_REPORT_DATE,
            stored=stored,
            incoming=incoming,
        )
        assert change.slug == "test-slug"
        assert change.change_type is ReportChangeType.NEW_REPORT_DATE
        assert change.stored is stored
        assert change.incoming is incoming


# ===========================================================================
# ReportMonitor._detect_changes
# ===========================================================================

class TestDetectChanges:

    # ------------------------------------------------------------------
    # Test 6 – No changes returns empty list
    # Name: Identical reports produce no changes
    # Description: When all three monitored fields are unchanged, detect_changes
    #              should return an empty list.
    # Steps: Pass two identical LatestReport objects.
    # Expected: []
    # ------------------------------------------------------------------
    def test_no_change_returns_empty_list(self, monitor, stored):
        result = monitor._detect_changes(stored, make_report())
        assert result == []

    # ------------------------------------------------------------------
    # Test 7 – report_date change → NEW_REPORT_DATE
    # Name: report_date change detected
    # Description: A different report_date should produce exactly one
    #              NEW_REPORT_DATE change.
    # Steps: Pass incoming with a different report_date.
    # Expected: [ReportChange(..., NEW_REPORT_DATE, ...)]
    # ------------------------------------------------------------------
    def test_report_date_change_returns_new_report_date(self, monitor, stored):
        incoming = make_report(report_date="01/22/2024")
        result = monitor._detect_changes(stored, incoming)
        assert len(result) == 1
        assert result[0].change_type is ReportChangeType.NEW_REPORT_DATE

    # ------------------------------------------------------------------
    # Test 8 – published_date change → PUBLISHED_DATE_UPDATED
    # Name: published_date change detected
    # Description: Same report_date but a different published_date should
    #              produce exactly one PUBLISHED_DATE_UPDATED change.
    # Steps: Pass incoming with a different published_date only.
    # Expected: [ReportChange(..., PUBLISHED_DATE_UPDATED, ...)]
    # ------------------------------------------------------------------
    def test_published_date_change_returns_published_date_updated(self, monitor, stored):
        incoming = make_report(published_date="01/15/2024 14:00:00")
        result = monitor._detect_changes(stored, incoming)
        assert len(result) == 1
        assert result[0].change_type is ReportChangeType.PUBLISHED_DATE_UPDATED

    # ------------------------------------------------------------------
    # Test 9 – report_status change → STATUS_CHANGED
    # Name: report_status change detected
    # Description: Same report_date and published_date but a different
    #              report_status should produce exactly one STATUS_CHANGED change.
    # Steps: Pass incoming with a different report_status only.
    # Expected: [ReportChange(..., STATUS_CHANGED, ...)]
    # ------------------------------------------------------------------
    def test_status_change_returns_status_changed(self, monitor, stored):
        incoming = make_report(report_status="Preliminary")
        result = monitor._detect_changes(stored, incoming)
        assert len(result) == 1
        assert result[0].change_type is ReportChangeType.STATUS_CHANGED

    # ------------------------------------------------------------------
    # Test 10 – published_date + status both change → both events returned
    # Name: Concurrent published_date and status change
    # Description: When both published_date and report_status change (but
    #              not report_date), both events should be returned.
    # Steps: Pass incoming with both published_date and report_status changed.
    # Expected: Two changes; one PUBLISHED_DATE_UPDATED, one STATUS_CHANGED.
    # ------------------------------------------------------------------
    def test_published_and_status_change_returns_both(self, monitor, stored):
        incoming = make_report(
            published_date="01/15/2024 14:00:00",
            report_status="Preliminary",
        )
        result = monitor._detect_changes(stored, incoming)
        change_types = {c.change_type for c in result}
        assert change_types == {
            ReportChangeType.PUBLISHED_DATE_UPDATED,
            ReportChangeType.STATUS_CHANGED,
        }

    # ------------------------------------------------------------------
    # Test 11 – report_date change suppresses PUBLISHED_DATE_UPDATED
    # Name: NEW_REPORT_DATE takes priority over PUBLISHED_DATE_UPDATED
    # Description: When report_date changes, an also-changed published_date
    #              should not produce a separate PUBLISHED_DATE_UPDATED event.
    # Steps: Pass incoming with both report_date and published_date changed.
    # Expected: Exactly one change of type NEW_REPORT_DATE.
    # ------------------------------------------------------------------
    def test_report_date_change_suppresses_published_date_event(self, monitor, stored):
        incoming = make_report(report_date="01/22/2024", published_date="01/22/2024 08:00:00")
        result = monitor._detect_changes(stored, incoming)
        assert len(result) == 1
        assert result[0].change_type is ReportChangeType.NEW_REPORT_DATE

    # ------------------------------------------------------------------
    # Test 12 – report_date change suppresses STATUS_CHANGED
    # Name: NEW_REPORT_DATE takes priority over STATUS_CHANGED
    # Description: When report_date changes, an also-changed report_status
    #              should not produce a separate STATUS_CHANGED event.
    # Steps: Pass incoming with both report_date and report_status changed.
    # Expected: Exactly one change of type NEW_REPORT_DATE.
    # ------------------------------------------------------------------
    def test_report_date_change_suppresses_status_event(self, monitor, stored):
        incoming = make_report(report_date="01/22/2024", report_status="Preliminary")
        result = monitor._detect_changes(stored, incoming)
        assert len(result) == 1
        assert result[0].change_type is ReportChangeType.NEW_REPORT_DATE

    # ------------------------------------------------------------------
    # Test 13 – Change carries stored and incoming references
    # Name: ReportChange holds correct stored/incoming objects
    # Description: The returned ReportChange should reference the exact
    #              stored and incoming LatestReport instances passed in.
    # Steps: Call _detect_changes; inspect change.stored and change.incoming.
    # Expected: change.stored is stored; change.incoming is incoming
    # ------------------------------------------------------------------
    def test_change_carries_stored_and_incoming_references(self, monitor, stored):
        incoming = make_report(report_date="01/22/2024")
        result = monitor._detect_changes(stored, incoming)
        assert result[0].stored is stored
        assert result[0].incoming is incoming

    # ------------------------------------------------------------------
    # Test 14 – Change carries the correct slug
    # Name: ReportChange.slug matches stored.slug
    # Description: The slug on the returned change should come from the
    #              stored report's slug attribute.
    # Steps: Call _detect_changes; inspect change.slug.
    # Expected: change.slug == stored.slug
    # ------------------------------------------------------------------
    def test_change_carries_correct_slug(self, monitor, stored):
        incoming = make_report(report_date="01/22/2024")
        result = monitor._detect_changes(stored, incoming)
        assert result[0].slug == stored.slug


# ===========================================================================
# ReportMonitor._dispatch
# ===========================================================================

class TestDispatch:

    @pytest.fixture(autouse=True)
    def patch_handlers(self, monitor):
        monitor._on_new_report_date = AsyncMock()
        monitor._on_published_date_updated = AsyncMock()
        monitor._on_status_changed = AsyncMock()

    @pytest.fixture
    def make_change(self, stored, incoming):
        def _make(change_type: ReportChangeType) -> ReportChange:
            return ReportChange("test-slug", change_type, stored, incoming)
        return _make

    # ------------------------------------------------------------------
    # Test 15 – NEW_REPORT_DATE routes to _on_new_report_date
    # Name: Dispatch routes NEW_REPORT_DATE correctly
    # Description: A change of type NEW_REPORT_DATE should call only
    #              _on_new_report_date with the change object.
    # Steps: Call _dispatch with a NEW_REPORT_DATE change.
    # Expected: _on_new_report_date called once; others not called.
    # ------------------------------------------------------------------
    async def test_routes_new_report_date(self, monitor, make_change):
        change = make_change(ReportChangeType.NEW_REPORT_DATE)
        await monitor._dispatch(change)
        monitor._on_new_report_date.assert_called_once_with(change)
        monitor._on_published_date_updated.assert_not_called()
        monitor._on_status_changed.assert_not_called()

    # ------------------------------------------------------------------
    # Test 16 – PUBLISHED_DATE_UPDATED routes to _on_published_date_updated
    # Name: Dispatch routes PUBLISHED_DATE_UPDATED correctly
    # Description: A change of type PUBLISHED_DATE_UPDATED should call only
    #              _on_published_date_updated.
    # Steps: Call _dispatch with a PUBLISHED_DATE_UPDATED change.
    # Expected: _on_published_date_updated called once; others not called.
    # ------------------------------------------------------------------
    async def test_routes_published_date_updated(self, monitor, make_change):
        change = make_change(ReportChangeType.PUBLISHED_DATE_UPDATED)
        await monitor._dispatch(change)
        monitor._on_published_date_updated.assert_called_once_with(change)
        monitor._on_new_report_date.assert_not_called()
        monitor._on_status_changed.assert_not_called()

    # ------------------------------------------------------------------
    # Test 17 – STATUS_CHANGED routes to _on_status_changed
    # Name: Dispatch routes STATUS_CHANGED correctly
    # Description: A change of type STATUS_CHANGED should call only
    #              _on_status_changed.
    # Steps: Call _dispatch with a STATUS_CHANGED change.
    # Expected: _on_status_changed called once; others not called.
    # ------------------------------------------------------------------
    async def test_routes_status_changed(self, monitor, make_change):
        change = make_change(ReportChangeType.STATUS_CHANGED)
        await monitor._dispatch(change)
        monitor._on_status_changed.assert_called_once_with(change)
        monitor._on_new_report_date.assert_not_called()
        monitor._on_published_date_updated.assert_not_called()

    # ------------------------------------------------------------------
    # Test 18 – _dispatch logs the change
    # Name: _dispatch emits an info log
    # Description: Each dispatched change should produce a log entry that
    #              includes the slug and change type.
    # Steps: Patch logger; call _dispatch; inspect log call.
    # Expected: logger.info called at least once with slug and change type.
    # ------------------------------------------------------------------
    async def test_logs_change_info(self, monitor, make_change):
        change = make_change(ReportChangeType.NEW_REPORT_DATE)
        with patch("app.services.report_monitor.logger") as mock_logger:
            await monitor._dispatch(change)
        mock_logger.info.assert_called_once()
        call_kwargs = mock_logger.info.call_args[1]
        assert call_kwargs["slug"] == "test-slug"
        assert call_kwargs["change"] == ReportChangeType.NEW_REPORT_DATE.value


# ===========================================================================
# ReportMonitor._load_stored_reports
# ===========================================================================

class TestLoadStoredReports:

    def _make_session(self, reports: list[LatestReport]) -> AsyncMock:
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = reports
        session.execute = AsyncMock(return_value=result)
        return session

    # ------------------------------------------------------------------
    # Test 19 – Returns reports keyed by slug
    # Name: _load_stored_reports returns dict keyed by slug
    # Description: Each LatestReport in the DB should be accessible by its
    #              slug in the returned dict.
    # Steps: Mock session to return two reports; call _load_stored_reports.
    # Expected: dict with each slug mapping to the correct LatestReport.
    # ------------------------------------------------------------------
    async def test_returns_reports_keyed_by_slug(self):
        report1 = make_report(slug_id="slug-1")
        report2 = make_report(slug_id="slug-2")
        session = self._make_session([report1, report2])
        monitor = ReportMonitor(api_client=AsyncMock(), session=session)

        result = await monitor._load_stored_reports()

        assert result == {"slug-1": report1, "slug-2": report2}

    # ------------------------------------------------------------------
    # Test 20 – Returns empty dict when no stored reports
    # Name: _load_stored_reports with empty table
    # Description: When there are no LatestReport rows in the DB, the
    #              method should return an empty dict.
    # Steps: Mock session to return []; call _load_stored_reports.
    # Expected: {}
    # ------------------------------------------------------------------
    async def test_returns_empty_dict_when_no_reports(self):
        session = self._make_session([])
        monitor = ReportMonitor(api_client=AsyncMock(), session=session)

        result = await monitor._load_stored_reports()

        assert result == {}

    # ------------------------------------------------------------------
    # Test 21 – Calls session.execute once
    # Name: _load_stored_reports calls session.execute
    # Description: The method must issue exactly one DB query via
    #              session.execute.
    # Steps: Call _load_stored_reports; verify execute called once.
    # Expected: session.execute called exactly once.
    # ------------------------------------------------------------------
    async def test_calls_session_execute_once(self):
        session = self._make_session([])
        monitor = ReportMonitor(api_client=AsyncMock(), session=session)

        await monitor._load_stored_reports()

        session.execute.assert_called_once()


# ===========================================================================
# ReportMonitor.run_cycle
# ===========================================================================

class TestRunCycle:

    # ------------------------------------------------------------------
    # Test 22 – Skips incoming reports with no matching stored record
    # Name: run_cycle skips untracked slugs
    # Description: If an incoming report's slug has no entry in the DB,
    #              _dispatch should not be called for it.
    # Steps: Return an incoming report whose slug is absent from stored_map;
    #        verify _dispatch is never called.
    # Expected: _dispatch not called.
    # ------------------------------------------------------------------
    async def test_skips_untracked_slugs(self):
        incoming = make_report(slug_id="unknown")
        monitor = ReportMonitor(api_client=AsyncMock(), session=AsyncMock())
        monitor.api_client.fetch_current_reports = AsyncMock(return_value=[incoming])
        monitor._load_stored_reports = AsyncMock(return_value={})
        monitor._dispatch = AsyncMock()

        await monitor.run_cycle()

        monitor._dispatch.assert_not_called()

    # ------------------------------------------------------------------
    # Test 23 – Dispatches when a change is detected
    # Name: run_cycle dispatches detected changes
    # Description: When report_date changes, _dispatch should be called
    #              once with a NEW_REPORT_DATE change.
    # Steps: Return an incoming with a new report_date; verify dispatch call.
    # Expected: _dispatch called once; change type is NEW_REPORT_DATE.
    # ------------------------------------------------------------------
    async def test_dispatches_when_change_detected(self):
        stored = make_report()
        incoming = make_report(report_date="01/22/2024")
        monitor = ReportMonitor(api_client=AsyncMock(), session=AsyncMock())
        monitor.api_client.fetch_current_reports = AsyncMock(return_value=[incoming])
        monitor._load_stored_reports = AsyncMock(return_value={stored.slug: stored})
        monitor._dispatch = AsyncMock()

        await monitor.run_cycle()

        monitor._dispatch.assert_called_once()
        change = monitor._dispatch.call_args[0][0]
        assert change.change_type is ReportChangeType.NEW_REPORT_DATE

    # ------------------------------------------------------------------
    # Test 24 – Does not dispatch when nothing changed
    # Name: run_cycle does not dispatch for unchanged reports
    # Description: If the incoming report is identical to the stored one,
    #              _dispatch should not be called.
    # Steps: Return matching stored and incoming reports; verify dispatch
    #        is not called.
    # Expected: _dispatch not called.
    # ------------------------------------------------------------------
    async def test_does_not_dispatch_when_no_change(self):
        stored = make_report()
        incoming = make_report()
        monitor = ReportMonitor(api_client=AsyncMock(), session=AsyncMock())
        monitor.api_client.fetch_current_reports = AsyncMock(return_value=[incoming])
        monitor._load_stored_reports = AsyncMock(return_value={stored.slug: stored})
        monitor._dispatch = AsyncMock()

        await monitor.run_cycle()

        monitor._dispatch.assert_not_called()

    # ------------------------------------------------------------------
    # Test 25 – Handles multiple incoming reports independently
    # Name: run_cycle processes multiple reports
    # Description: Each incoming report should be compared against its own
    #              stored counterpart; dispatch called once per change.
    # Steps: Return two incoming reports each with a new report_date.
    # Expected: _dispatch called twice.
    # ------------------------------------------------------------------
    async def test_handles_multiple_incoming_reports(self):
        stored1 = make_report(slug_id="slug-1")
        stored2 = make_report(slug_id="slug-2")
        incoming1 = make_report(slug_id="slug-1", report_date="01/22/2024")
        incoming2 = make_report(slug_id="slug-2", report_date="01/22/2024")
        monitor = ReportMonitor(api_client=AsyncMock(), session=AsyncMock())
        monitor.api_client.fetch_current_reports = AsyncMock(return_value=[incoming1, incoming2])
        monitor._load_stored_reports = AsyncMock(return_value={"slug-1": stored1, "slug-2": stored2})
        monitor._dispatch = AsyncMock()

        await monitor.run_cycle()

        assert monitor._dispatch.call_count == 2

    # ------------------------------------------------------------------
    # Test 26 – Calls fetch_current_reports once per cycle
    # Name: run_cycle calls the API exactly once
    # Description: A single run_cycle call should result in exactly one
    #              fetch_current_reports call.
    # Steps: Run a cycle with an empty API response; check call count.
    # Expected: fetch_current_reports called once.
    # ------------------------------------------------------------------
    async def test_fetches_current_reports_from_api(self):
        monitor = ReportMonitor(api_client=AsyncMock(), session=AsyncMock())
        monitor.api_client.fetch_current_reports = AsyncMock(return_value=[])
        monitor._load_stored_reports = AsyncMock(return_value={})

        await monitor.run_cycle()

        monitor.api_client.fetch_current_reports.assert_called_once()


# ===========================================================================
# ReportMonitor._on_status_changed
# ===========================================================================

class TestOnStatusChanged:

    # ------------------------------------------------------------------
    # Test 27 – Logs the status transition
    # Name: _on_status_changed logs from_status and to_status
    # Description: The handler should log an info message that includes the
    #              slug and both the old and new report_status values.
    # Steps: Build a STATUS_CHANGED change (preliminary → final); call the
    #        handler with a patched logger; inspect the log call.
    # Expected: logger.info called with slug, from_status, and to_status.
    # ------------------------------------------------------------------
    async def test_logs_status_transition(self, monitor):
        old_report = make_report(report_status="Preliminary")
        new_report = make_report(report_status="Final")
        change = ReportChange("test-slug", ReportChangeType.STATUS_CHANGED, old_report, new_report)

        with patch("app.services.report_monitor.logger") as mock_logger:
            await monitor._on_status_changed(change)

        mock_logger.info.assert_called_once()
        call_kwargs = mock_logger.info.call_args[1]
        assert call_kwargs["slug"] == "test-slug"
        assert call_kwargs["from_status"] == ReportStatusOptions.PRELIMINARY.value
        assert call_kwargs["to_status"] == ReportStatusOptions.FINAL.value
