import pytest

from app.domain.models import Reports

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
def test_debug_reports_fields(base_report_data):
    from pydantic import ValidationError
    report = Reports(**{**base_report_data, "head5": -999, "price5": -999, "weight5": -999})
    print(Reports.model_fields.items())
    print(report.model_config)
    print(report.__class__.__mro__)