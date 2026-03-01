from enum import Enum
from typing import Annotated, Any

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

class RegionOptions(LowerStrEnum):
    NORTH_CENTRAL = "north central"
    SOUTH_CENTRAL = "south central"

class ReportStatusOptions(LowerStrEnum):
    FINAL = "final"
    PRELIMINARY = "preliminary"

class MarketTypeOptions(str, Enum):
    LIVE = "live"
    DIRECT = "direct"
    VIDEO = "video"


# -------------------------------------------------------------------
# Market Type Validator
# -------------------------------------------------------------------

MARKET_TYPE_MAPPING = {
    "auction livestock": MarketTypeOptions.LIVE,
    "direct livestock": MarketTypeOptions.DIRECT,
    "video auction livestock": MarketTypeOptions.VIDEO,
}

def normalize_market_type(value: Any) -> MarketTypeOptions:
    if not isinstance(value, list) or not value:
        raise ValueError(f"Invalid market type: {value}")
    
    normalized = value[0].lower()
    try:
        return MARKET_TYPE_MAPPING[normalized]
    except KeyError as exc:
        raise ValueError(f"Invalid market type: {value}") from exc


MarketTypeValidator = Annotated[
    MarketTypeOptions,
    BeforeValidator(normalize_market_type),
]


# -------------------------------------------------------------------
# PostgreSQL ENUMS
# -------------------------------------------------------------------

MarketTypeEnum = postgresql.ENUM(
    MarketTypeOptions,
    name="market_type_enum",
    create_type=False, 
)

ReportStatusEnum = postgresql.ENUM(
    ReportStatusOptions,
    name="report_status_enum",
    create_type=False,
)

RegionEnum = postgresql.ENUM(
    RegionOptions,
    name="region_enum",
    create_type=False,
)