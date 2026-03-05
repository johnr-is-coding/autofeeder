import pytest

from app.domain.models import Auction
from app.utils.enums import MarketType


class TestAuction:

    @pytest.fixture
    def auction_data(self):
        return {
            "slug": "1234",
            "display_name": "Test Auction",
            "report_title": "Test Auction Report",
            "market_type": MarketType.LIVE,
        }

    def test_valid_construction(self, auction_data):
        auction = Auction.model_validate(auction_data)
        assert auction.slug == "1234"
        assert auction.display_name == "Test Auction"
        assert auction.report_title == "Test Auction Report"
        assert auction.market_type == MarketType.LIVE

    def test_defaults(self, auction_data):
        auction = Auction.model_validate(auction_data)
        assert auction.offset == 0
        assert auction.active is True

    def test_custom_offset(self, auction_data):
        auction = Auction.model_validate({**auction_data, "offset": 5})
        assert auction.offset == 5

    def test_inactive(self, auction_data):
        auction = Auction.model_validate({**auction_data, "active": False})
        assert auction.active is False

    def test_market_type_direct(self, auction_data):
        auction_data["market_type"] = MarketType.DIRECT
        auction = Auction.model_validate(auction_data)
        assert auction.market_type == MarketType.DIRECT

    def test_market_type_video(self, auction_data):
        auction_data["market_type"] = MarketType.VIDEO
        auction = Auction.model_validate(auction_data)
        assert auction.market_type == MarketType.VIDEO

    def test_str(self, auction_data):
        auction = Auction.model_validate(auction_data)
        assert str(auction) == "Test Auction(1234)"
