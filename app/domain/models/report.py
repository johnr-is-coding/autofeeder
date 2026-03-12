from datetime import date, datetime

from pydantic import RootModel
from sqlalchemy import Column, UniqueConstraint
from sqlmodel import SQLModel, Field, Relationship

from app.domain.models.auction import Auction
from app.utils.enums import Region, RegionEnum, ReportStatus, ReportStatusEnum


class Report(SQLModel, table=True):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("auction_slug", "report_date", "region", name="uq_report_slug_date_region"),
    )

    auction_slug: str = Field(foreign_key="auctions.slug", primary_key=True, ondelete="CASCADE")
    report_date: date = Field(primary_key=True)
    region: Region = Field(
        default=Region.EMPTY,
        sa_column=Column(RegionEnum, primary_key=True, nullable=False),
    )

    report_end_date: date
    published_date: datetime

    report_status: ReportStatus = Field(
        sa_column=Column(ReportStatusEnum, nullable=False)
    )

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

    auction: Auction = Relationship(back_populates="reports")
