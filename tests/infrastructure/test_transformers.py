from datetime import date, datetime

import pytest

from app.domain.models.schemas import ReportDetail
from app.infrastructure.transformers import ReportTransformer
from app.utils.enums import Region, ReportStatus

SLUG = "test-auction"
PUB_DATE = datetime(2024, 1, 15, 8, 0, 0)
END_DATE = date(2024, 1, 14)
REPORT_DATE = date(2024, 1, 7)


def make_detail(
    avg_weight: float,
    head_count: int = 10,
    avg_price: float = 200.0,
    region=None,
    report_date=REPORT_DATE,
    report_status=ReportStatus.FINAL,
) -> ReportDetail:
    return ReportDetail.model_validate({
        "report_date": report_date.strftime("%m/%d/%Y"),
        "report_end_date": END_DATE.strftime("%m/%d/%Y"),
        "published_date": PUB_DATE.strftime("%m/%d/%Y %H:%M:%S"),
        "report_status": report_status,
        "head_count": head_count,
        "avg_weight": avg_weight,
        "avg_price": avg_price,
        "region_name": region,
    })


@pytest.fixture
def transformer():
    return ReportTransformer()


class TestAggregate:
    def test_empty_returns_zeros(self, transformer):
        head, weight, price = transformer._aggregate([])
        assert head == 0
        assert weight == 0.0
        assert price == 0.0

    def test_single_detail(self, transformer):
        detail = make_detail(avg_weight=750.0, head_count=10, avg_price=180.0)
        head, weight, price = transformer._aggregate([detail])
        assert head == 10
        assert weight == pytest.approx(750.0)
        assert price == pytest.approx(180.0)

    def test_weighted_average(self, transformer):
        # 10 head at 700 lbs / $100, 30 head at 800 lbs / $200
        # weighted weight = (10*700 + 30*800) / 40 = 31000/40 = 775
        # weighted price  = (10*100 + 30*200) / 40 = 7000/40 = 175
        details = [
            make_detail(avg_weight=700.0, head_count=10, avg_price=100.0),
            make_detail(avg_weight=800.0, head_count=30, avg_price=200.0),
        ]
        head, weight, price = transformer._aggregate(details)
        assert head == 40
        assert weight == pytest.approx(775.0)
        assert price == pytest.approx(175.0)


class TestAggregateBins:
    def test_bins_empty_group_returns_zeros(self, transformer):
        result = transformer._aggregate_bins([])
        for wc in range(1, 6):
            assert result[f"head{wc}"] == 0
            assert result[f"weight{wc}"] == 0.0
            assert result[f"price{wc}"] == 0.0

    def test_detail_placed_in_correct_bin(self, transformer):
        result = transformer._aggregate_bins([make_detail(avg_weight=720.0, head_count=5)])
        assert result["head1"] == 5
        assert result["head2"] == 0
        assert result["head3"] == 0
        assert result["head4"] == 0
        assert result["head5"] == 5

    def test_bin_boundaries(self, transformer):
        details = [
            make_detail(avg_weight=700.0),  # class 1
            make_detail(avg_weight=749.0),  # class 1
            make_detail(avg_weight=750.0),  # class 2
            make_detail(avg_weight=799.0),  # class 2
            make_detail(avg_weight=800.0),  # class 3
            make_detail(avg_weight=849.0),  # class 3
            make_detail(avg_weight=850.0),  # class 4
            make_detail(avg_weight=899.0),  # class 4
        ]
        result = transformer._aggregate_bins(details)
        assert result["head1"] == 20
        assert result["head2"] == 20
        assert result["head3"] == 20
        assert result["head4"] == 20
        assert result["head5"] == 80

    def test_total_includes_all_items(self, transformer):
        details = [
            make_detail(avg_weight=710.0, head_count=5, avg_price=100.0),
            make_detail(avg_weight=810.0, head_count=10, avg_price=200.0),
        ]
        result = transformer._aggregate_bins(details)
        assert result["head5"] == 15
        assert result["weight5"] == pytest.approx((5 * 710 + 10 * 810) / 15)
        assert result["price5"] == pytest.approx((5 * 100 + 10 * 200) / 15)


class TestGroupByFields:
    def test_groups_by_report_date(self):
        date1 = date(2024, 1, 7)
        date2 = date(2024, 1, 14)
        details = [
            make_detail(avg_weight=720.0, report_date=date1),
            make_detail(avg_weight=760.0, report_date=date2),
        ]
        groups = ReportTransformer._group_by_fields(details)
        assert len(groups) == 2
        assert (date1, None) in groups
        assert (date2, None) in groups

    def test_groups_by_region(self):
        details = [
            make_detail(avg_weight=720.0, region="North Central"),
            make_detail(avg_weight=720.0, region="South Central"),
            make_detail(avg_weight=720.0, region=None),
        ]
        groups = ReportTransformer._group_by_fields(details)
        assert len(groups) == 3

    def test_same_date_and_region_grouped_together(self):
        details = [
            make_detail(avg_weight=720.0, head_count=5),
            make_detail(avg_weight=720.0, head_count=10),
        ]
        groups = ReportTransformer._group_by_fields(details)
        assert len(groups) == 1
        assert len(list(groups.values())[0]) == 2


class TestCreateReportHeader:
    def test_extracts_header_fields(self):
        detail = make_detail(avg_weight=720.0, report_status=ReportStatus.PRELIMINARY)
        header = ReportTransformer._create_report_header(detail)
        assert header["report_end_date"] == END_DATE
        assert header["published_date"] == PUB_DATE
        assert header["report_status"] == ReportStatus.PRELIMINARY


class TestTransform:
    def test_returns_one_report_per_group(self, transformer):
        date1 = date(2024, 1, 7)
        date2 = date(2024, 1, 14)
        details = [
            make_detail(avg_weight=720.0, report_date=date1),
            make_detail(avg_weight=760.0, report_date=date2),
        ]
        reports = transformer.transform(details, SLUG)
        assert len(reports) == 2

    def test_report_metadata(self, transformer):
        detail = make_detail(avg_weight=720.0, report_status=ReportStatus.PRELIMINARY)
        r = transformer.transform([detail], SLUG)[0]
        assert r.auction_slug == SLUG
        assert r.report_date == REPORT_DATE
        assert r.report_end_date == END_DATE
        assert r.published_date == PUB_DATE
        assert r.report_status == ReportStatus.PRELIMINARY

    def test_report_region(self, transformer):
        details = [
            make_detail(avg_weight=720.0, region="North Central"),
            make_detail(avg_weight=720.0, region="South Central"),
            make_detail(avg_weight=720.0, region=None),
        ]
        reports = transformer.transform(details, SLUG)
        regions = {r.region for r in reports}
        assert regions == {Region.NORTH_CENTRAL, Region.SOUTH_CENTRAL, None}
