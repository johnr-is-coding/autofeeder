import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.api_client import APIClient
from app.domain.agg_models import LatestReport

MODULE = "app.infrastructure.api_client"

VALID_ITEM = {
    "slug_id": "1281",
    "report_date": "01/15/2024",
    "published_date": "01/15/2024 10:00:00",
    "report_status": "Final",
    "market_types": ["Auction Livestock"],
    "hasCorrectionsInLastThreeDays": False,
}

# An item that fails LatestReport validation (missing required fields)
INVALID_ITEM = {"name": "Some Other Report Type", "slug_id": "9999"}


def make_client() -> APIClient:
    return APIClient(base_url="https://example.com", api_version="v1", api_key="test-key")


# ===========================================================================
# fetch_current_reports — validation filtering
# ===========================================================================

class TestFetchCurrentReports:

    # ------------------------------------------------------------------
    # Test 1 – Valid items are returned as LatestReport objects
    # Name: fetch_current_reports parses valid items
    # Description: Items that satisfy LatestReport validation should be
    #              included in the returned list.
    # Steps: Mock _get to return one valid item; call fetch_current_reports.
    # Expected: List of length 1 containing a LatestReport.
    # ------------------------------------------------------------------
    async def test_valid_items_are_returned(self):
        client = make_client()
        client._get = AsyncMock(return_value=[VALID_ITEM])

        reports = await client.fetch_current_reports()

        assert len(reports) == 1
        assert isinstance(reports[0], LatestReport)

    # ------------------------------------------------------------------
    # Test 2 – Items that fail validation are silently skipped
    # Name: fetch_current_reports skips invalid items
    # Description: Items that raise ValidationError should be dropped
    #              without raising an exception.
    # Steps: Mock _get to return one invalid item; call fetch_current_reports.
    # Expected: Empty list; no exception raised.
    # ------------------------------------------------------------------
    async def test_invalid_items_are_skipped(self):
        client = make_client()
        client._get = AsyncMock(return_value=[INVALID_ITEM])

        reports = await client.fetch_current_reports()

        assert reports == []

    # ------------------------------------------------------------------
    # Test 3 – Mixed response returns only valid items
    # Name: fetch_current_reports filters mixed response
    # Description: When the API returns a mix of valid and invalid items,
    #              only the valid ones should appear in the result.
    # Steps: Mock _get to return [invalid, valid, invalid]; call method.
    # Expected: List of length 1 containing the valid LatestReport.
    # ------------------------------------------------------------------
    async def test_mixed_response_returns_only_valid(self):
        client = make_client()
        client._get = AsyncMock(return_value=[INVALID_ITEM, VALID_ITEM, INVALID_ITEM])

        reports = await client.fetch_current_reports()

        assert len(reports) == 1
        assert isinstance(reports[0], LatestReport)
        assert reports[0].slug == VALID_ITEM["slug_id"]

    # ------------------------------------------------------------------
    # Test 4 – All invalid items returns empty list
    # Name: fetch_current_reports returns empty list when all items invalid
    # Description: If every item from the API fails validation, the result
    #              should be an empty list without raising.
    # Steps: Mock _get to return three invalid items.
    # Expected: []
    # ------------------------------------------------------------------
    async def test_all_invalid_returns_empty_list(self):
        client = make_client()
        client._get = AsyncMock(return_value=[INVALID_ITEM, INVALID_ITEM, INVALID_ITEM])

        reports = await client.fetch_current_reports()

        assert reports == []

    # ------------------------------------------------------------------
    # Test 5 – Empty API response returns empty list
    # Name: fetch_current_reports handles empty list from API
    # Description: An empty list from the API should return an empty list.
    # Steps: Mock _get to return [].
    # Expected: []
    # ------------------------------------------------------------------
    async def test_empty_response_returns_empty_list(self):
        client = make_client()
        client._get = AsyncMock(return_value=[])

        reports = await client.fetch_current_reports()

        assert reports == []

    # ------------------------------------------------------------------
    # Test 6 – Count logged reflects only valid items
    # Name: Logged count matches number of valid reports
    # Description: The info log should report the count of successfully
    #              parsed reports, not the raw item count from the API.
    # Steps: Mock _get to return 1 invalid + 1 valid; patch logger;
    #        check the logged count.
    # Expected: logger.info called with count=1.
    # ------------------------------------------------------------------
    async def test_logged_count_reflects_valid_items_only(self):
        client = make_client()
        client._get = AsyncMock(return_value=[INVALID_ITEM, VALID_ITEM])

        with patch(f"{MODULE}.logger") as mock_logger:
            await client.fetch_current_reports()

        mock_logger.info.assert_called_once()
        assert mock_logger.info.call_args[1]["count"] == 1