from datetime import date, datetime

from pydantic import ValidationError
import pytest

from app.domain.models.schemas import IncomingReport, ReportDetail, ReportResponse, ReportStats
from app.utils.enums import MarketType, Region, ReportStatus

class TestIncomingReport:

    @pytest.fixture
    def incoming_report_data(self):
        return {
            "slug_id": "1234",
            "report_date": "06/01/2024",
            "published_date": "06/02/2024 14:30:00",
            "report_status": "Final",
            "market_types": ["Auction Livestock"],
            "hasCorrectionsInLastThreeDays": False
        }
    

    def test_valid_construction_via_aliases(self, incoming_report_data):
        report = IncomingReport(**incoming_report_data)
        assert report.slug == "1234"
        assert report.report_date == date(2024, 6, 1)
        assert report.published_date == datetime(2024, 6, 2, 14, 30, 0)
        assert report.report_status == ReportStatus.FINAL
        assert report.market_type == MarketType.LIVE
        assert report.has_corrections is False

    def test_valid_construction_via_model_validate(self, incoming_report_data):
        report = IncomingReport.model_validate(incoming_report_data)
        assert report.slug == "1234"
        assert report.report_date == date(2024, 6, 1)
        assert report.published_date == datetime(2024, 6, 2, 14, 30, 0)
        assert report.report_status == ReportStatus.FINAL
        assert report.market_type == MarketType.LIVE
        assert report.has_corrections is False

    def test_extra_fields_ignored(self, incoming_report_data):
        data = {**incoming_report_data, "extra_field": "should be ignored"}
        report = IncomingReport(**data)
        assert report.slug == "1234"

    def test_valid_construction_with_market_type_none(self, incoming_report_data):
        incoming_report_data["market_types"] = ["Unknown Market Type"]
        report = IncomingReport(**incoming_report_data)
        assert report.market_type is None

    def test_invalid_report_date(self, incoming_report_data):
        incoming_report_data["report_date"] = "invalid-date"  # Wrong format
        with pytest.raises(ValidationError):
            IncomingReport(**incoming_report_data)

    def test_invalid_published_date(self, incoming_report_data):
        incoming_report_data["published_date"] = "invalid-datetime"  # Wrong format
        with pytest.raises(ValidationError):
            IncomingReport(**incoming_report_data)

    def test_invalid_report_status(self, incoming_report_data):
        incoming_report_data["report_status"] = "UnknownStatus"
        with pytest.raises(ValidationError):
            IncomingReport(**incoming_report_data)

    def test_missing_required_fields(self, incoming_report_data):
        for key in incoming_report_data.keys():
            modified_data = incoming_report_data.copy()
            del modified_data[key]
            with pytest.raises(ValidationError) as e:
                IncomingReport(**modified_data)
            
            errors = e.value.errors()
            assert any(error["loc"] == (key,) and error["type"] == "missing" for error in errors)


class TestReportDetail:

    @pytest.fixture
    def report_detail_data(self):
        return {
            "report_date": "06/01/2024",
            "report_end_date": "06/01/2024",
            "published_date": "06/02/2024 14:30:00",
            "report_status": "Final",
            "head_count": 150,
            "avg_weight": "850.5",
            "avg_price": 350.5,
            "region_name": "North Central"
        }
    

    def test_valid_construction(self, report_detail_data):
        detail = ReportDetail(**report_detail_data)
        assert detail.report_date == date(2024, 6, 1)
        assert detail.report_end_date == date(2024, 6, 1)
        assert detail.published_date == datetime(2024, 6, 2, 14, 30, 0)
        assert detail.report_status == ReportStatus.FINAL
        assert detail.head_count == 150
        assert detail.avg_weight == 850.5
        assert detail.avg_price == 350.5
        assert detail.region == Region.NORTH_CENTRAL

    def test_valid_construction_with_missing_region(self, report_detail_data):
        report_detail_data.pop("region_name")
        detail = ReportDetail(**report_detail_data)
        assert detail.region is None

    def test_valid_construction_with_video_aliases(self, report_detail_data):
        report_detail_data["wtd_avg_weight"] = report_detail_data.pop("avg_weight")
        report_detail_data["wtd_Avg_Price"] = report_detail_data.pop("avg_price")
        detail = ReportDetail(**report_detail_data)
        assert detail.avg_weight == 850.5
        assert detail.avg_price == 350.5
        
    def test_valid_construction_with_direct_alias(self, report_detail_data):
        report_detail_data["wtd_avg_weight"] = report_detail_data.pop("avg_weight")
        report_detail_data["wtd_avg_price"] = report_detail_data.pop("avg_price")
        detail = ReportDetail(**report_detail_data)
        assert detail.avg_weight == 850.5
        assert detail.avg_price == 350.5


class TestReportStats:

    @pytest.fixture
    def report_stats_data(self):
        return {
            "returnedRows": 10
        }
    
    def test_valid_construction(self, report_stats_data):
        stats = ReportStats(**report_stats_data)
        assert stats.returned_rows == 10

    def test_missing_returned_rows(self, report_stats_data):
        report_stats_data.pop("returnedRows")
        with pytest.raises(ValidationError):
            ReportStats(**report_stats_data)
    
    def test_extra_fields_ignored(self, report_stats_data):
        data = {**report_stats_data, "extra_field": "should be ignored"}
        stats = ReportStats(**data)
        assert stats.returned_rows == 10


class TestReportResponse:
    @pytest.fixture
    def report_response_data(self):
        return {
            "results": [
                {
                    "report_date": "06/01/2024",
                    "report_end_date": "06/01/2024",
                    "published_date": "06/02/2024 14:30:00",
                    "report_status": "Final",
                    "head_count": 150,
                    "avg_weight": "850.5",
                    "avg_price": 350.5,
                    "region_name": "North Central"
                }
            ],
            "stats": {
                "returnedRows": 1
            }
        }
    
    def test_valid_construction(self, report_response_data):
        response = ReportResponse(**report_response_data)
        assert len(response.results) == 1
        detail = response.results[0]
        assert detail.report_date == date(2024, 6, 1)
        assert detail.report_end_date == date(2024, 6, 1)
        assert detail.published_date == datetime(2024, 6, 2, 14, 30, 0)
        assert detail.report_status == ReportStatus.FINAL
        assert detail.head_count == 150
        assert detail.avg_weight == 850.5
        assert detail.avg_price == 350.5
        assert detail.region == Region.NORTH_CENTRAL
        assert response.stats.returned_rows == 1
        assert response.row_count == 1