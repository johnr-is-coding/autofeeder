from typing import Optional
import uuid as uuid_pkg

from sqlalchemy import text
from sqlalchemy.orm import RelationshipProperty
from sqlmodel import SQLModel, Field, Relationship, Column, Index, UniqueConstraint
from pydantic import AliasChoices

from app.utils.validators import ReportDate, ReportDateTime
from app.utils.enums import (
    MarketTypeEnum, 
    MarketTypeOptions,
    RegionOptions,
    ReportStatusEnum, 
    ReportStatusOptions
)


class Auction(SQLModel, table=True):
    """
    ORM model for the auctions table, with relationships to StoredReport and Reports.
    """

    __tablename__ = "auctions"

    slug: str = Field(primary_key=True, index=True)
    display_name: str = Field(unique=True, index=True)
    report_title: str = Field(unique=True, index=True)

    # sa_column bypasses type inference, so nullable=False IS needed here
    market_type: MarketTypeOptions = Field(
        sa_column=Column(
            MarketTypeEnum, 
            nullable=False, 
            default=MarketTypeOptions.LIVE
        )
    )

    offset: int = Field(default=0)
    active: bool = Field(default=True)

    stored_report: Optional["StoredReport"] = Relationship(
        sa_relationship=RelationshipProperty(
            "StoredReport",
            uselist=False,
            back_populates="auction"
        ),
        cascade_delete=True,
    )
    reports: list["Reports"] = Relationship(
        back_populates="auction",
        cascade_delete=True,
    )

    def __str__(self) -> str:
        return f"{self.display_name}({self.slug})"


class StoredReport(SQLModel, table=True):
    """
    ORM model for the stored_reports table, linked one-to-one with Auction.
    """

    __tablename__ = "stored_reports"

    slug: str = Field(
        primary_key=True,
        index=True,
        foreign_key="auctions.slug",
        exclude=True
    )

    report_date: ReportDate
    published_date: ReportDateTime

    report_status: ReportStatusOptions = Field(
        sa_column=Column(
            ReportStatusEnum, 
            nullable=False
        )
    )
    market_type: MarketTypeOptions = Field(
        sa_column=Column(
            MarketTypeEnum, 
            nullable=False
        )
    )
    has_corrections: bool

    auction: Auction = Relationship(
        sa_relationship=RelationshipProperty(
            "Auction",
            back_populates="stored_report",
            single_parent=True
        )
    )
   
   
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

    slug: str = Field(alias="slug_id")
    report_date: ReportDate
    published_date: ReportDateTime

    report_status: ReportStatusOptions = Field(alias="report_status")
    market_type: MarketTypeOptions = Field(alias="market_types")
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
    head_count: int
    avg_weight: float = Field(
        validation_alias=AliasChoices("avg_weight", "wtd_avg_weight")
    )
    avg_price: float = Field(
        validation_alias=AliasChoices("avg_price", "wtd_Avg_Price", "wtd_avg_price")
    )
    region: Optional[RegionOptions] = Field(
        default=None,
        validation_alias=AliasChoices("region_name", "region"),
    )

    def __str__(self) -> str:
        return f"({self.head_count}, {self.avg_weight}, {self.avg_price})"


class ReportStats(SQLModel):

    returned_rows: int = Field(alias="returnedRows")


class ReportResponse(SQLModel):

    results: list[ReportDetail]
    stats: ReportStats

    @property
    def row_count(self) -> int:
        return self.stats.returned_rows
    

class Reports(SQLModel, table=True):
    __tablename__ = "reports"
    
    __table_args__ = (
        # When region IS NULL (the common case)
        Index(
            "uq_reports_slug_date_no_region",
            "auction_slug",
            "report_date",
            unique=True,
            postgresql_where=text("region IS NULL"),
        ),
        # When region IS NOT NULL
        UniqueConstraint(
            "auction_slug",
            "report_date",
            "region",
            name="uq_reports_slug_date_region",
        ),
    )
    
    uuid: uuid_pkg.UUID = Field(
        default_factory=uuid_pkg.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("gen_random_uuid()"),
            "unique": True
        }
    )

    report_date: ReportDate
    report_end_date: ReportDate
    published_date: ReportDateTime

    # sa_column bypasses type inference — nullable=False IS needed here if required
    report_status: ReportStatusOptions = Field(
        sa_column=Column(ReportStatusEnum, nullable=False)
    )
    region: Optional[RegionOptions] = Field(default=None)

    head1: int = Field(default=0)
    weight1: float = Field(default=0.0)
    price1: float = Field(default=0.0)

    head2: int = Field(default=0)
    weight2: float = Field(default=0.0)
    price2: float = Field(default=0.0)

    head3: int = Field(default=0)
    weight3: float = Field(default=0.0)
    price3: float = Field(default=0.0)

    head4: int = Field(default=0)
    weight4: float = Field(default=0.0)
    price4: float = Field(default=0.0)

    # Slots 1-4 are weight-classes; slot 5 is the computed total
    head5: int = Field(gt=0)
    weight5: float = Field(gt=0.0)
    price5: float = Field(gt=0.0)

    auction_slug: str = Field(foreign_key="auctions.slug", ondelete="CASCADE")
    auction: Auction = Relationship(back_populates="reports")

    def __str__(self) -> str:
        data_str = f"{self.head5} head at ${self.price5} on {self.report_date}"
        if self.region:
            return f"{self.auction.display_name} {self.region}({self.auction_slug}): {data_str}"
        return f"{self.auction.display_name}({self.auction_slug}): {data_str}"
    