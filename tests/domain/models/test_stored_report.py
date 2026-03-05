from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.domain.models.stored_report import StoredReport
from app.utils.enums import MarketType, ReportStatus


class TestStoredReport:

    @pytest.fixture
    def stored_report_data(self):
        return {
            "slug": "1234",
            "report_date": date(2024, 6, 1),
            "published_date": datetime(2024, 6, 2, 14, 30, 0),
            "report_status": ReportStatus.FINAL,
            "market_type": MarketType.LIVE,
            "has_corrections": False,
        }

    # --- Construction ---

    def test_valid_construction(self, stored_report_data):
        report = StoredReport.model_validate(stored_report_data)
        assert report.slug == "1234"
        assert report.report_date == date(2024, 6, 1)
        assert report.published_date == datetime(2024, 6, 2, 14, 30, 0)
        assert report.report_status == ReportStatus.FINAL
        assert report.market_type == MarketType.LIVE
        assert report.has_corrections is False

    # --- Required field nullability ---

    def test_slug_none_raises(self, stored_report_data):
        stored_report_data["slug"] = None
        with pytest.raises(ValidationError):
            StoredReport.model_validate(stored_report_data)

    def test_report_date_none_raises(self, stored_report_data):
        stored_report_data["report_date"] = None
        with pytest.raises(ValidationError):
            StoredReport.model_validate(stored_report_data)

    def test_published_date_none_raises(self, stored_report_data):
        stored_report_data["published_date"] = None
        with pytest.raises(ValidationError):
            StoredReport.model_validate(stored_report_data)

    def test_has_corrections_none_raises(self, stored_report_data):
        stored_report_data["has_corrections"] = None
        with pytest.raises(ValidationError):
            StoredReport.model_validate(stored_report_data)

    # --- ReportStatus ---

    def test_report_status_final(self, stored_report_data):
        report = StoredReport.model_validate(stored_report_data)
        assert report.report_status == ReportStatus.FINAL

    def test_report_status_preliminary(self, stored_report_data):
        stored_report_data["report_status"] = ReportStatus.PRELIMINARY
        report = StoredReport.model_validate(stored_report_data)
        assert report.report_status == ReportStatus.PRELIMINARY

    # --- MarketType ---

    def test_market_type_live(self, stored_report_data):
        report = StoredReport.model_validate(stored_report_data)
        assert report.market_type == MarketType.LIVE

    def test_market_type_direct(self, stored_report_data):
        stored_report_data["market_type"] = MarketType.DIRECT
        report = StoredReport.model_validate(stored_report_data)
        assert report.market_type == MarketType.DIRECT

    def test_market_type_video(self, stored_report_data):
        stored_report_data["market_type"] = MarketType.VIDEO
        report = StoredReport.model_validate(stored_report_data)
        assert report.market_type == MarketType.VIDEO

    # --- has_corrections ---

    def test_has_corrections_false(self, stored_report_data):
        report = StoredReport.model_validate(stored_report_data)
        assert report.has_corrections is False

    def test_has_corrections_true(self, stored_report_data):
        stored_report_data["has_corrections"] = True
        report = StoredReport.model_validate(stored_report_data)
        assert report.has_corrections is True
