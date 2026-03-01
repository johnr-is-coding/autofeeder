from typing import Optional
import uuid as uuid_pkg

from datetime import date, datetime
from sqlalchemy import text
from sqlalchemy.orm import RelationshipProperty
from sqlmodel import SQLModel, Field, Relationship, Column, Index, UniqueConstraint
from pydantic import AliasChoices, field_validator, model_validator

from app.domain.base import UUIDModel, TimestampModel
from app.utils.validators import ReportDate, ReportDateTime
from app.utils.enums import (
    MarketTypeEnum, 
    MarketTypeOptions,
    RegionOptions,
    ReportStatusEnum, 
    ReportStatusOptions
)

class ReportDetail(SQLModel):
    """
    Schema for shared report detail fields. Not a database table.

    Incoming data formats:
        report_date                   : MM/DD/YYYY
        report_end_date               : MM/DD/YYYY
        published_date                : MM/DD/YYYY HH:MM:SS
        avg_weight                    : float or str (e.g. "850.5" or 850.5)
        avg_price                     : float or str (e.g. "850.5" or 850.5)
        region                        : Optional[str] (e.g. "North Central", "South Central")
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
    

class Auction(SQLModel, table=True):
    """
    Table for auction metadata with relationships to LatestReport and Reports.

    Date formats:
        report_date    : MM/DD/YYYY
        published_date : MM/DD/YYYY HH:MM:SS 
    """

    __tablename__ = "auctions"

    # Primary keys are implicitly non-null — nullable=False not needed
    slug: str = Field(primary_key=True, index=True)
    # Plain str fields are inferred as nullable=False by SQLAlchemy — no need to state it
    display_name: str = Field(unique=True, index=True)
    report_title: str = Field(unique=True, index=True)

    # sa_column bypasses type inference, so nullable=False IS needed here
    market_type: MarketTypeOptions = Field(
        sa_column=Column(MarketTypeEnum, nullable=False, default=MarketTypeOptions.LIVE)
    )

    # Plain int/bool fields are inferred as nullable=False
    offset: int = Field(default=0)
    active: bool = Field(default=True)

    latest_report: Optional["LatestReport"] = Relationship(
        sa_relationship=RelationshipProperty(
            "LatestReport",
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
    

class LatestReport(SQLModel, table=True):
    """
    Table for last fetched report metadata, linked one-to-one with Auction.

    Incoming data formats:
        report_date    : MM/DD/YYYY
        published_date : MM/DD/YYYY HH:MM:SS
        report_status  : "Preliminary" or "Final"
        market_type    : list[str] (e.g. ["Auction Livestock"], ["Direct Livestock"], ["Video Auction Livestock"])
    """

    __tablename__ = "latest_reports"

    # Primary key + foreign key — nullable=False is implicit
    slug: str = Field(alias="slug_id", primary_key=True, index=True, foreign_key="auctions.slug")

    report_date: ReportDate
    published_date: ReportDateTime

    # sa_column bypasses type inference — nullable=False IS needed here if required
    report_status: ReportStatusOptions = Field(
        sa_column=Column(ReportStatusEnum, nullable=False)
    )
    market_type: MarketTypeOptions = Field(
        alias="market_types",
        sa_column=Column(MarketTypeEnum, nullable=False),
    )

    has_corrections: bool = Field(alias="hasCorrectionsInLastThreeDays")

    auction: Optional[Auction] = Relationship(back_populates="latest_report")

    @model_validator(mode="after")
    def require_slug(self) -> "LatestReport":
        if self.slug is None:
            raise ValueError("slug_id is required — must reference a valid auctions.slug")
        return self

    def __str__(self) -> str:
        if self.report_status == ReportStatusOptions.PRELIMINARY:
            return f"{self.slug}, {self.report_date}, {self.report_status}, published={self.published_date})"
        return f"{self.auction}: {self.report_status} report on {self.report_date}"


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
    created_at: datetime = Field(
        default_factory=datetime.now,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("current_timestamp(0)")
        }
    )

    updated_at: datetime = Field(
        default_factory=datetime.now,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("current_timestamp(0)"),
            "onupdate": text("current_timestamp(0)")
        }
    )

    report_date: ReportDate
    report_end_date: ReportDate
    published_date: ReportDateTime

    # sa_column bypasses type inference — nullable=False IS needed here if required
    report_status: ReportStatusOptions = Field(
        sa_column=Column(ReportStatusEnum, nullable=False)
    )

    # Optional[] is correctly inferred as nullable=True — no extra config needed
    region: Optional[RegionOptions] = Field(default=None)

    # Plain int/float inferred as nullable=False, defaults handled by Python
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

    head5: int = Field(gt=0)
    weight5: float = Field(gt=0.0)
    price5: float = Field(gt=0.0)

    # Plain str foreign key inferred as nullable=False
    auction_slug: str = Field(foreign_key="auctions.slug", ondelete="CASCADE")
    auction: Auction = Relationship(back_populates="reports")

    def __str__(self) -> str:
        if self.region:
            return f"{self.display_name} {self.region}({self.slug}): {self.head5} head at ${self.price5} on {self.report_date}"
        return f"{self.auction}: {self.head5} head at ${self.price5} on {self.report_date}"
    