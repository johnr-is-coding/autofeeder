from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.domain.models.report import Report
from app.utils.enums import Region, ReportStatus


class TestReport:

    @pytest.fixture
    def report_data(self):
        return {
            "report_date": date(2024, 6, 1),
            "report_end_date": date(2024, 6, 7),
            "published_date": datetime(2024, 6, 2, 14, 30, 0),
            "report_status": ReportStatus.FINAL,
            "head5": 100,
            "weight5": 850.0,
            "price5": 350.0,
            "auction_slug": "1234",
        }

    # --- Construction ---

    def test_valid_construction(self, report_data):
        report = Report.model_validate(report_data)
        assert report.report_date == date(2024, 6, 1)
        assert report.report_end_date == date(2024, 6, 7)
        assert report.published_date == datetime(2024, 6, 2, 14, 30, 0)
        assert report.report_status == ReportStatus.FINAL
        assert report.head5 == 100
        assert report.weight5 == 850.0
        assert report.price5 == 350.0
        assert report.auction_slug == "1234"

    # --- Defaults ---

    def test_region_defaults_to_empty(self, report_data):
        report = Report.model_validate(report_data)
        assert report.region == Region.EMPTY

    def test_weight_class_slots_default_to_zero(self, report_data):
        report = Report.model_validate(report_data)
        for slot in range(1, 5):
            assert getattr(report, f"head{slot}") == 0
            assert getattr(report, f"weight{slot}") == 0.0
            assert getattr(report, f"price{slot}") == 0.0

    # --- ReportStatus ---

    def test_report_status_final(self, report_data):
        report = Report.model_validate(report_data)
        assert report.report_status == ReportStatus.FINAL

    def test_report_status_preliminary(self, report_data):
        report_data["report_status"] = ReportStatus.PRELIMINARY
        report = Report.model_validate(report_data)
        assert report.report_status == ReportStatus.PRELIMINARY

    # --- Region ---

    def test_region_north_central(self, report_data):
        report_data["region"] = Region.NORTH_CENTRAL
        report = Report.model_validate(report_data)
        assert report.region == Region.NORTH_CENTRAL

    def test_region_south_central(self, report_data):
        report_data["region"] = Region.SOUTH_CENTRAL
        report = Report.model_validate(report_data)
        assert report.region == Region.SOUTH_CENTRAL

    def test_region_from_string_case_insensitive(self, report_data):
        report_data["region"] = "north central"
        report = Report.model_validate(report_data)
        assert report.region == Region.NORTH_CENTRAL

    # --- Weight-class slots 1–4 ---

    def test_weight_class_slots_custom_values(self, report_data):
        report_data.update({
            "head1": 10, "weight1": 800.0, "price1": 300.0,
            "head2": 20, "weight2": 850.0, "price2": 325.0,
            "head3": 30, "weight3": 900.0, "price3": 350.0,
            "head4": 40, "weight4": 950.0, "price4": 375.0,
        })
        report = Report.model_validate(report_data)
        assert report.head1 == 10
        assert report.weight1 == 800.0
        assert report.price1 == 300.0
        assert report.head4 == 40
        assert report.weight4 == 950.0
        assert report.price4 == 375.0

    # --- Slot 5 (totals) gt=0 constraint ---

    def test_head5_zero_raises(self, report_data):
        report_data["head5"] = 0
        with pytest.raises(ValidationError):
            Report.model_validate(report_data)

    def test_head5_negative_raises(self, report_data):
        report_data["head5"] = -1
        with pytest.raises(ValidationError):
            Report.model_validate(report_data)

    def test_weight5_zero_raises(self, report_data):
        report_data["weight5"] = 0.0
        with pytest.raises(ValidationError):
            Report.model_validate(report_data)

    def test_weight5_negative_raises(self, report_data):
        report_data["weight5"] = -1.0
        with pytest.raises(ValidationError):
            Report.model_validate(report_data)

    def test_price5_zero_raises(self, report_data):
        report_data["price5"] = 0.0
        with pytest.raises(ValidationError):
            Report.model_validate(report_data)

    def test_price5_negative_raises(self, report_data):
        report_data["price5"] = -1.0
        with pytest.raises(ValidationError):
            Report.model_validate(report_data)
