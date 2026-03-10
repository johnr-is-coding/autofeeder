from typing import Optional

from sqlmodel import SQLModel, Field
from pydantic import AliasChoices

from app.utils.validators import ReportDate, ReportDateTime
from app.utils.enums import MarketTypeField, Region, ReportStatus

   
class IncomingReport(SQLModel):
    """
    Validation-only model for parsing raw API responses.

    Incoming data formats:
        slug            : "1234"
        report_date     : MM/DD/YYYY
        published_date  : MM/DD/YYYY HH:MM:SS
        report_status   : "Preliminary" or "Final"
        market_type     : list[str] (e.g. ["Auction Livestock"])
        has_corrections : true or false
    """

    slug: str = Field(alias="slug_id",)
    report_date: ReportDate
    published_date: ReportDateTime

    report_status: ReportStatus = Field(alias="report_status")
    market_type: MarketTypeField = Field(alias="market_types")
    has_corrections: bool = Field(alias="hasCorrectionsInLastThreeDays")
    

class ReportDetail(SQLModel):
    """
    Schema for shared report detail fields. Not a database table.

    Incoming data formats:
        report_date                   : MM/DD/YYYY
        report_end_date               : MM/DD/YYYY
        published_date                : MM/DD/YYYY HH:MM:SS
        head_count                    : int (e.g. 150)
        avg_weight                    : float or str (e.g. "850.5" or 850.5)
        avg_price                     : float or str (e.g. "850.5" or 850.5)
        region                        : Optional[str] (e.g. "North Central", "South Central", or None)
    """

    report_date: ReportDate
    report_end_date: ReportDate
    published_date: ReportDateTime
    report_status: ReportStatus
    head_count: int
    avg_weight: float = Field(
        validation_alias=AliasChoices("avg_weight", "wtd_avg_weight", "wtd_avg_wt")
    )
    avg_price: float = Field(
        validation_alias=AliasChoices("avg_price", "wtd_Avg_Price", "wtd_avg_price")
    )
    region: Optional[Region] = Field(default=None, alias="region_name")


class ReportStats(SQLModel):
    returned_rows: int = Field(alias="returnedRows")


class ReportResponse(SQLModel):
    results: list[ReportDetail]
    stats: ReportStats

    @property
    def row_count(self) -> int:
        return self.stats.returned_rows
    