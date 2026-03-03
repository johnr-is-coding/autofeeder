import aiohttp
from typing import Any, Self
from datetime import date
from loguru import logger
from pydantic import ValidationError

from app.config import settings
from app.utils.enums import MarketTypeOptions
from app.domain.models import ReportResponse, StoredReport
from app.utils.exceptions import APIClientError, ReportNotFoundError


class QueryBuilder:
    _BASE_FILTERS = (
        "class=Steers;"
        "frame=Medium and Large;"
        "muscle_grade=1-2,1;"
        "freight=F.O.B.;"
    )

    _MARKET_FILTERS: dict[MarketTypeOptions, str] = {
        MarketTypeOptions.LIVE: "avg_weight=700:899;",
        MarketTypeOptions.VIDEO: "wtd_avg_wt=700:899;current=Yes;region_name=South Central,North Central;",
        MarketTypeOptions.DIRECT: "wtd_avg_wt=700:899;current=Yes;",
    }

    # Pre-built at class load time — no work done at call time
    _BUILT: dict[MarketTypeOptions, str] = {}

    def __init_subclass__(cls) -> None:
        cls._BUILT = {k: cls._BASE_FILTERS + v for k, v in cls._MARKET_FILTERS.items()}

    @classmethod
    def build(cls, market_type: MarketTypeOptions) -> str:
        return cls._BUILT.get(market_type, cls._BASE_FILTERS)
    

class BaseAPIClient:

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> Self:
        self.session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.api_key, "")
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' to create as session")
        
        async with self.session.get(
            url,
            params=params,
            timeout=aiohttp.ClientTimeout(total=settings.DEFAULT_REQUEST_TIMEOUT)
        ) as response:
            response.raise_for_status()
            return await response.json()
        

class APIClient(BaseAPIClient):
    
    def __init__(
            self, 
            base_url: str = settings.MMN_BASE_URL,
            api_version: str = settings.MMN_API_VERSION,
            api_key: str = settings.MMN_API_KEY
        ) -> None:
        super().__init__(base_url, api_key)
        self.endpoint = f"{base_url}/{api_version}/reports"


    async def fetch_current_reports(self) -> list[StoredReport]:
        try:
            data = await self._get(self.endpoint)
        except aiohttp.ClientError as exc:
            logger.error("Failed to fetch reports", endpoint=self.endpoint, error=str(exc))
            raise APIClientError("Failed to fetch reports") from exc
        
        if not isinstance(data, list):
            logger.warning("Unexpected response format", endpoint=self.endpoint, type=type(data).__name__)
            return []
        
        reports = []
        for item in data:
            try:
                reports.append(StoredReport.model_validate(item))
            except ValidationError:
                pass

        logger.info("Fetched reports", endpoint=self.endpoint, count=len(reports))
        return reports


    async def fetch_report_details(
        self,
        slug: str,
        market_type: MarketTypeOptions,
        prev_report_date: date
    ) -> ReportResponse:
        url = f"{self.endpoint}/{slug}/Report Details"
        params = self._build_report_params(market_type, prev_report_date)

        try:
            data = await self._get(url, params=params)
        except aiohttp.ClientError as exc:
            logger.error("Failed to fetch report details", slug=slug, market_type=market_type.value, error=str(exc))
            raise APIClientError(f"Failed to fetch report details for {slug!r}") from exc

        if not isinstance(data, dict):
            logger.warning("Unexpected response format", slug=slug, type=type(data).__name__)
            raise ReportNotFoundError(f"Unexpected response format for {slug!r}: expected dict, got {type(data).__name__}")

        logger.info("Fetched report details", slug=slug, market_type=market_type.value, params=params)
        return ReportResponse.model_validate(data)

    @staticmethod
    def _calculate_last_days(prev_report_date: date) -> int:
        return (date.today() - prev_report_date).days
    
    def _build_report_params(self, market_type: MarketTypeOptions, prev_report_date: date) -> dict[str, Any]:
        return {
            "lastDays": self._calculate_last_days(prev_report_date),
            "q": QueryBuilder.build(market_type)
        }

