import pytest
from datetime import date, datetime
from dateutil.parser import ParserError
from pydantic import BaseModel, ValidationError

from app.utils.validators import (
    parse_date, 
    parse_datetime, 
    ReportDate, 
    ReportDateTime
)

# Timezone stripping convention (applies to parse_datetime / ReportDateTime):
#   If the parsed datetime is tz-aware, convert to UTC first, then strip tzinfo.
#   Examples:
#     "2024-06-15T10:30:00+05:30"  →  05:00 UTC  →  datetime(2024, 6, 15,  5,  0, 0)
#     "2024-06-15T10:30:00Z"       →  10:30 UTC  →  datetime(2024, 6, 15, 10, 30, 0)
#     "2024-06-15T23:00:00-03:00"  →  02:00 UTC  →  datetime(2024, 6, 16,  2,  0, 0)



# ---------------------------------------------------------------------------
# Helpers / Pydantic models used in integration tests
# ---------------------------------------------------------------------------

class ReportDateModel(BaseModel):
    report_date: ReportDate


class ReportDateTimeModel(BaseModel):
    report_dt: ReportDateTime

# ===========================================================================
# parse_date
# ===========================================================================

class TestParseDate:

    # TC-01
    def test_native_date_returned_as_is(self):
        """A date instance is returned unchanged."""
        d = date(2024, 6, 15)
        result = parse_date(d)
        assert result == d

    # TC-02
    def test_datetime_passes_isinstance_check(self):
        """datetime is a subclass of date so it is returned as-is, not truncated."""
        dt = datetime(2024, 6, 15, 10, 30)
        result = parse_date(dt)
        assert result == dt.date()

    # TC-03
    def test_us_slash_format(self):
        """MM/DD/YYYY string is parsed with dateutil's US-first default."""
        assert parse_date("06/15/2024") == date(2024, 6, 15)

    # TC-04
    def test_invalid_string_raises(self):
        """A non-parseable string raises ParserError or ValueError."""
        with pytest.raises((ParserError, ValueError)):
            parse_date("not-a-date")

    # TC-05
    def test_none_raises(self):
        """None raises TypeError or ParserError."""
        with pytest.raises((TypeError, ParserError)):
            parse_date(None)

    # TC-06
    def test_integer_raises(self):
        """An integer is not a supported input type and should raise."""
        with pytest.raises((TypeError, ParserError)):
            parse_date(1718444400)


# ===========================================================================
# parse_datetime
# ===========================================================================

class TestParseDatetime:

    # TC-10
    def test_native_datetime_returned_as_is(self):
        """A datetime instance is returned unchanged."""
        dt = datetime(2024, 6, 15, 10, 30, 0)
        result = parse_datetime(dt)
        assert result == dt

    # TC-11
    def test_date_object_converted_to_datetime(self):
        """A date object is NOT a datetime subclass, so it goes through dateutil
        and comes back as a naive datetime with time defaulting to midnight."""
        result = parse_datetime(date(2024, 6, 15))
        assert isinstance(result, datetime)
        assert result.date() == date(2024, 6, 15)
        assert result.hour == 0 and result.minute == 0 and result.second == 0
        assert result.tzinfo is None

    # TC-12
    def test_positive_offset_converted_to_utc_and_stripped(self):
        """A +05:30 string is shifted to UTC (-5h30m) and tzinfo stripped.
        10:30+05:30  ->  05:00 UTC  ->  naive datetime(2024, 6, 15, 5, 0, 0)"""
        result = parse_datetime("2024-06-15T10:30:00+05:30")
        assert isinstance(result, datetime)
        assert result.tzinfo is None
        assert result == datetime(2024, 6, 15, 5, 0, 0)

    # TC-12b
    def test_utc_z_offset_stripped(self):
        """A Z (UTC) string is kept at the same time and tzinfo stripped.
        10:30Z  ->  10:30 UTC  ->  naive datetime(2024, 6, 15, 10, 30, 0)"""
        result = parse_datetime("2024-06-15T10:30:00Z")
        assert isinstance(result, datetime)
        assert result.tzinfo is None
        assert result == datetime(2024, 6, 15, 10, 30, 0)

    # TC-12c
    def test_negative_offset_rolls_over_midnight(self):
        """A -03:00 string near midnight rolls over to the next UTC day.
        23:00-03:00  ->  02:00 UTC next day  ->  naive datetime(2024, 6, 16, 2, 0, 0)"""
        result = parse_datetime("2024-06-15T23:00:00-03:00")
        assert isinstance(result, datetime)
        assert result.tzinfo is None
        assert result == datetime(2024, 6, 16, 2, 0, 0)

    # TC-13
    def test_naive_datetime_string(self):
        """A string with no timezone info produces a naive datetime unchanged."""
        result = parse_datetime("06/15/2024 10:30:00")
        assert result == datetime(2024, 6, 15, 10, 30, 0)
        assert result.tzinfo is None

    # TC-14
    def test_date_only_string_defaults_midnight(self):
        """A date-only string is parsed into a naive datetime at midnight."""
        result = parse_datetime("06/15/2024")
        assert result == datetime(2024, 6, 15, 0, 0, 0)

    # TC-15
    def test_invalid_string_raises(self):
        """A non-parseable string raises ParserError or ValueError."""
        with pytest.raises((ParserError, ValueError)):
            parse_datetime("banana")

# ===========================================================================
# ReportDate / ReportDateTime Pydantic integration
# ===========================================================================

class TestReportDatePydantic:

    # TC-16
    def test_valid_string_coerced(self):
        """BeforeValidator correctly coerces a date string in a Pydantic model."""
        model = ReportDateModel(report_date="06/15/2024")
        assert model.report_date == date(2024, 6, 15)

    # TC-17
    def test_native_date_accepted(self):
        """A native date object is accepted directly."""
        model = ReportDateModel(report_date=date(2024, 6, 15))
        assert model.report_date == date(2024, 6, 15)

    # TC-18
    def test_datetime_string_truncated(self):
        """A datetime string is truncated to a date inside the model."""
        model = ReportDateModel(report_date="2024-06-15T23:59:59")
        assert model.report_date == date(2024, 6, 15)

    # TC-19
    def test_invalid_string_raises_validation_error(self):
        """An unparseable string surfaces as a Pydantic ValidationError."""
        with pytest.raises(ValidationError):
            ReportDateModel(report_date="not-a-date")


class TestReportDateTimePydantic:

    # TC-20
    def test_timezone_aware_string_coerced(self):
        """A timezone-aware string is coerced into a tz-aware datetime."""
        model = ReportDateTimeModel(report_dt="2024-06-15T10:30:00Z")
        assert isinstance(model.report_dt, datetime)
        assert model.report_dt.tzinfo is None
        assert model.report_dt.date() == date(2024, 6, 15)
        assert model.report_dt.hour == 10 and model.report_dt.minute == 30

    # TC-21
    def test_native_datetime_accepted(self):
        """A native datetime object is accepted directly."""
        dt = datetime(2024, 6, 15, 10, 30, 0)
        model = ReportDateTimeModel(report_dt=dt)
        assert model.report_dt == dt

    # TC-22
    def test_date_only_string_defaults_midnight(self):
        """A date-only string defaults to midnight in the model."""
        model = ReportDateTimeModel(report_dt="2024-06-15")
        assert model.report_dt == datetime(2024, 6, 15, 0, 0, 0)

    # TC-23
    def test_invalid_string_raises_validation_error(self):
        """An unparseable string surfaces as a Pydantic ValidationError."""
        with pytest.raises(ValidationError):
            ReportDateTimeModel(report_dt="not-a-datetime")