"""
Integration tests for ReportMonitor — require a live DB and API connection.

Run only these tests:
    pytest -m integration

Exclude from normal runs:
    pytest -m "not integration"
"""

import pytest

from app.domain.models import LatestReport
from app.infrastructure.api_client import APIClient
from app.infrastructure.database import AsyncSessionLocal
from app.services.report_monitor import ReportChange, ReportChangeType, ReportMonitor

pytestmark = pytest.mark.integration


# ===========================================================================
# Live API
# ===========================================================================

class TestLiveAPI:

    # ------------------------------------------------------------------
    # Test 1 – API returns a non-empty list of LatestReport objects
    # Name: fetch_current_reports returns valid LatestReport list
    # Description: A real call to the MMN API should return at least one
    #              report and every item should parse into a LatestReport.
    # Steps: Open a real APIClient session; call fetch_current_reports().
    # Expected: Non-empty list; all items are LatestReport instances.
    # ------------------------------------------------------------------
    async def test_fetch_current_reports_returns_latest_reports(self):
        async with APIClient() as client:
            reports = await client.fetch_current_reports()

        assert isinstance(reports, list)
        assert len(reports) > 0
        assert all(isinstance(r, LatestReport) for r in reports)

    # ------------------------------------------------------------------
    # Test 2 – Each report has required fields populated
    # Name: Live LatestReport objects have slug, report_date, report_status
    # Description: Every report returned by the API should have non-empty
    #              values for the three fields the CDC monitors.
    # Steps: Fetch reports; inspect slug, report_date, report_status,
    #        and published_date on each.
    # Expected: All fields truthy / not None.
    # ------------------------------------------------------------------
    async def test_reports_have_required_fields(self):
        async with APIClient() as client:
            reports = await client.fetch_current_reports()

        for report in reports:
            assert report.slug, f"slug is empty for report: {report}"
            assert report.report_date, f"report_date missing for slug {report.slug}"
            assert report.published_date, f"published_date missing for slug {report.slug}"
            assert report.report_status, f"report_status missing for slug {report.slug}"


# ===========================================================================
# Live DB
# ===========================================================================

class TestLiveDB:

    # ------------------------------------------------------------------
    # Test 3 – DB returns a dict of LatestReport records keyed by slug
    # Name: _load_stored_reports returns dict[str, LatestReport]
    # Description: The method should query the live DB and return every
    #              stored LatestReport row, keyed by slug.
    # Steps: Open a real session; call _load_stored_reports().
    # Expected: dict where keys are strings and values are LatestReport.
    # ------------------------------------------------------------------
    async def test_load_stored_reports_returns_dict(self):
        async with AsyncSessionLocal() as session:
            monitor = ReportMonitor(api_client=None, session=session)  # type: ignore[arg-type]
            stored = await monitor._load_stored_reports()

        assert isinstance(stored, dict)
        assert all(isinstance(k, str) for k in stored.keys())
        assert all(isinstance(v, LatestReport) for v in stored.values())

    # ------------------------------------------------------------------
    # Test 4 – Stored report slugs match auctions.slug format
    # Name: Stored slugs are non-empty strings
    # Description: Every slug key in the returned dict should be a
    #              non-empty string, consistent with the FK on auctions.
    # Steps: Load stored reports; inspect all keys.
    # Expected: All slugs are non-empty strings.
    # ------------------------------------------------------------------
    async def test_stored_report_slugs_are_non_empty(self):
        async with AsyncSessionLocal() as session:
            monitor = ReportMonitor(api_client=None, session=session)  # type: ignore[arg-type]
            stored = await monitor._load_stored_reports()

        for slug in stored:
            assert isinstance(slug, str) and slug.strip(), f"Blank slug found: {slug!r}"


# ===========================================================================
# Live end-to-end
# ===========================================================================

class TestLiveEndToEnd:

    # ------------------------------------------------------------------
    # Test 5 – Full run_cycle completes without error
    # Name: run_cycle runs end-to-end against live services
    # Description: A complete polling cycle against the real DB and API
    #              should not raise. Handlers are stubs so no data is
    #              written.
    # Steps: Open a real APIClient and session; call run_cycle().
    # Expected: No exception raised.
    # ------------------------------------------------------------------
    async def test_run_cycle_completes_without_error(self):
        async with APIClient() as api_client:
            async with AsyncSessionLocal() as session:
                monitor = ReportMonitor(api_client, session)
                await monitor.run_cycle()  # all handlers are pass — read-only

    # ------------------------------------------------------------------
    # Test 6 – Any detected changes are valid ReportChange objects
    # Name: detect_changes on live data produces well-formed changes
    # Description: For every incoming report that has a stored counterpart,
    #              _detect_changes should return only valid ReportChange
    #              objects with a known ReportChangeType.
    # Steps: Fetch incoming from API; load stored from DB; run
    #        _detect_changes for each matched slug; inspect results.
    # Expected: All changes are ReportChange with a valid change_type.
    # ------------------------------------------------------------------
    async def test_detected_changes_are_valid_report_changes(self):
        async with APIClient() as api_client:
            incoming_reports = await api_client.fetch_current_reports()

        async with AsyncSessionLocal() as session:
            monitor = ReportMonitor(api_client=None, session=session)  # type: ignore[arg-type]
            stored_map = await monitor._load_stored_reports()

        changes: list[ReportChange] = []
        for incoming in incoming_reports:
            stored = stored_map.get(incoming.slug)
            if stored is not None:
                changes.extend(monitor._detect_changes(stored, incoming))

        valid_types = set(ReportChangeType)
        for change in changes:
            assert isinstance(change, ReportChange), f"Not a ReportChange: {change!r}"
            assert change.change_type in valid_types, f"Unknown change_type: {change.change_type!r}"
            assert isinstance(change.stored, LatestReport)
            assert isinstance(change.incoming, LatestReport)
            assert change.slug == change.stored.slug == change.incoming.slug
