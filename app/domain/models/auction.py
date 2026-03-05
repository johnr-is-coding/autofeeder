from typing import Optional, TYPE_CHECKING

from sqlalchemy.orm import RelationshipProperty
from sqlmodel import Column, SQLModel, Field, Relationship

from app.utils.enums import (
    MarketTypeEnum,
    MarketType,
)

if TYPE_CHECKING:
    from app.domain.models.report import Report
    from app.domain.models.stored_report import StoredReport

class Auction(SQLModel, table=True):
    """
    ORM model for the auctions table, with relationships to StoredReport and Reports.
    """

    __tablename__ = "auctions"

    slug: str = Field(primary_key=True, index=True)
    display_name: str = Field(unique=True, index=True)
    report_title: str = Field(unique=True, index=True)

    # sa_column bypasses type inference, so nullable=False IS needed here
    market_type: MarketType = Field(
        sa_column=Column(
            MarketTypeEnum,
            nullable=False,
            default=MarketType.LIVE
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
    reports: list["Report"] = Relationship(
        back_populates="auction",
        cascade_delete=True,
    )

    def __str__(self) -> str:
        return f"{self.display_name}({self.slug})"