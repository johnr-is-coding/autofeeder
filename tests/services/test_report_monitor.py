import asyncio
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError

from app.domain.models import stored_report
from app.domain.models.report import Report
from app.domain.models.schemas import IncomingReport
from app.domain.models.stored_report import StoredReport
from app.infrastructure.api_client import APIClient
from app.infrastructure.transformers import ReportTransformer
from app.utils.enums import MarketType, ReportStatus
from app.utils.exceptions import APIClientError, DatabaseError, ServiceError, TransformerError
from app.services.report_monitor import ReportMonitor, ReportChange


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session
 
 
@pytest.fixture
def mock_api_client():
    return AsyncMock(spec=APIClient)
 
 
@pytest.fixture
def monitor(mock_api_client, mock_session):
    return ReportMonitor(api_client=mock_api_client, session=mock_session)


def make_stored_report(
        slug="1234",
        report_date=date(2024, 1, 1),
        published_date=date(2024, 1, 2),
        report_status=ReportStatus.FINAL,
        market_type=MarketType.LIVE
) -> MagicMock:
    stored_report = MagicMock(spec=StoredReport)
    stored_report.slug = slug
    stored_report.report_date = report_date
    stored_report.published_date = published_date
    stored_report.report_status = report_status
    stored_report.market_type = market_type
    return stored_report

def make_incoming_report(
        slug="1234",
        report_date=date(2024, 1, 1),
        published_date=date(2024, 1, 2),
        report_status=ReportStatus.FINAL,
        market_type=MarketType.LIVE,
        has_corrections=False,
) -> MagicMock:
    incoming_report = MagicMock(spec=IncomingReport)
    incoming_report.slug = slug
    incoming_report.report_date = report_date
    incoming_report.published_date = published_date
    incoming_report.report_status = report_status
    incoming_report.market_type = market_type
    incoming_report.has_corrections = has_corrections
    return incoming_report

def make_report(slug="1234") -> MagicMock:
    r = MagicMock(spec=Report)
    r.model_dump = MagicMock(return_value={
        "slug": slug,
        "report_end_date": date(2024, 1, 1)
    })
    return r

# ---------------------------------------------------------------------------
# _detect_changes
# ---------------------------------------------------------------------------
 
class TestDetectChanges:
    def test_no_changes_returns_false(self):
        stored = make_stored_report()
        incoming = make_incoming_report()
        assert ReportMonitor._detect_changes(stored, incoming) is False
 
    def test_report_date_changed(self):
        stored = make_stored_report(report_date=date(2024, 1, 1))
        incoming = make_incoming_report(report_date=date(2024, 1, 2))
        assert ReportMonitor._detect_changes(stored, incoming) is True
 
    def test_report_status_changed(self):
        stored = make_stored_report(report_status="preliminary")
        incoming = make_incoming_report(report_status="final")
        assert ReportMonitor._detect_changes(stored, incoming) is True
 
    def test_published_date_changed(self):
        stored = make_stored_report(published_date=date(2024, 1, 2))
        incoming = make_incoming_report(published_date=date(2024, 1, 3))
        assert ReportMonitor._detect_changes(stored, incoming) is True
 
    def test_multiple_fields_changed(self):
        stored = make_stored_report(report_date=date(2024, 1, 1), report_status="preliminary")
        incoming = make_incoming_report(report_date=date(2024, 1, 5), report_status="final")
        assert ReportMonitor._detect_changes(stored, incoming) is True
 
 
# ---------------------------------------------------------------------------
# _get_changes
# ---------------------------------------------------------------------------
 
class TestGetChanges:
    def test_returns_change_when_fields_differ(self, monitor):
        stored = make_stored_report(report_status="preliminary")
        incoming = make_incoming_report(report_status="final")
        result = monitor._get_changes([stored], {"1234": incoming})
        assert len(result) == 1
        assert result[0].slug == "1234"
        assert result[0].stored is stored
        assert result[0].incoming is incoming
 
    def test_no_changes_when_fields_identical(self, monitor):
        stored = make_stored_report()
        incoming = make_incoming_report()
        result = monitor._get_changes([stored], {"1234": incoming})
        assert result == []
 
    def test_skips_slug_missing_from_incoming_map(self, monitor):
        stored = make_stored_report(slug="ghost-slug")
        result = monitor._get_changes([stored], {})
        assert result == []
 
    def test_mixed_stored_reports(self, monitor):
        stored_changed = make_stored_report(slug="1234", report_status="preliminary")
        stored_unchanged = make_stored_report(slug="2345", report_status="final")
 
        incoming_a = make_incoming_report(slug="1234", report_status="final")
        incoming_b = make_incoming_report(slug="2345", report_status="final")
        incoming_c = make_incoming_report(slug="3456", report_status="preliminary")
 
        result = monitor._get_changes(
            [stored_changed, stored_unchanged],
            {
                "1234": incoming_a,
                "2345": incoming_b,
                "3456": incoming_c,
            },
        )
 
        assert len(result) == 1
        assert result[0].slug == "1234"
 
    def test_empty_stored_returns_empty(self, monitor):
        stored = []
        incoming = make_incoming_report(slug="1234", report_status="final")
        assert monitor._get_changes(stored, {"1234": incoming}) == []
 
    def test_empty_incoming_map_returns_empty(self, monitor):
        stored = make_stored_report(slug="1234", report_status="preliminary")
        incoming = {}
        assert monitor._get_changes([stored], incoming) == []
 
 
# ---------------------------------------------------------------------------
# _generate_reports
# ---------------------------------------------------------------------------

# NOTE: These tests focus on the orchestration logic of _generate_reports, 
# not the internal workings of the API client or transformer, which are 
# covered by their own unit tests.
# ---------------------------------------------------------------------------
 
class TestGenerateReports:
    @pytest.mark.asyncio
    async def test_returns_transformed_reports(self, monitor):
        report = make_report()
        api_response = MagicMock()
        api_response.results = [MagicMock()]
        monitor.api_client.fetch_report_details = AsyncMock(return_value=api_response)
        monitor.transformer.transform = MagicMock(return_value=[report])
 
        result = await monitor._generate_reports("1234", MarketType.LIVE)
 
        assert result == [report]
        monitor.api_client.fetch_report_details.assert_awaited_once_with("1234", MarketType.LIVE)
        monitor.transformer.transform.assert_called_once_with(api_response.results, "1234")
 
    @pytest.mark.asyncio
    async def test_api_error_raises_service_error(self, monitor):
        monitor.api_client.fetch_report_details = AsyncMock(
            side_effect=APIClientError("timeout")
        )
        with pytest.raises(ServiceError, match="1234"):
            await monitor._generate_reports("1234", MarketType.LIVE)
 
    @pytest.mark.asyncio
    async def test_transformer_error_raises_service_error(self, monitor):
        api_response = MagicMock()
        monitor.api_client.fetch_report_details = AsyncMock(return_value=api_response)
        monitor.transformer.transform = MagicMock(
            side_effect=TransformerError("bad data")
        )
 
        with pytest.raises(ServiceError, match="1234"):
            await monitor._generate_reports("1234", MarketType.LIVE)

    @pytest.mark.asyncio
    async def test_empty_api_results_returns_empty_list(self, monitor):
        api_response = MagicMock()
        api_response.results = []
        monitor.api_client.fetch_report_details = AsyncMock(return_value=api_response)
        monitor.transformer.transform = MagicMock(return_value=[])

        result = await monitor._generate_reports("1234", MarketType.LIVE)

        assert result == []
        monitor.transformer.transform.assert_called_once_with([], "1234")

 
# ---------------------------------------------------------------------------
# _persist_report_update
# ---------------------------------------------------------------------------
 
class TestPersistReportUpdate:
    @pytest.mark.asyncio
    async def test_executes_two_statements_and_commits(self, monitor, mock_session):
        reports = [make_report()]
        incoming = make_incoming_report()
 
        with patch("app.services.report_monitor.pg_insert") as mock_insert:
            mock_stmt = MagicMock()
            mock_stmt.on_conflict_do_update.return_value = mock_stmt
            mock_stmt.excluded = MagicMock()
            mock_insert.return_value = mock_stmt
 
            await monitor._persist_report_update(reports, incoming)
 
        assert mock_session.execute.await_count == 2
        mock_session.commit.assert_awaited_once()
        mock_session.rollback.assert_not_awaited()
 
    @pytest.mark.asyncio
    async def test_rolls_back_and_raises_database_error_on_sql_failure(
        self, monitor, mock_session
    ):
        mock_session.execute = AsyncMock(side_effect=SQLAlchemyError("constraint violation"))
        reports = [make_report()]
        incoming = make_incoming_report()
 
        with patch("app.services.report_monitor.pg_insert") as mock_insert:
            mock_stmt = MagicMock()
            mock_stmt.on_conflict_do_update.return_value = mock_stmt
            mock_stmt.excluded = MagicMock()
            mock_insert.return_value = mock_stmt
 
            with pytest.raises(DatabaseError, match="Failed to persist report update"):
                await monitor._persist_report_update(reports, incoming)
 
        mock_session.rollback.assert_awaited_once()
        mock_session.commit.assert_not_awaited()
 
 
# ---------------------------------------------------------------------------
# _load_stored_reports
# ---------------------------------------------------------------------------
 
class TestLoadStoredReports:
    @pytest.mark.asyncio
    async def test_returns_list_of_stored_reports(self, monitor, mock_session):
        stored = make_stored_report()
        scalar_result = MagicMock()
        scalar_result.unique.return_value.scalars.return_value.all.return_value = [stored]
        mock_session.execute = AsyncMock(return_value=scalar_result)
 
        result = await monitor._load_stored_reports()
 
        assert result == [stored]
 
    @pytest.mark.asyncio
    async def test_raises_database_error_on_sql_failure(self, monitor, mock_session):
        mock_session.execute = AsyncMock(side_effect=SQLAlchemyError("connection lost"))
 
        with pytest.raises(DatabaseError, match="Failed to load stored reports"):
            await monitor._load_stored_reports()
 
    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_rows(self, monitor, mock_session):
        scalar_result = MagicMock()
        scalar_result.unique.return_value.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=scalar_result)
 
        result = await monitor._load_stored_reports()
 
        assert result == []


# ---------------------------------------------------------------------------
# run_cycle — integration-level
# ---------------------------------------------------------------------------
 
class TestRunCycle:
    def _setup_load(self, monitor, mock_session, stored_reports):
        scalar_result = MagicMock()
        scalar_result.unique.return_value.scalars.return_value.all.return_value = stored_reports
        mock_session.execute = AsyncMock(return_value=scalar_result)

    @pytest.mark.asyncio
    async def test_no_changes_exits_early(self, monitor, mock_session):
        stored = make_stored_report()
        incoming = make_incoming_report()
        
        monitor.api_client.fetch_current_reports = AsyncMock(return_value={"1234": incoming})
        self._setup_load(monitor, mock_session, [stored])
 
        await monitor.run_cycle()
 
        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_successful_cycle_persists_all_changes(self, monitor, mock_session):
        stored_a = make_stored_report(slug="1234", report_status="preliminary")
        stored_b = make_stored_report(slug="2345", report_status="preliminary")
        incoming_a = make_incoming_report(slug="1234", report_status="final")
        incoming_b = make_incoming_report(slug="2345", report_status="final")
        incoming_c = make_incoming_report(slug="3456", report_status="final")
        report_a = make_report(slug="1234")
        report_b = make_report(slug="2345")

        monitor.api_client.fetch_current_reports = AsyncMock(
            return_value={"1234": incoming_a, "2345": incoming_b, "3456": incoming_c}
        )
        self._setup_load(monitor, mock_session, [stored_a, stored_b])

        async def fake_generate(slug, market_type):
            return [report_a] if slug == "1234" else [report_b]

        monitor._generate_reports = AsyncMock(side_effect=fake_generate)
        monitor._persist_report_update = AsyncMock()

        await monitor.run_cycle()

        assert monitor._persist_report_update.await_count == 2
        persisted_slugs = {c.args[1].slug for c in monitor._persist_report_update.await_args_list}
        assert persisted_slugs == {"1234", "2345"}

    @pytest.mark.asyncio
    async def test_gather_processes_all_changes_even_if_one_fails(self, monitor, mock_session):
        stored_a = make_stored_report(slug="1234", report_status="preliminary")
        stored_b = make_stored_report(slug="2345", report_status="preliminary")
        incoming_a = make_incoming_report(slug="1234", report_status="final")
        incoming_b = make_incoming_report(slug="2345", report_status="final")
        incoming_c = make_incoming_report(slug="3456", report_status="final")

        monitor.api_client.fetch_current_reports = AsyncMock(
            return_value={"1234": incoming_a, "2345": incoming_b, "3456": incoming_c}
        )
        self._setup_load(monitor, mock_session, [stored_a, stored_b])

        started = []

        async def fake_generate(slug, market_type):
            started.append(slug)
            await asyncio.sleep(0)
            if slug == "1234":
                raise ServiceError("failed to generate reports for 1234")
            return [make_report(slug=slug)]

        monitor._generate_reports = AsyncMock(side_effect=fake_generate)
        monitor._persist_report_update = AsyncMock()

        with pytest.raises(ServiceError, match="1234"):
            await monitor.run_cycle()

        assert sorted(started) == ["1234", "2345"]
        monitor._persist_report_update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_api_init_failure_raises_service_error(self, monitor):
        monitor.api_client.fetch_current_reports = AsyncMock(side_effect=APIClientError("service unavailable"))
 
        with pytest.raises(ServiceError, match="Failed to initialize report monitoring cycle"):
            await monitor.run_cycle()

    @pytest.mark.asyncio
    async def test_partial_failure_raises_service_error_with_slugs(
        self, monitor, mock_session
    ):
        stored_a = make_stored_report(slug="1234", report_status="preliminary")
        stored_b = make_stored_report(slug="2345", report_status="preliminary")
        incoming_a = make_incoming_report(slug="1234", report_status="final")
        incoming_b = make_incoming_report(slug="2345", report_status="final")
        incoming_c = make_incoming_report(slug="3456", report_status="final")

        monitor.api_client.fetch_current_reports = AsyncMock(
            return_value={"1234": incoming_a, "2345": incoming_b, "3456": incoming_c}
        )
        self._setup_load(monitor, mock_session, [stored_a, stored_b])
        monitor._generate_reports = AsyncMock(
            side_effect=[ServiceError("failed to generate reports for 2345"), [make_report(slug="2345")]]
        )
        monitor._persist_report_update = AsyncMock()

        with pytest.raises(ServiceError, match="Cycle completed with failed report updates for slugs: \\['1234'\\]"):
            await monitor.run_cycle()

        monitor._persist_report_update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_persist_failure_adds_slug_to_failed_list(self, monitor, mock_session):
        stored_report = make_stored_report(slug="1234", report_status="preliminary")
        incoming_report = make_incoming_report(slug="1234", report_status="final")

        monitor.api_client.fetch_current_reports = AsyncMock(
            return_value={"1234": incoming_report}
        )
        self._setup_load(monitor, mock_session, [stored_report])
        monitor._generate_reports = AsyncMock(
            return_value=[make_report(slug="1234")]
        )
        monitor._persist_report_update = AsyncMock(
            side_effect=DatabaseError("failed to persist update for 1234")
        )

        with pytest.raises(ServiceError, match="Cycle completed with failed report updates for slugs: \\['1234'\\]"):
            await monitor.run_cycle()

        monitor._persist_report_update.assert_awaited_once()
