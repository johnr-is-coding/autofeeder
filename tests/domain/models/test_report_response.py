import pytest

from pydantic import ValidationError

from app.domain.models import ReportDetail, ReportResponse, ReportStats
from app.utils.enums import RegionOptions


@pytest.fixture
def valid_stats_data():
    return {"returnedRows": 1}


@pytest.fixture
def valid_report_detail_data():
    return {
        "report_date": "01/15/2024",
        "report_end_date": "01/15/2024",
        "published_date": "01/15/2024 10:00:00",
        "head_count": 500,
        "avg_weight": 850.5,
        "avg_price": 145.75,
    }

@pytest.fixture
def valid_report_detail(valid_report_detail_data):
    return ReportDetail(**valid_report_detail_data)


# ===========================================================================
# ReportStats
# ===========================================================================

class TestReportStats:

    # ------------------------------------------------------------------
    # Test 1 – Valid construction via alias
    # Name: Valid ReportStats construction
    # Description: ReportStats should instantiate correctly when supplied
    #              with the "returnedRows" alias key.
    # Steps: Pass {"returnedRows": 1}.
    # Expected: Instance created; returned_rows == 1
    # ------------------------------------------------------------------
    def test_valid_construction_via_alias(self, valid_stats_data):
        stats = ReportStats(**valid_stats_data)
        assert stats.returned_rows == 1

    # ------------------------------------------------------------------
    # Test 2 – Valid construction with extra fields
    # Name: Extra fields are ignored
    # Description: ReportStats should ignore any extra fields not defined in the model.
    # Steps: Pass {"returnedRows": 10, "userAllowedRows": 10000}
    # Expected: Instance created; returned_rows == 10; no error raised.
    # ------------------------------------------------------------------
    def test_extra_fields_ignored(self):
        stats = ReportStats(**{"returnedRows": 10, "userAllowedRows": 10000})
        assert stats.returned_rows == 10

    # ------------------------------------------------------------------
    # Test 3 – returnedRows alias is required
    # Name: Missing returnedRows raises ValidationError
    # Description: returned_rows has no default; omitting it should fail.
    # Steps: Construct ReportStats with an empty dict.
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_missing_returned_rows_raises(self):
        with pytest.raises(ValidationError):
            ReportStats(**{})

    # ------------------------------------------------------------------
    # Test 4 – Direct field name is not accepted without alias mode
    # Name: Snake_case field name not accepted by default
    # Description: By default SQLModel uses the alias as the input key.
    #              Passing "returned_rows" directly should fail.
    # Steps: Pass {"returned_rows": 10}.
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_snake_case_key_not_accepted(self):
        with pytest.raises(ValidationError):
            ReportStats(**{"returned_rows": 10})

    # ------------------------------------------------------------------
    # Test 5 – returned_rows must be an integer
    # Name: Non-integer returnedRows raises ValidationError
    # Description: Passing a non-coercible string should fail validation.
    # Steps: Pass {"returnedRows": "not-a-number"}.
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_non_integer_raises(self):
        with pytest.raises(ValidationError):
            ReportStats(**{"returnedRows": "not-a-number"})

    # ------------------------------------------------------------------
    # Test 6 – Integer coercion from string
    # Name: Numeric string is coerced to int
    # Description: Pydantic will coerce a numeric string to int.
    # Steps: Pass {"returnedRows": "5"}.
    # Expected: stats.returned_rows == 5
    # ------------------------------------------------------------------
    def test_numeric_string_is_coerced(self):
        stats = ReportStats(**{"returnedRows": "5"})
        assert stats.returned_rows == 5

    # ------------------------------------------------------------------
    # Test 7 – Zero is a valid value
    # Name: returned_rows accepts zero
    # Description: Zero is a valid row count (e.g. empty result set).
    # Steps: Pass {"returnedRows": 0}.
    # Expected: stats.returned_rows == 0
    # ------------------------------------------------------------------
    def test_zero_is_valid(self):
        stats = ReportStats(**{"returnedRows": 0})
        assert stats.returned_rows == 0


class TestReportDetail:

    # ------------------------------------------------------------------
    # Test 1 – Valid construction with all required fields
    # Name: Valid ReportDetail construction
    # Description: A fully-populated ReportDetail should instantiate without error.
    # Steps: Supply all required fields with valid values.
    # Expected: Instance created; field values match inputs.
    # ------------------------------------------------------------------
    def test_valid_construction(self, valid_report_detail_data):
        report = ReportDetail(**valid_report_detail_data)
        assert report.head_count == 500
        assert report.avg_weight == 850.5
        assert report.avg_price == 145.75

    # ------------------------------------------------------------------
    # Test 2 - Valid construction with extra fields
    # Name: Extra fields are ignored
    # Description: ReportDetail should ignore any extra fields not defined in the model.
    # Steps: Add an extra key to the input data.
    # Expected: Instance created; extra field is ignored; no error raised.
    # ------------------------------------------------------------------
    def test_extra_fields_ignored(self, valid_report_detail_data):
        data = {**valid_report_detail_data, "extra_field": "should be ignored"}
        report = ReportDetail(**data)
        assert report.head_count == 500
        assert report.avg_weight == 850.5
        assert report.avg_price == 145.75

    # ------------------------------------------------------------------
    # Test 2 – avg_weight alias "wtd_avg_weight"
    # Name: avg_weight via wtd_avg_weight alias
    # Description: avg_weight should be populated when the payload key is "wtd_avg_weight".
    # Steps: Pass "wtd_avg_weight" instead of "avg_weight".
    # Expected: report.avg_weight == 900.0
    # ------------------------------------------------------------------
    def test_avg_weight_alias(self, valid_report_detail_data):
        data = {**valid_report_detail_data}
        data.pop("avg_weight")
        data["wtd_avg_weight"] = 900.0
        report = ReportDetail(**data)
        assert report.avg_weight == 900.0

    # ------------------------------------------------------------------
    # Test 3 – avg_weight type string
    # Name: avg_weight as string"
    # Description: avg_weight should be cast to float when the payload key is str.
    # Steps: Pass "900.0" instead of 900.0.
    # Expected: report.avg_weight == 900.0
    # ------------------------------------------------------------------
    def test_avg_weight_string(self, valid_report_detail_data):
        data = {**valid_report_detail_data}
        data.pop("avg_weight")
        data["avg_weight"] = "900.0"
        report = ReportDetail(**data)
        assert report.avg_weight == 900.0

    # ------------------------------------------------------------------
    # Test 4 – avg_price alias "wtd_Avg_Price"
    # Name: avg_price via wtd_Avg_Price alias
    # Description: avg_price should be populated when the payload key is "wtd_Avg_Price".
    # Steps: Pass "wtd_Avg_Price" instead of "avg_price".
    # Expected: report.avg_price == 200.0
    # ------------------------------------------------------------------
    def test_avg_price_alias_title_case(self, valid_report_detail_data):
        data = {**valid_report_detail_data}
        data.pop("avg_price")
        data["wtd_Avg_Price"] = 200.0
        report = ReportDetail(**data)
        assert report.avg_price == 200.0

    # ------------------------------------------------------------------
    # Test 5 – avg_price alias "wtd_avg_price"
    # Name: avg_price via wtd_avg_price alias
    # Description: avg_price should be populated when the payload key is "wtd_avg_price".
    # Steps: Pass "wtd_avg_price" instead of "avg_price".
    # Expected: report.avg_price == 199.99
    # ------------------------------------------------------------------
    def test_avg_price_alias_lower_case(self, valid_report_detail_data):
        data = {**valid_report_detail_data}
        data.pop("avg_price")
        data["wtd_avg_price"] = 199.99
        report = ReportDetail(**data)
        assert report.avg_price == 199.99

    # ------------------------------------------------------------------
    # Test 6 – avg_price type string
    # Name: avg_price as string"
    # Description: avg_price should be cast to float when the payload key is str.
    # Steps: Pass "199.99" instead of 199.99.
    # Expected: report.avg_price == 199.99
    # ------------------------------------------------------------------
    def test_avg_price_string(self, valid_report_detail_data):
        data = {**valid_report_detail_data}
        data.pop("avg_price")
        data["avg_price"] = "199.99"
        report = ReportDetail(**data)
        assert report.avg_price == 199.99

    # ------------------------------------------------------------------
    # Test 7 – region alias "region_name"
    # Name: region via region_name alias
    # Description: region should be populated when the payload key is "region_name".
    # Steps: Pass "region_name" with a valid RegionOptions value.
    # Expected: report.region == RegionOptions.NORTH_CENTRAL
    # ------------------------------------------------------------------
    def test_region_alias_region_name(self, valid_report_detail_data):
        data = {**valid_report_detail_data, "region_name": "North Central"}
        report = ReportDetail(**data)
        assert report.region == RegionOptions.NORTH_CENTRAL

    # ------------------------------------------------------------------
    # Test 8 – region defaults to None
    # Name: region defaults to None when omitted
    # Description: region is Optional; omitting it should leave it as None.
    # Steps: Construct ReportDetail without a region key.
    # Expected: report.region is None
    # ------------------------------------------------------------------
    def test_region_defaults_to_none(self, valid_report_detail_data):
        data = {k: v for k, v in valid_report_detail_data.items() if k != "region_name"}
        report = ReportDetail(**data)
        assert report.region is None

    # ------------------------------------------------------------------
    # Test 9 – Missing required field raises ValidationError
    # Name: Missing head_count raises error
    # Description: head_count is required; omitting it should raise ValidationError.
    # Steps: Construct ReportDetail without head_count.
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_missing_required_field_raises(self, valid_report_detail_data):
        data = {**valid_report_detail_data}
        data.pop("head_count")
        with pytest.raises(ValidationError):
            ReportDetail(**data)

    # ------------------------------------------------------------------
    # Test 10 – Invalid type for head_count
    # Name: Non-integer head_count
    # Description: Passing a string that can't be coerced to int should raise ValidationError.
    # Steps: Set head_count to "not-a-number".
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_invalid_head_count_type(self, valid_report_detail_data):
        data = {**valid_report_detail_data, "head_count": "not-a-number"}
        with pytest.raises(ValidationError):
            ReportDetail(**data)


# ===========================================================================
# ReportResponse
# ===========================================================================

class TestReportResponse:

    # ------------------------------------------------------------------
    # Test 9 – Valid construction with one result
    # Name: Valid ReportResponse with one result
    # Description: A ReportResponse with a single ReportDetail and valid
    #              ReportStats should instantiate without error.
    # Steps: Construct ReportResponse with results=[detail] and stats.
    # Expected: Instance created; len(response.results) == 1
    # ------------------------------------------------------------------
    def test_valid_construction_single_result(self, valid_report_detail, valid_stats_data):
        stats = ReportStats(**valid_stats_data)
        response = ReportResponse(results=[valid_report_detail], stats=stats)
        assert len(response.results) == 1
        assert response.stats.returned_rows == 1

    # ------------------------------------------------------------------
    # Test 10 – Valid construction with multiple results
    # Name: Valid ReportResponse with multiple results
    # Description: results should accept a list of multiple ReportDetail instances.
    # Steps: Construct ReportResponse with three ReportDetail instances.
    # Expected: len(response.results) == 3
    # ------------------------------------------------------------------
    def test_valid_construction_multiple_results(self, valid_report_detail, valid_stats_data):
        stats = ReportStats(**valid_stats_data)
        response = ReportResponse(
            results=[valid_report_detail, valid_report_detail, valid_report_detail],
            stats={"returnedRows": 3},
        )
        assert len(response.results) == 3
        assert response.stats.returned_rows == 3
        assert response.row_count == 3

    # ------------------------------------------------------------------
    # Test 11 – Empty results list is valid
    # Name: ReportResponse accepts empty results
    # Description: An empty results list is valid (no reports returned).
    # Steps: Construct ReportResponse with results=[].
    # Expected: response.results == []
    # ------------------------------------------------------------------
    def test_empty_results_list_is_valid(self, valid_stats_data):
        stats = ReportStats(**valid_stats_data)
        response = ReportResponse(results=[], stats=stats)
        assert response.results == []

    # ------------------------------------------------------------------
    # Test 12 – stats is required
    # Name: Missing stats raises ValidationError
    # Description: stats has no default; omitting it should fail.
    # Steps: Construct ReportResponse without stats.
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_missing_stats_raises(self, valid_report_detail):
        with pytest.raises(ValidationError):
            ReportResponse(results=[valid_report_detail])

    # ------------------------------------------------------------------
    # Test 13 – results is required
    # Name: Missing results raises ValidationError
    # Description: results has no default; omitting it should fail.
    # Steps: Construct ReportResponse without results.
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_missing_results_raises(self, valid_stats_data):
        stats = ReportStats(**valid_stats_data)
        with pytest.raises(ValidationError):
            ReportResponse(stats=stats)

    # ------------------------------------------------------------------
    # Test 14 – results must be a list
    # Name: Non-list results raises ValidationError
    # Description: Passing a single ReportDetail instead of a list should fail.
    # Steps: Pass results=valid_report_detail (not wrapped in a list).
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_non_list_results_raises(self, valid_report_detail, valid_stats_data):
        stats = ReportStats(**valid_stats_data)
        with pytest.raises(ValidationError):
            ReportResponse(results=valid_report_detail, stats=stats)

    # ------------------------------------------------------------------
    # Test 15 – results list items must be ReportDetail
    # Name: Invalid results item type raises ValidationError
    # Description: A list containing non-ReportDetail items should fail.
    # Steps: Pass results=["not a report detail"].
    # Expected: pydantic.ValidationError is raised.
    # ------------------------------------------------------------------
    def test_invalid_results_item_type_raises(self, valid_stats_data):
        stats = ReportStats(**valid_stats_data)
        with pytest.raises(ValidationError):
            ReportResponse(results=["not a report detail"], stats=stats)

    # ------------------------------------------------------------------
    # Test 16 – stats must be a ReportStats instance
    # Name: Invalid stats type raises ValidationError
    # Description: Passing a plain dict as stats should fail.
    # Steps: Pass stats={"returnedRows": 10} (not a ReportStats instance).
    # Expected: Instance created via Pydantic coercion, OR ValidationError.
    #
    # NOTE: Pydantic v2 will coerce a matching dict into ReportStats
    # automatically. This test documents that behavior.
    # ------------------------------------------------------------------
    def test_stats_dict_is_coerced(self, valid_report_detail):
        response = ReportResponse(
            results=[valid_report_detail],
            stats={"returnedRows": 1},
        )
        assert isinstance(response.stats, ReportStats)
        assert response.stats.returned_rows == 1

    # ------------------------------------------------------------------
    # Test 17 – results items are ReportDetail instances
    # Name: Results items are ReportDetail
    # Description: Each item in response.results should be a ReportDetail.
    # Steps: Construct ReportResponse; check type of each result.
    # Expected: All items are ReportDetail instances.
    # ------------------------------------------------------------------
    def test_results_items_are_report_detail(self, valid_report_detail, valid_stats_data):
        stats = ReportStats(**valid_stats_data)
        response = ReportResponse(results=[valid_report_detail], stats=stats)
        for item in response.results:
            assert isinstance(item, ReportDetail)

    # ------------------------------------------------------------------
    # Test 18 – stats row count matches results length
    # Name: stats.returned_rows reflects result count
    # Description: While not enforced by the schema, documents the expected
    #              relationship between returned_rows and len(results).
    # Steps: Build a response where returned_rows == len(results).
    # Expected: response.stats.returned_rows == len(response.results)
    # ------------------------------------------------------------------
    def test_stats_row_count_matches_results_length(
        self, valid_report_detail, valid_report_detail_data
    ):
        details = [ReportDetail(**valid_report_detail_data) for _ in range(3)]
        stats = ReportStats(**{"returnedRows": 3})
        response = ReportResponse(results=details, stats=stats)
        assert response.stats.returned_rows == len(response.results)

    # ------------------------------------------------------------------
    # Test 19 – ReportResponse built from raw dict via model_validate
    # Name: ReportResponse constructed from raw API payload
    # Description: model_validate should correctly parse a full nested
    #              dict as returned by the MMN API.
    # Steps: Pass a raw dict matching the API response shape.
    # Expected: Instance created with correct nested values.
    # ------------------------------------------------------------------
    def test_constructed_from_raw_dict(self, valid_report_detail_data):
        payload = {
            "results": [valid_report_detail_data],
            "stats": {"returnedRows": 1},
        }
        response = ReportResponse.model_validate(payload)
        assert len(response.results) == 1
        assert response.stats.returned_rows == 1
        assert isinstance(response.results[0], ReportDetail)

    # ------------------------------------------------------------------
    # Test 20 – ReportDetail region is preserved through ReportResponse
    # Name: ReportDetail region preserved in ReportResponse
    # Description: Optional fields on nested ReportDetail should survive
    #              being wrapped in a ReportResponse.
    # Steps: Build a ReportDetail with a region; wrap in ReportResponse.
    # Expected: response.results[0].region == RegionOptions.NORTH_CENTRAL
    # ------------------------------------------------------------------
    def test_report_detail_region_preserved(self, valid_report_detail_data):
        data = {**valid_report_detail_data, "region": RegionOptions.NORTH_CENTRAL}
        detail = ReportDetail(**data)
        stats = ReportStats(**{"returnedRows": 1})
        response = ReportResponse(results=[detail], stats=stats)
        assert response.results[0].region == RegionOptions.NORTH_CENTRAL