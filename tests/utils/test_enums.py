import pytest

from app.utils.enums import (
    LowerStrEnum,
    Region,
    ReportStatus,
    MarketType,
    normalize_market_type,
    MARKET_TYPE_MAPPING,
)


class TestLowerStrEnum:
    def test_case_insensitive_matching_lower(self):
        assert Region("north central") == Region.NORTH_CENTRAL

    def test_case_insensitive_matching_upper(self):
        assert Region("NORTH CENTRAL") == Region.NORTH_CENTRAL

    def test_case_insensitive_matching_mixed(self):
        assert Region("NoRtH CeNtRaL") == Region.NORTH_CENTRAL

    def test_missing_value_returns_none(self):
        assert Region._missing_("invalid region") is None

    def test_missing_value_non_string(self):
        assert Region._missing_(123) is None


class TestRegion:
    def test_north_central_value(self):
        assert Region.NORTH_CENTRAL.value == "north central"

    def test_south_central_value(self):
        assert Region.SOUTH_CENTRAL.value == "south central"

    def test_all_members(self):
        assert len(Region) == 2


class TestReportStatus:
    def test_final_value(self):
        assert ReportStatus.FINAL.value == "final"

    def test_preliminary_value(self):
        assert ReportStatus.PRELIMINARY.value == "preliminary"

    def test_case_insensitive(self):
        assert ReportStatus("FINAL") == ReportStatus.FINAL


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
        result = normalize_market_type(["auction livestock"])
        assert result == MarketType.LIVE

    def test_normalize_direct_livestock(self):
        result = normalize_market_type(["direct livestock"])
        assert result == MarketType.DIRECT

    def test_normalize_video_auction_livestock(self):
        result = normalize_market_type(["video auction livestock"])
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
        result = normalize_market_type(["direct livestock", "extra"])
        assert result == MarketType.DIRECT


class TestMarketTypeMapping:
    def test_mapping_contains_all_types(self):
        assert len(MARKET_TYPE_MAPPING) == 3

    def test_mapping_values_are_market_type(self):
        for value in MARKET_TYPE_MAPPING.values():
            assert isinstance(value, MarketType)
