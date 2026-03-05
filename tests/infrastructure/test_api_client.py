from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from app.domain.models.schemas import IncomingReport, ReportResponse
from app.infrastructure.api_client import APIClient, BaseAPIClient, QueryBuilder
from app.utils.enums import MarketType
from app.utils.exceptions import APIClientError, ReportNotFoundError


# ---------------------------------------------------------------------------
# Shared fixtures / sample data
# ---------------------------------------------------------------------------

INCOMING_REPORT_DATA = {
    "slug_id": "2497",
    "report_date": "01/15/2024",
    "published_date": "01/15/2024 10:00:00",
    "report_status": "Final",
    "market_types": ["Auction Livestock"],
    "hasCorrectionsInLastThreeDays": False,
}

REPORT_DETAIL_DATA = {
    "report_date": "01/15/2024",
    "report_end_date": "01/15/2024",
    "published_date": "01/15/2024 10:00:00",
    "head_count": 150,
    "avg_weight": 850.5,
    "avg_price": 175.0,
    "region_name": None,
}

REPORT_RESPONSE_DATA = {
    "results": [REPORT_DETAIL_DATA],
    "stats": {"returnedRows": 1},
}


def _make_mock_session(return_value, raise_for_status_effect=None):
    """Build a mock aiohttp session whose .get() context manager returns return_value."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(side_effect=raise_for_status_effect)
    mock_response.json = AsyncMock(return_value=return_value)

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_cm)
    return mock_session, mock_response


# ---------------------------------------------------------------------------
# QueryBuilder
# ---------------------------------------------------------------------------

class TestQueryBuilder:

    def test_base_filters_contains_expected_constraints(self):
        f = QueryBuilder._BASE_FILTERS
        assert "class=Steers" in f
        assert "frame=Medium and Large" in f
        assert "muscle_grade=1-2,1" in f
        assert "freight=F.O.B." in f

    def test_market_filters_defined_for_all_market_types(self):
        for market_type in MarketType:
            assert market_type in QueryBuilder._MARKET_FILTERS

    def test_build_prepends_base_filters(self):
        for market_type in MarketType:
            result = QueryBuilder.build(market_type)
            assert result.startswith(QueryBuilder._BASE_FILTERS)

    def test_build_live_appends_correct_filters(self):
        result = QueryBuilder.build(MarketType.LIVE)
        assert result == QueryBuilder._BASE_FILTERS + QueryBuilder._MARKET_FILTERS[MarketType.LIVE]

    def test_build_video_appends_correct_filters(self):
        result = QueryBuilder.build(MarketType.VIDEO)
        assert result == QueryBuilder._BASE_FILTERS + QueryBuilder._MARKET_FILTERS[MarketType.VIDEO]

    def test_build_direct_appends_correct_filters(self):
        result = QueryBuilder.build(MarketType.DIRECT)
        assert result == QueryBuilder._BASE_FILTERS + QueryBuilder._MARKET_FILTERS[MarketType.DIRECT]


# ---------------------------------------------------------------------------
# BaseAPIClient
# ---------------------------------------------------------------------------

class TestBaseAPIClientContextManager:

    async def test_aenter_creates_session_with_basic_auth(self):
        client = BaseAPIClient("https://example.com", "mykey")
        with patch("app.infrastructure.api_client.aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = MagicMock()
            result = await client.__aenter__()

        assert result is client
        assert client.session is mock_cls.return_value
        mock_cls.assert_called_once()
        auth_arg = mock_cls.call_args.kwargs["auth"]
        assert isinstance(auth_arg, aiohttp.BasicAuth)
        assert auth_arg.login == "mykey"

    async def test_aexit_closes_session(self):
        client = BaseAPIClient("https://example.com", "key")
        mock_session = AsyncMock()
        client.session = mock_session

        await client.__aexit__(None, None, None)

        mock_session.close.assert_awaited_once()

    async def test_aexit_safe_when_session_is_none(self):
        client = BaseAPIClient("https://example.com", "key")
        await client.__aexit__(None, None, None)  # should not raise


class TestBaseAPIClientGet:

    async def test_raises_runtime_error_without_session(self):
        client = BaseAPIClient("https://example.com", "key")
        with pytest.raises(RuntimeError, match="Session not initialized"):
            await client._get("https://example.com/api")

    async def test_returns_json_on_success(self):
        client = BaseAPIClient("https://example.com", "key")
        mock_session, _ = _make_mock_session({"ok": True})
        client.session = mock_session

        result = await client._get("https://example.com/api")

        assert result == {"ok": True}

    async def test_calls_raise_for_status(self):
        client = BaseAPIClient("https://example.com", "key")
        mock_session, mock_response = _make_mock_session({})
        client.session = mock_session

        await client._get("https://example.com/api")

        mock_response.raise_for_status.assert_called_once()

    async def test_passes_params_to_session_get(self):
        client = BaseAPIClient("https://example.com", "key")
        mock_session, _ = _make_mock_session({})
        client.session = mock_session

        params = {"foo": "bar"}
        await client._get("https://example.com/api", params=params)

        call_kwargs = mock_session.get.call_args
        assert call_kwargs.kwargs.get("params") == params

    async def test_propagates_http_error(self):
        client = BaseAPIClient("https://example.com", "key")
        mock_session, _ = _make_mock_session(
            {},
            raise_for_status_effect=aiohttp.ClientResponseError(
                MagicMock(), MagicMock(), status=404
            ),
        )
        client.session = mock_session

        with pytest.raises(aiohttp.ClientResponseError):
            await client._get("https://example.com/api")


# ---------------------------------------------------------------------------
# APIClient.__init__
# ---------------------------------------------------------------------------

class TestAPIClientInit:

    def test_endpoint_built_from_base_url_and_version(self):
        client = APIClient(
            base_url="https://api.example.com",
            api_version="v1.1",
            api_key="key",
        )
        assert client.endpoint == "https://api.example.com/v1.1/reports"

    def test_uses_settings_defaults(self):
        from app.config import settings

        client = APIClient()
        assert client.base_url == settings.MMN_BASE_URL
        assert client.api_key == settings.MMN_API_KEY


# ---------------------------------------------------------------------------
# APIClient._calculate_last_days / _build_report_params
# ---------------------------------------------------------------------------

class TestCalculateLastDays:

    def test_returns_correct_number_of_days(self):
        prev = date.today() - timedelta(days=7)
        assert APIClient._calculate_last_days(prev) == 7

    def test_returns_zero_for_today(self):
        assert APIClient._calculate_last_days(date.today()) == 0

    def test_returns_one_for_yesterday(self):
        assert APIClient._calculate_last_days(date.today() - timedelta(days=1)) == 1


class TestBuildReportParams:

    @pytest.fixture
    def client(self):
        return APIClient(base_url="https://x.com", api_version="v1", api_key="k")

    def test_contains_last_days_and_q(self, client):
        prev = date.today() - timedelta(days=3)
        params = client._build_report_params(MarketType.LIVE, prev)
        assert "lastDays" in params
        assert "q" in params

    def test_last_days_value_is_correct(self, client):
        prev = date.today() - timedelta(days=5)
        params = client._build_report_params(MarketType.LIVE, prev)
        assert params["lastDays"] == 5

    def test_q_matches_query_builder(self, client):
        prev = date.today() - timedelta(days=1)
        for market_type in MarketType:
            params = client._build_report_params(market_type, prev)
            assert params["q"] == QueryBuilder.build(market_type)


# ---------------------------------------------------------------------------
# APIClient.fetch_current_reports
# ---------------------------------------------------------------------------

class TestFetchCurrentReports:

    @pytest.fixture
    def client(self):
        return APIClient(base_url="https://x.com", api_version="v1", api_key="k")

    async def test_returns_dict_keyed_by_slug(self, client):
        with patch.object(client, "_get", AsyncMock(return_value=[INCOMING_REPORT_DATA])):
            result = await client.fetch_current_reports()
        assert "2497" in result

    async def test_values_are_incoming_report_instances(self, client):
        with patch.object(client, "_get", AsyncMock(return_value=[INCOMING_REPORT_DATA])):
            result = await client.fetch_current_reports()
        assert isinstance(result["2497"], IncomingReport)

    async def test_multiple_reports_keyed_correctly(self, client):
        data = [
            {**INCOMING_REPORT_DATA, "slug_id": "100"},
            {**INCOMING_REPORT_DATA, "slug_id": "200"},
        ]
        with patch.object(client, "_get", AsyncMock(return_value=data)):
            result = await client.fetch_current_reports()
        assert set(result.keys()) == {"100", "200"}

    async def test_raises_api_client_error_on_client_error(self, client):
        with patch.object(
            client, "_get", AsyncMock(side_effect=aiohttp.ClientError("fail"))
        ):
            with pytest.raises(APIClientError):
                await client.fetch_current_reports()

    async def test_returns_empty_list_on_non_list_response(self, client):
        with patch.object(client, "_get", AsyncMock(return_value={"unexpected": "dict"})):
            result = await client.fetch_current_reports()
        assert result == []

    async def test_calls_correct_endpoint(self, client):
        mock_get = AsyncMock(return_value=[])
        with patch.object(client, "_get", mock_get):
            await client.fetch_current_reports()
        mock_get.assert_awaited_once_with(client.endpoint)


# ---------------------------------------------------------------------------
# APIClient.fetch_report_details
# ---------------------------------------------------------------------------

class TestFetchReportDetails:

    @pytest.fixture
    def client(self):
        return APIClient(base_url="https://x.com", api_version="v1", api_key="k")

    async def test_returns_report_response(self, client):
        with patch.object(client, "_get", AsyncMock(return_value=REPORT_RESPONSE_DATA)):
            result = await client.fetch_report_details("2497", MarketType.LIVE, date(2024, 1, 1))
        assert isinstance(result, ReportResponse)

    async def test_url_contains_slug_and_report_details(self, client):
        captured = {}

        async def mock_get(url, params=None):
            captured["url"] = url
            return REPORT_RESPONSE_DATA

        with patch.object(client, "_get", mock_get):
            await client.fetch_report_details("my-slug", MarketType.LIVE, date(2024, 1, 1))

        assert "my-slug" in captured["url"]
        assert "Report Details" in captured["url"]

    async def test_passes_params_to_get(self, client):
        captured = {}

        async def mock_get(url, params=None):
            captured["params"] = params
            return REPORT_RESPONSE_DATA

        with patch.object(client, "_get", mock_get):
            await client.fetch_report_details("slug", MarketType.LIVE, date(2024, 1, 1))

        assert "lastDays" in captured["params"]
        assert "q" in captured["params"]

    async def test_raises_api_client_error_on_client_error(self, client):
        with patch.object(
            client, "_get", AsyncMock(side_effect=aiohttp.ClientError("fail"))
        ):
            with pytest.raises(APIClientError):
                await client.fetch_report_details("slug", MarketType.LIVE, date(2024, 1, 1))

    async def test_raises_report_not_found_on_non_dict_response(self, client):
        with patch.object(client, "_get", AsyncMock(return_value=[{"not": "a dict"}])):
            with pytest.raises(ReportNotFoundError):
                await client.fetch_report_details("slug", MarketType.LIVE, date(2024, 1, 1))

    async def test_report_response_row_count(self, client):
        with patch.object(client, "_get", AsyncMock(return_value=REPORT_RESPONSE_DATA)):
            result = await client.fetch_report_details("slug", MarketType.LIVE, date(2024, 1, 1))
        assert result.row_count == 1
