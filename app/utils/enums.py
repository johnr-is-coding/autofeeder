from enum import Enum
from typing import Annotated, Any, Optional

from pydantic import BeforeValidator
from sqlalchemy.dialects import postgresql


# -------------------------------------------------------------------
# Base Enum (case insensitive matching)
# -------------------------------------------------------------------

class LowerStrEnum(str, Enum):
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            value = value.lower()
            return next(
                (member for member in cls if member.value == value),
                None,
            )
        return None


# -------------------------------------------------------------------
# Enums
# -------------------------------------------------------------------

class Region(LowerStrEnum):
    EMPTY = "empty"
    NORTH_CENTRAL = "north central"
    SOUTH_CENTRAL = "south central"

class ReportStatus(LowerStrEnum):
    FINAL = "final"
    PRELIMINARY = "preliminary"

class MarketType(str, Enum):
    LIVE = "live"
    DIRECT = "direct"
    VIDEO = "video"


# -------------------------------------------------------------------
# Model Type Field (Pydantic annotated type with input normalization)
# -------------------------------------------------------------------

MARKET_TYPE_MAPPING = {
    "auction livestock": MarketType.LIVE,
    "direct livestock": MarketType.DIRECT,
    "video auction livestock": MarketType.VIDEO,
    "auction livestock (special)": MarketType.LIVE,
    "auction livestock (special graded)": MarketType.LIVE,
}

def normalize_market_type(value: Any) -> Optional[MarketType]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"Market type must be a non-empty list; got: {value!r}")

    normalized = value[0].lower()
    return MARKET_TYPE_MAPPING.get(normalized, None)
 

MarketTypeField = Annotated[
    Optional[MarketType],
    BeforeValidator(normalize_market_type),
]

RegionField = Annotated[Region, BeforeValidator(lambda v: Region.EMPTY if v is None else v)]


# -------------------------------------------------------------------
# PostgreSQL ENUMS
# -------------------------------------------------------------------

MarketTypeEnum = postgresql.ENUM(
    MarketType,
    name="market_type_enum",
    create_type=False,
)

ReportStatusEnum = postgresql.ENUM(
    ReportStatus,
    name="report_status_enum",
    create_type=False,
)

RegionEnum = postgresql.ENUM(
    Region,
    name="region_enum",
    create_type=False,
)
