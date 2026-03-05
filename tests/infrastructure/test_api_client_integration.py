from datetime import date, timedelta

import aiohttp
import pytest
from loguru import logger
from app.domain.models.schemas import IncomingReport, ReportResponse
from app.infrastructure.api_client import APIClient
from app.utils.enums import MarketType
from app.utils.exceptions import APIClientError, ReportNotFoundError

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.integration
class TestFetchCurrentReportsIntegration:

    async def test_returns_non_empty_dict(self):
        async with APIClient() as client:
            result = await client.fetch_current_reports()
        assert isinstance(result, dict)
        assert len(result) > 0

    async def test_values_are_incoming_report_instances(self):
        async with APIClient() as client:
            result = await client.fetch_current_reports()
        assert all(isinstance(r, IncomingReport) for r in result.values())

    async def test_slugs_are_strings(self):
        async with APIClient() as client:
            result = await client.fetch_current_reports()
        assert all(isinstance(slug, str) for slug in result.keys())

    async def test_reports_have_valid_dates(self):
        async with APIClient() as client:
            result = await client.fetch_current_reports()
        for report in result.values():
            assert isinstance(report.report_date, date)
            assert isinstance(report.published_date.date(), date)


@pytest.mark.integration
class TestFetchReportDetailsIntegration:

    @pytest.fixture(scope="class")
    async def reports(self):
        async with APIClient() as client:
            return await client.fetch_current_reports()

    async def test_live_market_returns_report_response(self, reports):
        live = [r for r in reports.values() if r.market_type == MarketType.LIVE]
        if not live:
            pytest.skip("No LIVE market reports available")
        report = live[0]
        prev_date = report.report_date - timedelta(days=7)
        async with APIClient() as client:
            result = await client.fetch_report_details(report.slug, MarketType.LIVE, prev_date)
        assert isinstance(result, ReportResponse)

    async def test_video_market_returns_report_response(self, reports):
        video = [r for r in reports.values() if r.market_type == MarketType.VIDEO]
        if not video:
            pytest.skip("No VIDEO market reports available")
        report = video[0]
        logger.info("Testing VIDEO market report details", slug=report.slug, report_date=report.report_date, published_date=report.published_date)
        prev_date = report.report_date - timedelta(days=7)
        async with APIClient() as client:
            result = await client.fetch_report_details(report.slug, MarketType.VIDEO, prev_date)
        assert isinstance(result, ReportResponse)

    async def test_direct_market_returns_report_response(self, reports):
        direct = [r for r in reports.values() if r.market_type == MarketType.DIRECT]
        if not direct:
            pytest.skip("No DIRECT market reports available")
        report = direct[0]
        logger.info("Testing DIRECT market report details", slug=report.slug, report_date=report.report_date, published_date=report.published_date)
        prev_date = report.report_date - timedelta(days=7)
        async with APIClient() as client:
            result = await client.fetch_report_details(report.slug, MarketType.DIRECT, prev_date)
        assert isinstance(result, ReportResponse)

    async def test_result_has_stats_and_results(self, reports):
        available = [r for r in reports.values() if r.market_type is not None]
        if not available:
            pytest.skip("No reports with a recognized market type")
        report = available[0]
        prev_date = report.report_date - timedelta(days=7)
        async with APIClient() as client:
            result = await client.fetch_report_details(report.slug, report.market_type, prev_date)
        assert isinstance(result.results, list)
        assert isinstance(result.row_count, int)

    async def test_invalid_slug_raises(self):
        async with APIClient() as client:
            with pytest.raises((APIClientError, ReportNotFoundError)):
                await client.fetch_report_details(
                    "invalid-slug-that-does-not-exist",
                    MarketType.LIVE,
                    date.today() - timedelta(days=7),
                )


@pytest.mark.integration
class TestAPIClientContextManagerIntegration:

    async def test_session_is_none_before_entering(self):
        client = APIClient()
        assert client.session is None

    async def test_session_is_set_after_entering(self):
        async with APIClient() as client:
            assert client.session is not None

    async def test_session_is_closed_after_exiting(self):
        async with APIClient() as client:
            session = client.session
        assert session.connector is None or session.closed

    async def test_get_raises_without_context_manager(self):
        client = APIClient()
        with pytest.raises(RuntimeError, match="Session not initialized"):
            await client._get(client.endpoint)
