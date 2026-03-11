from typing import TypeVar

import aiohttp
from typing import Any, Self
from datetime import date
from loguru import logger
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.domain.models.report import Reports
from app.domain.models.schemas import ReportResponse, IncomingReport

from app.utils.enums import MarketType
from app.utils.exceptions import APIClientError


T = TypeVar("T", bound=BaseModel)

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
        return self._BASE_FILTERS + self._MARKET_FILTERS.get(market_type)
    

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
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def _get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        response_model: type[T] | None = None,
    ) -> T | Any:
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'async with' to create as session")
        
        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
            if response_model:
                return response_model(**data)
            return data
        

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
            data = await self._get(self.endpoint, response_model=Reports)
            return {report.slug: report for report in data}

        except aiohttp.ClientError as err:
            logger.error("Failed to fetch reports", endpoint=self.endpoint, error=str(err))
            raise APIClientError("Failed to fetch reports") from err
        
        except ValidationError as err:
            logger.error("Failed to parse report data", endpoint=self.endpoint, error=str(err))
            raise APIClientError("Failed to parse report data") from err
        

    async def fetch_report_details(
        self,
        slug: str,
        market_type: MarketType,
        prev_report_date: date,
    ) -> ReportResponse | None:
        url = f"{self.endpoint}/{slug}/Report Details"
        params = self._build_report_params(market_type, prev_report_date)

        try:
            return await self._get(url, params=params, response_model=ReportResponse)
        
        except aiohttp.ClientError as err:
            logger.error("Failed to fetch report details", slug=slug, market_type=market_type.value, error=str(err))
            raise APIClientError(f"Failed to fetch report details for {slug!r}") from err
        
        except ValidationError as err:
            logger.error("Failed to parse report details", slug=slug, market_type=market_type.value, error=str(err))
            raise APIClientError(f"Failed to parse report details for {slug!r}") from err
        

    @staticmethod
    def _calculate_last_days(prev_report_date: date) -> int:
        return (date.today() - prev_report_date).days
    
    def _build_report_params(self, market_type: MarketType, prev_report_date: date) -> dict[str, Any]:
        return {
            "lastDays": self._calculate_last_days(prev_report_date),
            "q": QueryBuilder.build(market_type)
        }

