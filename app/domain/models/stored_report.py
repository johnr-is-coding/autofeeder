from sqlmodel import Column, SQLModel, Field, Relationship
from sqlalchemy.orm import RelationshipProperty

from app.domain.models.auction import Auction
from app.utils.validators import ReportDate, ReportDateTime
from app.utils.enums import (
    MarketTypeEnum,
    ReportStatusEnum,
    MarketTypeOptions,
    ReportStatusOptions,
    ReportStatusOptions
)


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
            back_populates="stored_reports",
            single_parent=True
        )
    )
   