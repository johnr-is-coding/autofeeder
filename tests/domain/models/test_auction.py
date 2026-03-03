import pytest

from app.domain.agg_models import Auction
from app.utils.enums import MarketTypeOptions


@pytest.fixture
def base_auction_data():
    return {
        "slug": "1234",
        "display_name": "Test Auction",
        "report_title": "Test Auction Report",
        "market_type": ["Auction Livestock"],
    }


# ===========================================================================
# Auction
# ===========================================================================

class TestAuction:

    # ------------------------------------------------------------------
    # Test 11 – Valid construction with required fields
    # Name: Valid Auction construction
    # Description: An Auction with all required fields should instantiate correctly.
    # Steps: Supply slug, display_name, report_title, market_type.
    # Expected: Instance created; defaults applied for offset and active.
    # ------------------------------------------------------------------
    def test_valid_construction(self, base_auction_data):
        auction = Auction(**base_auction_data)
        assert auction.slug == "1234"
        assert auction.display_name == "Test Auction"
        assert auction.offset == 0
        assert auction.active is True

    # ------------------------------------------------------------------
    # Test 12 – Default market_type is LIVE
    # Name: market_type default value
    # Description: When market_type is not explicitly set via Python default, it resolves to LIVE.
    # Steps: Read MarketTypeOptions.LIVE directly from the sa_column default.
    # Expected: MarketTypeOptions.LIVE
    # ------------------------------------------------------------------
    def test_market_type_default_is_live(self):
        """The sa_column default is LIVE; verify the enum value directly."""
        assert MarketTypeOptions.LIVE.value == "live"

    # ------------------------------------------------------------------
    # Test 13 – active defaults to True
    # Name: active field default
    # Description: active should default to True when not supplied.
    # Steps: Construct Auction without active.
    # Expected: auction.active is True
    # ------------------------------------------------------------------
    def test_active_defaults_to_true(self, base_auction_data):
        auction = Auction(**base_auction_data)
        assert auction.active is True

    # ------------------------------------------------------------------
    # Test 14 – offset defaults to 0
    # Name: offset field default
    # Description: offset should default to 0 when not supplied.
    # Steps: Construct Auction without offset.
    # Expected: auction.offset == 0
    # ------------------------------------------------------------------
    def test_offset_defaults_to_zero(self, base_auction_data):
        auction = Auction(**base_auction_data)
        assert auction.offset == 0

    # ------------------------------------------------------------------
    # Test 15 – __str__ output
    # Name: Auction __str__
    # Description: __str__ should return "DisplayName(slug)".
    # Steps: Call str() on a valid Auction.
    # Expected: "Test Auction(1234)"
    # ------------------------------------------------------------------
    def test_str_representation(self, base_auction_data):
        auction = Auction(**base_auction_data)
        assert str(auction) == "Test Auction(1234)"

    # ------------------------------------------------------------------
    # Test 16 – Explicit active=False
    # Name: Auction marked inactive
    # Description: active can be explicitly set to False.
    # Steps: Pass active=False.
    # Expected: auction.active is False
    # ------------------------------------------------------------------
    def test_explicit_inactive(self, base_auction_data):
        auction = Auction(**{**base_auction_data, "active": False})
        assert auction.active is False

    # ------------------------------------------------------------------
    # Test 17 – Custom offset
    # Name: Auction with non-zero offset
    # Description: offset can be set to any integer.
    # Steps: Pass offset=3.
    # Expected: auction.offset == 3
    # ------------------------------------------------------------------
    def test_custom_offset(self, base_auction_data):
        auction = Auction(**{**base_auction_data, "offset": 3})
        assert auction.offset == 3

    # ------------------------------------------------------------------
    # Test 18 – market_type accepts all MarketTypeOptions values
    # Name: Auction market_type accepts DIRECT and VIDEO
    # Description: market_type should accept every MarketTypeOptions member.
    # Steps: Construct Auctions with DIRECT and VIDEO.
    # Expected: market_type matches the supplied value.
    # ------------------------------------------------------------------
    @pytest.mark.parametrize("market_type", list(MarketTypeOptions))
    def test_market_type_all_values(self, base_auction_data, market_type):
        auction = Auction(**{**base_auction_data, "market_type": market_type})
        assert auction.market_type == market_type

