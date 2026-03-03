import uuid as uuid_pkg
from typing import Optional

from sqlmodel import (
    Index, 
    SQLModel,
    UniqueConstraint,
    Column,
    Field,
    Relationship,
    text
)

from app.domain.models.auction import Auction
from app.utils.enums import RegionOptions, ReportStatusOptions, ReportStatusEnum
from app.utils.validators import ReportDate, ReportDateTime

class Report(SQLModel, table=True):
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
    