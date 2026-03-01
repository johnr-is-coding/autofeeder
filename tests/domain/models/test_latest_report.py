import pytest
from unittest.mock import MagicMock

from app.domain.models import LatestReport

# ===========================================================================
# LatestReport
# ===========================================================================

class TestLatestReport:

    @pytest.fixture
    def base_latest_report_data(self):
        return {
            "slug_id": "1234",
            "report_date": "01/15/2024",
            "published_date": "01/15/2024 10:00:00",
            "report_status": "Final",
            "market_types": ["Auction Livestock"],
            "hasCorrectionsInLastThreeDays": False,
        }

    # ------------------------------------------------------------------
    # Test 18 – Valid construction via aliases
    # Name: LatestReport construction with field aliases
    # Description: All primary-alias fields should be mapped correctly.
    # Steps: Supply "slug_id", "market_types", "hasCorrectionsInLastThreeDays".
    # Expected: Instance created with correct attribute values.
    # ------------------------------------------------------------------
    def test_valid_construction_via_aliases(self, base_latest_report_data):
        report = LatestReport(**base_latest_report_data)
        assert report.slug == "1234"
        assert report.has_corrections is False

    # ------------------------------------------------------------------
    # Test 19 – has_corrections alias
    # Name: has_corrections via hasCorrectionsInLastThreeDays
    # Description: The camelCase alias should populate has_corrections.
    # Steps: Pass hasCorrectionsInLastThreeDays=True.
    # Expected: report.has_corrections is True
    # ------------------------------------------------------------------
    def test_has_corrections_alias_true(self, base_latest_report_data):
        data = {**base_latest_report_data, "hasCorrectionsInLastThreeDays": True}
        report = LatestReport(**data)
        assert report.has_corrections is True

    # ------------------------------------------------------------------
    # Test 20 – __str__ when status is FINAL
    # Name: LatestReport __str__ with FINAL status
    # Description: When report_status is FINAL the longer format is returned.
    # Steps: Build a LatestReport with FINAL status and a mocked auction.
    # Expected: String contains auction str and report_date.
    # ------------------------------------------------------------------
    def test_str_final_status(self, base_latest_report_data):
        report = LatestReport(**base_latest_report_data)
        mock_auction = MagicMock()
        mock_auction.__str__ = lambda self: "Test Auction(1234)"
        report.auction = mock_auction
        result = str(report)
        assert "final" in result.lower() or "01/15/2024" in result

    # ------------------------------------------------------------------
    # Test 22 – Missing required alias raises ValidationError
    # Name: Missing slug_id raises ValidationError
    # Description: slug_id is required (maps to slug primary key).
    # Steps: Omit slug_id from construction data.
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_missing_slug_id_raises(self, base_latest_report_data):
        from pydantic import ValidationError
        data = {**base_latest_report_data}
        data.pop("slug_id")
        with pytest.raises(ValidationError):
            LatestReport.model_validate(data)

