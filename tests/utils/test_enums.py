import pytest

from app.utils.enums import (
    LowerStrEnum,
    RegionOptions,
    ReportStatusOptions,
    MarketTypeOptions,
    MARKET_TYPE_MAPPING,
    normalize_market_type,
)


# ===========================================================================
# LowerStrEnum - Case-Insensitive Matching
# ===========================================================================

class TestLowerStrEnum:
    
    def test_exact_lowercase_match(self):
        """Test 1 - exact lowercase value returns correct member."""
        assert RegionOptions("north central") is RegionOptions.NORTH_CENTRAL

    def test_uppercase_input_match(self):
        """Test 2 - uppercase input is normalised and matches."""
        assert RegionOptions("NORTH CENTRAL") is RegionOptions.NORTH_CENTRAL

    def test_mixed_case_input_match(self):
        """Test 3 - mixed-case input resolves to the correct member."""
        assert ReportStatusOptions("Preliminary") is ReportStatusOptions.PRELIMINARY

    def test_invalid_string_raises(self):
        """Test 4 - unrecognised string raises ValueError."""
        with pytest.raises(ValueError):
            RegionOptions("east central")

    def test_non_string_integer_raises(self):
        """Test 5a - integer input raises ValueError."""
        with pytest.raises(ValueError):
            RegionOptions(123)

    def test_non_string_none_raises(self):
        """Test 5b - None input raises ValueError."""
        with pytest.raises(ValueError):
            RegionOptions(None)



# ===========================================================================
# normalize_market_type
# ===========================================================================

class TestNormalizeMarketType:
    
    def test_auction_livestock_maps_to_live(self):
        """Test 12 - 'Auction Livestock' → LIVE."""
        result = normalize_market_type(["Auction Livestock"])
        assert result is MarketTypeOptions.LIVE

    def test_direct_livestock_maps_to_direct(self):
        """Test 13 - 'Direct Livestock' → DIRECT."""
        result = normalize_market_type(["Direct Livestock"])
        assert result is MarketTypeOptions.DIRECT

    def test_video_auction_livestock_maps_to_video(self):
        """Test 14 - 'Video Auction Livestock' → VIDEO."""
        result = normalize_market_type(["Video Auction Livestock"])
        assert result is MarketTypeOptions.VIDEO

    def test_case_insensitive_list_value(self):
        """Test 15 - uppercase list element is normalised before lookup."""
        result = normalize_market_type(["Auction Livestock"])
        assert result is MarketTypeOptions.LIVE

    def test_empty_list_raises(self):
        """Test 16 - empty list raises ValueError."""
        with pytest.raises(ValueError, match="Invalid market type"):
            normalize_market_type([])

    def test_non_list_string_raises(self):
        """Test 17 - plain string (not a list) raises ValueError."""
        with pytest.raises(ValueError, match="Invalid market type"):
            normalize_market_type("Auction Livestock")

    def test_non_list_none_raises(self):
        """Test 18 - None raises ValueError."""
        with pytest.raises(ValueError, match="Invalid market type"):
            normalize_market_type(None)

    def test_unrecognised_string_raises(self):
        """Test 19 - unrecognised market type string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid market type"):
            normalize_market_type(["unknown market"])

    def test_only_first_element_used(self):
        """Test 20 - extra list elements are ignored; only value[0] matters."""
        result = normalize_market_type(["Auction Livestock", "something else"])
        assert result is MarketTypeOptions.LIVE

    def test_non_string_element_raises_attribute_error(self):
        """Test 21 - integer as first element raises AttributeError (no .lower())."""
        with pytest.raises(AttributeError):
            normalize_market_type([123])

    def test_integer_value_raises(self):
        """Bonus - integer passed instead of list raises ValueError."""
        with pytest.raises(ValueError, match="Invalid market type"):
            normalize_market_type(42)

    def test_dict_value_raises(self):
        """Bonus - dict passed instead of list raises ValueError."""
        with pytest.raises(ValueError, match="Invalid market type"):
            normalize_market_type({"key": "Auction Livestock"})


# ===========================================================================
# MarketTypeOptions
# ===========================================================================

class TestMarketTypeOptions:

    def test_does_not_inherit_lower_str_enum(self):
        """Test 10 – MarketTypeOptions does NOT extend LowerStrEnum."""
        assert not issubclass(MarketTypeOptions, LowerStrEnum)

    def test_uppercase_raises_value_error(self):
        """Test 10b – uppercase lookup fails because there is no _missing_ override."""
        with pytest.raises(ValueError):
            MarketTypeOptions("LIVE")

    def test_exact_match_live(self):
        """Test 11a – exact lowercase value resolves to LIVE."""
        assert MarketTypeOptions("live") is MarketTypeOptions.LIVE

    def test_exact_match_direct(self):
        """Test 11b – exact lowercase value resolves to DIRECT."""
        assert MarketTypeOptions("direct") is MarketTypeOptions.DIRECT

    def test_exact_match_video(self):
        """Test 11c – exact lowercase value resolves to VIDEO."""
        assert MarketTypeOptions("video") is MarketTypeOptions.VIDEO


# ===========================================================================
# MARKET_TYPE_MAPPING completeness
# ===========================================================================

class TestMarketTypeMapping:
    
    def test_all_three_keys_present(self):
        """Bonus - the mapping covers all three expected raw strings."""
        expected_keys = {"auction livestock", "direct livestock", "video auction livestock"}
        assert set(MARKET_TYPE_MAPPING.keys()) == expected_keys

    def test_mapping_values_are_market_type_options(self):
        """Bonus - every value in the mapping is a MarketTypeOptions member."""
        for v in MARKET_TYPE_MAPPING.values():
            assert isinstance(v, MarketTypeOptions)
            
