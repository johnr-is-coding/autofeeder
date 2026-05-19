import pytest
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.api_client import APIClient, BaseAPIClient, QueryBuilder
from app.utils.enums import MarketType
from app.utils.exceptions import APIClientError, ReportNotFoundError

BASE_URL = "https://api.example.com"
API_VERSION = "v1"
API_KEY = "test-key"

RAW_INCOMING_REPORT = {
    "slug_id": "1234",
    "report_date": "03/19/2026",
    "published_date": "03/19/2026 08:00:00",
    "report_status": "Final",
    "market_types": ["Auction Livestock"],
    "hasCorrectionsInLastThreeDays": False,
}

RAW_REPORT_DETAIL = {
    "report_date": "03/19/2026",
    "report_end_date": "03/19/2026",
    "published_date": "03/19/2026 08:00:00",
    "final_ind": "Final",
    "head_count": 100,
    "avg_weight": 850.0,
    "avg_price": 150.0,
    "region_name": None,
}

RAW_REPORT_RESPONSE = {
    "results": [RAW_REPORT_DETAIL],
    "stats": {"returnedRows": 1},
}


@pytest.fixture
def client():
    return APIClient(base_url=BASE_URL, api_version=API_VERSION, api_key=API_KEY)


@pytest.fixture
def base_client():
    return BaseAPIClient(base_url=BASE_URL, api_key=API_KEY)


def make_mock_response(json_data=None, raise_on_status=None):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=json_data)
    mock_response.raise_for_status = MagicMock(
        side_effect=raise_on_status if raise_on_status else None
    )
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    return mock_response


# ---------------------------------------------------------------------------
# QueryBuilder
# ---------------------------------------------------------------------------

class TestQueryBuilder:
    def test_build_live_contains_live_weight_filter(self):
        result = QueryBuilder.build(MarketType.LIVE)
        assert "avg_weight=700:899;" in result

    def test_build_video_contains_video_filters(self):
        result = QueryBuilder.build(MarketType.VIDEO)
        assert "wtd_avg_wt=700:899;" in result
        assert "region_name=South Central,North Central;" in result

    def test_build_direct_contains_direct_filters(self):
        result = QueryBuilder.build(MarketType.DIRECT)
        assert "wtd_avg_wt=700:899;" in result
        assert "current=Yes;" in result

    def test_all_market_types_include_base_filters(self):
        base_params = [
            "class=Steers;",
            "frame=Medium and Large;",
            "muscle_grade=1-2,1;",
            "freight=F.O.B.;",
        ]
        for market_type in MarketType:
            result = QueryBuilder.build(market_type)
            for param in base_params:
                assert param in result, f"Missing {param!r} for {market_type}"

    def test_build_unsupported_market_type_raises(self):
        bad_type = MagicMock(spec=MarketType)
        bad_type.__repr__ = lambda _: "bad"
        with pytest.raises(APIClientError, match="Unsupported market type"):
            QueryBuilder.build(bad_type)


# ---------------------------------------------------------------------------
# BaseAPIClient
# ---------------------------------------------------------------------------

class TestBaseAPIClient:
    @pytest.mark.asyncio
    async def test_aenter_creates_session_with_basic_auth(self, base_client):
        with patch("app.infrastructure.api_client.aiohttp.ClientSession") as mock_cls:
            mock_session = MagicMock()
            mock_cls.return_value = mock_session

            result = await base_client.__aenter__()

            assert result is base_client
            assert base_client.session is mock_session
            call_kwargs = mock_cls.call_args.kwargs
            assert isinstance(call_kwargs["auth"], aiohttp.BasicAuth)
            assert call_kwargs["auth"].login == API_KEY

    @pytest.mark.asyncio
    async def test_aexit_closes_session(self, base_client):
        mock_session = AsyncMock()
        base_client.session = mock_session

        await base_client.__aexit__(None, None, None)

        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aexit_with_no_session_is_noop(self, base_client):
        # Should not raise
        await base_client.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_get_raises_runtime_error_without_session(self, base_client):
        with pytest.raises(RuntimeError, match="Session not initialized"):
            await base_client._get("https://api.example.com/resource")

    @pytest.mark.asyncio
    async def test_get_returns_json_on_success(self, base_client):
        expected = {"key": "value"}
        mock_response = make_mock_response(json_data=expected)
        base_client.session = MagicMock(get=MagicMock(return_value=mock_response))

        result = await base_client._get("https://api.example.com/resource", params={"k": "v"})

        assert result == expected

    @pytest.mark.asyncio
    async def test_get_reraises_on_client_error(self, base_client):
        mock_response = make_mock_response(
            raise_on_status=aiohttp.ClientResponseError(MagicMock(), ())
        )
        base_client.session = MagicMock(get=MagicMock(return_value=mock_response))

        with pytest.raises(aiohttp.ClientResponseError):
            await base_client._get("https://api.example.com/resource")


# ---------------------------------------------------------------------------
# APIClient.__init__
# ---------------------------------------------------------------------------

class TestAPIClientInit:
    def test_endpoint_is_built_from_base_url_and_version(self, client):
        assert client.endpoint == f"{BASE_URL}/{API_VERSION}/reports"

    def test_base_url_and_api_key_stored(self, client):
        assert client.base_url == BASE_URL
        assert client.api_key == API_KEY


# ---------------------------------------------------------------------------
# fetch_current_reports
# ---------------------------------------------------------------------------

class TestFetchCurrentReports:
    @pytest.mark.asyncio
    async def test_returns_dict_keyed_by_slug(self, client):
        client._get = AsyncMock(return_value=[RAW_INCOMING_REPORT])

        result = await client.fetch_current_reports()

        assert "1234" in result
        assert result["1234"].slug == "1234"

    @pytest.mark.asyncio
    async def test_multiple_reports_all_present(self, client):
        second = {**RAW_INCOMING_REPORT, "slug_id": "other-slug"}
        client._get = AsyncMock(return_value=[RAW_INCOMING_REPORT, second])

        result = await client.fetch_current_reports()

        assert set(result.keys()) == {"1234", "other-slug"}

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty_dict(self, client):
        client._get = AsyncMock(return_value=[])

        result = await client.fetch_current_reports()

        assert result == {}

    @pytest.mark.asyncio
    async def test_non_list_response_raises_api_client_error(self, client):
        client._get = AsyncMock(return_value={"not": "a list"})

        with pytest.raises(APIClientError, match="Expected report list"):
            await client.fetch_current_reports()

    @pytest.mark.asyncio
    async def test_client_error_raises_api_client_error(self, client):
        client._get = AsyncMock(side_effect=aiohttp.ClientError())

        with pytest.raises(APIClientError, match="Failed to fetch reports"):
            await client.fetch_current_reports()

    @pytest.mark.asyncio
    async def test_malformed_payload_raises_api_client_error(self, client):
        client._get = AsyncMock(return_value=[{"bad": "payload"}])

        with pytest.raises(APIClientError, match="Failed to parse report data"):
            await client.fetch_current_reports()

    @pytest.mark.asyncio
    async def test_type_error_raises_api_client_error(self, client):
        client._get = AsyncMock(return_value=[None])

        with pytest.raises(APIClientError, match="Malformed report payload"):
            await client.fetch_current_reports()


# ---------------------------------------------------------------------------
# fetch_report_details
# ---------------------------------------------------------------------------

class TestFetchReportDetails:
    @pytest.mark.asyncio
    async def test_returns_report_response_on_success(self, client):
        client._get = AsyncMock(return_value=RAW_REPORT_RESPONSE)

        result = await client.fetch_report_details("1234", MarketType.LIVE)

        assert result.row_count == 1
        assert len(result.results) == 1

    @pytest.mark.asyncio
    async def test_url_includes_slug_and_report_details(self, client):
        client._get = AsyncMock(return_value=RAW_REPORT_RESPONSE)

        await client.fetch_report_details("1234", MarketType.LIVE)

        call_url = client._get.call_args.args[0]
        assert "1234" in call_url
        assert "Report Details" in call_url

    @pytest.mark.asyncio
    async def test_params_include_last_reports_and_query(self, client):
        client._get = AsyncMock(return_value=RAW_REPORT_RESPONSE)

        await client.fetch_report_details("1234", MarketType.LIVE)

        call_kwargs = client._get.call_args.kwargs
        assert call_kwargs["params"]["lastReports"] == 1
        assert "q" in call_kwargs["params"]

    @pytest.mark.asyncio
    async def test_non_dict_response_raises_report_not_found_error(self, client):
        client._get = AsyncMock(return_value=[RAW_REPORT_RESPONSE])

        with pytest.raises(ReportNotFoundError, match="1234"):
            await client.fetch_report_details("1234", MarketType.LIVE)

    @pytest.mark.asyncio
    async def test_client_error_raises_api_client_error(self, client):
        client._get = AsyncMock(side_effect=aiohttp.ClientError())

        with pytest.raises(APIClientError, match="Failed to fetch report details"):
            await client.fetch_report_details("1234", MarketType.LIVE)

    @pytest.mark.asyncio
    async def test_malformed_payload_raises_api_client_error(self, client):
        client._get = AsyncMock(return_value={"results": "not-a-list", "stats": {}})

        with pytest.raises(APIClientError, match="Failed to parse report details"):
            await client.fetch_report_details("1234", MarketType.LIVE)

    @pytest.mark.asyncio
    async def test_type_error_raises_api_client_error(self, client):
        client._get = AsyncMock(return_value=None)

        with pytest.raises(APIClientError, match="Expected report detail object"):
            await client.fetch_report_details("1234", MarketType.LIVE)


# ---------------------------------------------------------------------------
# _build_report_params
# ---------------------------------------------------------------------------

class TestBuildReportParams:
    def test_returns_last_reports_one(self, client):
        params = client._build_report_params(MarketType.LIVE)
        assert params["lastReports"] == 1

    def test_query_string_present_for_each_market_type(self, client):
        for market_type in MarketType:
            params = client._build_report_params(market_type)
            assert "q" in params
            assert len(params["q"]) > 0
