import aiohttp
from typing import Any, Self
from time import perf_counter
from loguru import logger
from pydantic import ValidationError

from app.config import settings
from app.domain.models.schemas import ReportResponse, IncomingReport

from app.utils.enums import MarketType
from app.utils.exceptions import APIClientError, ReportNotFoundError

class QueryBuilder:
    _BASE_FILTERS = (
        "class=Steers;"
        "frame=Medium and Large;"
        "muscle_grade=1-2,1;"
        "freight=F.O.B.;"
    )

    _MARKET_FILTERS: dict[MarketType, str] = {
        MarketType.LIVE: "avg_weight=700:899;",
        MarketType.VIDEO: "wtd_avg_wt=700:899;current=Yes;region_name=South Central,North Central;",
        MarketType.DIRECT: "wtd_avg_wt=700:899;current=Yes;",
    }

    @classmethod
    def build(self, market_type: MarketType) -> str:
        market_filters = self._MARKET_FILTERS.get(market_type)
        if market_filters is None:
            raise APIClientError(f"Unsupported market type: {market_type!r}")
        return self._BASE_FILTERS + market_filters
    

class BaseAPIClient:

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> Self:
        self.session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.api_key, ""),
            timeout=aiohttp.ClientTimeout(total=settings.DEFAULT_REQUEST_TIMEOUT)
        )
        logger.info(
            "API client session initialized",
            event="api_session_open",
            operation="api_session_init",
            base_url=self.base_url,
            timeout_seconds=settings.DEFAULT_REQUEST_TIMEOUT,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()
            logger.info(
                "API client session closed",
                event="api_session_close",
                operation="api_session_close",
                base_url=self.base_url,
            )

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' to create as session")

        started_at = perf_counter()
        logger.debug(
            "API request started",
            event="api_request_start",
            operation="api_get",
            url=url,
            has_params=params is not None,
            param_keys=sorted(params.keys()) if params else [],
        )

        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                payload = await response.json()
                elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
                logger.debug(
                    "API request completed",
                    event="api_request_complete",
                    operation="api_get",
                    url=url,
                    status=response.status,
                    elapsed_ms=elapsed_ms,
                    payload_type=type(payload).__name__,
                )
                return payload
        except Exception as err:
            elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "API request failed",
                event="api_request_failed",
                operation="api_get",
                url=url,
                elapsed_ms=elapsed_ms,
                error=str(err),
                error_type=type(err).__name__,
            )
            raise
        

class APIClient(BaseAPIClient):
    
    def __init__(
            self,
            base_url: str = settings.MMN_BASE_URL,
            api_version: str = settings.MMN_API_VERSION,
            api_key: str = settings.MMN_API_KEY,
        ) -> None:
        super().__init__(base_url, api_key)
        self.endpoint = f"{base_url}/{api_version}/reports"


    async def fetch_current_reports(self) -> dict[str, IncomingReport]:
        try:
            raw_data = await self._get(self.endpoint)
            if not isinstance(raw_data, list):
                raise APIClientError("Expected report list from current reports endpoint")
            data = [IncomingReport(**report) for report in raw_data]
            logger.info(
                "Fetched current reports",
                event="current_reports_fetched",
                operation="fetch_current_reports",
                endpoint=self.endpoint,
                report_count=len(data),
            )
            return {report.slug: report for report in data}

        except aiohttp.ClientError as err:
            logger.error("Failed to fetch reports", endpoint=self.endpoint, error=str(err))
            raise APIClientError("Failed to fetch reports") from err
        
        except ValidationError as err:
            logger.error("Failed to parse report data", endpoint=self.endpoint, error=str(err))
            raise APIClientError("Failed to parse report data") from err
        except TypeError as err:
            logger.exception(
                "Malformed report payload",
                event="current_reports_malformed",
                operation="fetch_current_reports",
                endpoint=self.endpoint,
                error=str(err),
            )
            raise APIClientError("Malformed report payload received from current reports endpoint") from err
        

    async def fetch_report_details(self, slug: str, market_type: MarketType) -> ReportResponse:
        url = f"{self.endpoint}/{slug}/Report Details"
        params = self._build_report_params(market_type)

        try:
            raw_data = await self._get(url, params=params)
            if not isinstance(raw_data, dict):
                raise ReportNotFoundError(f"Expected report detail object for {slug!r}")
            response = ReportResponse(**raw_data)
            logger.info(
                "Fetched report details",
                event="report_details_fetched",
                operation="fetch_report_details",
                slug=slug,
                market_type=market_type.value,
                row_count=response.row_count,
            )
            return response
        
        except aiohttp.ClientError as err:
            logger.error("Failed to fetch report details", slug=slug, market_type=market_type.value, error=str(err))
            raise APIClientError(f"Failed to fetch report details for {slug!r}") from err
        
        except ValidationError as err:
            logger.error("Failed to parse report details", slug=slug, market_type=market_type.value, error=str(err))
            raise APIClientError(f"Failed to parse report details for {slug!r}") from err
        except TypeError as err:
            logger.exception(
                "Malformed report details payload",
                event="report_details_malformed",
                operation="fetch_report_details",
                slug=slug,
                market_type=market_type.value,
                error=str(err),
            )
            raise APIClientError(f"Malformed report details payload for {slug!r}") from err
        
    
    def _build_report_params(self, market_type: MarketType) -> dict[str, Any]:
        return {
            "lastReports": 1,
            "q": QueryBuilder.build(market_type)
        }

