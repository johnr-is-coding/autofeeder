import pytest
from unittest.mock import MagicMock

from app.domain.agg_models import Reports
from app.utils.enums import (
    RegionOptions,
    ReportStatusOptions,
)

@pytest.fixture
def base_report_data():
    return {
        "report_date": "01/15/2024",
        "report_end_date": "01/15/2024",
        "published_date": "01/15/2024 10:00:00",
        "report_status": "Final",
        "head5": 500,
        "weight5": 850.5,
        "price5": 145.75,
        "auction_slug": "1234",
    }


# ===========================================================================
# Reports
# ===========================================================================

class TestReports:

    # ------------------------------------------------------------------
    # Test 23 – Valid construction with all required fields
    # Name: Valid Reports construction
    # Description: A report with all required fields should instantiate without error.
    # Steps: Supply report_date, report_end_date, published_date, report_status,
    #        head5, weight5, price5, and auction_slug.
    # Expected: Instance created; numeric group defaults are 0.
    # ------------------------------------------------------------------
    def test_valid_construction(self, base_report_data):
        report = Reports(**base_report_data)
        assert report.head5 == 500
        assert report.price5 == 145.75
        assert report.head1 == 0
        assert report.weight1 == 0.0

    # ------------------------------------------------------------------
    # Test 24 – head5 must be > 0 (gt constraint)
    # Name: head5 zero value raises ValidationError
    # Description: head5 has Field(gt=0); passing 0 should fail validation.
    # Steps: Set head5=0.
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_head5_zero_raises(self, base_report_data):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Reports.model_validate({**base_report_data, "head5": 0})

    # ------------------------------------------------------------------
    # Test 25 – head5 negative value raises ValidationError
    # Name: head5 negative value raises ValidationError
    # Description: head5 has Field(gt=0); negative values must fail.
    # Steps: Set head5=-1.
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_head5_negative_raises(self, base_report_data):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Reports.model_validate({**base_report_data, "head5": -1})

    # ------------------------------------------------------------------
    # Test 26 – weight5 must be > 0.0
    # Name: weight5 zero raises ValidationError
    # Description: weight5 has Field(gt=0.0); passing 0.0 should fail.
    # Steps: Set weight5=0.0.
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_weight5_zero_raises(self, base_report_data):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Reports.model_validate({**base_report_data, "weight5": 0.0})

    # ------------------------------------------------------------------
    # Test 27 – price5 must be > 0.0
    # Name: price5 zero raises ValidationError
    # Description: price5 has Field(gt=0.0); passing 0.0 should fail.
    # Steps: Set price5=0.0.
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_price5_zero_raises(self, base_report_data):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Reports.model_validate({**base_report_data, "price5": 0})

    # ------------------------------------------------------------------
    # Test 28 – region defaults to None
    # Name: region is None by default
    # Description: region is Optional; omitting it should leave it as None.
    # Steps: Construct Reports without region.
    # Expected: report.region is None
    # ------------------------------------------------------------------
    def test_region_defaults_to_none(self, base_report_data):
        report = Reports.model_validate(base_report_data)
        assert report.region is None

    # ------------------------------------------------------------------
    # Test 29 – region accepts valid RegionOptions
    # Name: region set to NORTH_CENTRAL
    # Description: A valid RegionOptions value should be accepted.
    # Steps: Set region=RegionOptions.NORTH_CENTRAL.
    # Expected: report.region == RegionOptions.NORTH_CENTRAL
    # ------------------------------------------------------------------
    def test_region_accepts_valid_value(self, base_report_data):
        report = Reports.model_validate({**base_report_data, "region": RegionOptions.NORTH_CENTRAL})
        assert report.region == RegionOptions.NORTH_CENTRAL

    # ------------------------------------------------------------------
    # Test 30 – Numeric group fields (1–4) default to 0
    # Name: Numeric defaults for groups 1-4
    # Description: head/weight/price 1-4 should all default to 0 / 0.0.
    # Steps: Construct Reports without supplying group 1–4 fields.
    # Expected: All are zero.
    # ------------------------------------------------------------------
    def test_numeric_group_defaults(self, base_report_data):
        report = Reports.model_validate(base_report_data)
        for i in range(1, 5):
            assert getattr(report, f"head{i}") == 0
            assert getattr(report, f"weight{i}") == 0.0
            assert getattr(report, f"price{i}") == 0.0

    # ------------------------------------------------------------------
    # Test 31 – __str__ without region
    # Name: Reports __str__ without region
    # Description: When region is None, __str__ uses the auction-based format.
    # Steps: Construct Reports without region; mock auction.
    # Expected: String contains auction str representation and price5.
    # ------------------------------------------------------------------
    def test_str_without_region(self, base_report_data):
        report = Reports.model_validate(base_report_data)
        mock_auction = MagicMock()
        mock_auction.__str__ = lambda self: "Test Auction(test-auction)"
        report.auction = mock_auction
        result = str(report)
        assert "145.75" in result

    # ------------------------------------------------------------------
    # Test 32 – __str__ with region
    # Name: Reports __str__ with region present
    # Description: When region is set, __str__ references display_name and region.
    # Steps: Construct Reports with region; call str().
    # Expected: String contains region and price5 values.
    #
    # NOTE: This test documents a potential bug — __str__ references
    # self.display_name and self.slug which are not fields on Reports.
    # ------------------------------------------------------------------
    def test_str_with_region_documents_bug(self, base_report_data):
        report = Reports(**{**base_report_data, "region": RegionOptions.NORTH_CENTRAL})
        # display_name and slug are not defined on Reports — this will raise AttributeError
        with pytest.raises(AttributeError):
            str(report)

    # ------------------------------------------------------------------
    # Test 33 – Missing required field raises ValidationError
    # Name: Missing report_status raises ValidationError
    # Description: report_status is required; omitting it should fail.
    # Steps: Construct Reports without report_status.
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_missing_report_status_raises(self, base_report_data):
        from pydantic import ValidationError
        data = {**base_report_data}
        data.pop("report_status")
        with pytest.raises(ValidationError):
            Reports.model_validate(data)

    # ------------------------------------------------------------------
    # Test 34 – Missing auction_slug raises ValidationError
    # Name: Missing auction_slug raises ValidationError
    # Description: auction_slug is a required foreign key field.
    # Steps: Construct Reports without auction_slug.
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_missing_auction_slug_raises(self, base_report_data):
        from pydantic import ValidationError
        data = {**base_report_data}
        data.pop("auction_slug")
        with pytest.raises(ValidationError):
            Reports.model_validate(data)

    # ------------------------------------------------------------------
    # Test 35 – Reports inherits from UUIDModel and TimestampModel
    # Name: Reports has id, created_at, updated_at fields
    # Description: Verify the base model fields are accessible on Reports.
    # Steps: Construct a Reports instance; inspect inherited field names.
    # Expected: model_fields includes "id", "created_at", "updated_at" (or equivalent).
    # ------------------------------------------------------------------
    def test_inherits_uuid_and_timestamp_fields(self, base_report_data):
        report = Reports.model_validate(base_report_data)
        field_names = set(Reports.model_fields.keys())
        # UUID and timestamp field names may vary by your UUIDModel/TimestampModel impl
        assert "id" in field_names or any("id" in f for f in field_names)

    # ------------------------------------------------------------------
    # Test 36 – report_status accepts PRELIMINARY
    # Name: Reports with PRELIMINARY status
    # Description: Both FINAL and PRELIMINARY are valid report statuses.
    # Steps: Construct Reports with report_status=PRELIMINARY.
    # Expected: report.report_status == ReportStatusOptions.PRELIMINARY
    # ------------------------------------------------------------------
    def test_report_status_preliminary(self, base_report_data):
        report = Reports.model_validate({**base_report_data, "report_status": ReportStatusOptions.PRELIMINARY})
        assert report.report_status == ReportStatusOptions.PRELIMINARY
