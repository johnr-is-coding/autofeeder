import pytest
from pydantic import BaseModel, ValidationError

from app.utils.enums import (
    Region,
    ReportStatus,
    MarketType,
    MarketTypeField,
    RegionField,
    normalize_market_type,
)


class EnumFieldModel(BaseModel):
    market_type: MarketTypeField
    region: RegionField


class TestRegion:
    def test_case_insensitive(self):
        assert Region("NORTH CENTRAL") == Region.NORTH_CENTRAL
        assert Region("south central") == Region.SOUTH_CENTRAL
        assert Region("EmPtY") == Region.EMPTY

    def test_north_central_value(self):
        assert Region.NORTH_CENTRAL.value == "north central"

    def test_south_central_value(self):
        assert Region.SOUTH_CENTRAL.value == "south central"

    def test_empty_value(self):
        assert Region.EMPTY.value == "empty"

    def test_missing_value_returns_none(self):
        assert Region._missing_("invalid region") is None

    def test_missing_value_non_string(self):
        assert Region._missing_(123) is None


class TestReportStatus:
    def test_case_insensitive(self):
        assert ReportStatus("FINAL") == ReportStatus.FINAL
        assert ReportStatus("preliminary") == ReportStatus.PRELIMINARY

    def test_final_value(self):
        assert ReportStatus.FINAL.value == "final"

    def test_preliminary_value(self):
        assert ReportStatus.PRELIMINARY.value == "preliminary"


class TestMarketType:
    def test_live_value(self):
        assert MarketType.LIVE.value == "live"

    def test_direct_value(self):
        assert MarketType.DIRECT.value == "direct"

    def test_video_value(self):
        assert MarketType.VIDEO.value == "video"

    def test_all_members(self):
        assert len(MarketType) == 3


class TestNormalizeMarketType:
    def test_normalize_auction_livestock(self):
        result = normalize_market_type(["Auction Livestock"])
        assert result == MarketType.LIVE

    def test_normalize_special_livestock(self):
        result = normalize_market_type(["Auction Livestock (Special)"])
        assert result == MarketType.LIVE

    def test_normalize_graded_livestock(self):
        result = normalize_market_type(["Auction Livestock (Special Graded)"])
        assert result == MarketType.LIVE

    def test_normalize_direct_livestock(self):
        result = normalize_market_type(["Direct Livestock"])
        assert result == MarketType.DIRECT

    def test_normalize_video_auction_livestock(self):
        result = normalize_market_type(["Video Auction Livestock"])
        assert result == MarketType.VIDEO

    def test_normalize_case_insensitive(self):
        result = normalize_market_type(["AUCTION LIVESTOCK"])
        assert result == MarketType.LIVE

    def test_invalid_empty_list(self):
        with pytest.raises(ValueError, match="Invalid market type"):
            normalize_market_type([])

    def test_invalid_not_list(self):
        with pytest.raises(ValueError, match="Invalid market type"):
            normalize_market_type("auction livestock")

    def test_invalid_none(self):
        with pytest.raises(ValueError, match="Invalid market type"):
            normalize_market_type(None)

    def test_invalid_market_type(self):
        with pytest.raises(ValueError, match="Invalid market type"):
            normalize_market_type(["invalid type"])

    def test_takes_first_element(self):
        result = normalize_market_type(["Direct Livestock", "extra"])
        assert result == MarketType.DIRECT


class TestAnnotatedEnumFields:
    def test_market_type_field_normalizes_from_list(self):
        model = EnumFieldModel(market_type=["Auction Livestock"], region="north central")
        assert model.market_type == MarketType.LIVE

    def test_market_type_field_invalid_shape_raises(self):
        with pytest.raises(ValidationError, match="Market type must be a non-empty list"):
            EnumFieldModel(market_type="Auction Livestock", region="north central")

    def test_region_field_none_defaults_to_empty(self):
        model = EnumFieldModel(market_type=["Direct Livestock"], region=None)
        assert model.region == Region.EMPTY

    def test_region_field_parses_case_insensitive(self):
        model = EnumFieldModel(market_type=["Video Auction Livestock"], region="SOUTH CENTRAL")
        assert model.region == Region.SOUTH_CENTRAL

