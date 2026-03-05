import pytest
from datetime import date, datetime, timezone

from app.utils.validators import parse_date, parse_datetime


class TestParseDate:
    def test_date_passthrough(self):
        d = date(2024, 1, 15)
        assert parse_date(d) == d

    def test_datetime_returns_date_part(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        assert parse_date(dt) == date(2024, 1, 15)

    def test_iso_string(self):
        assert parse_date("2024-01-15") == date(2024, 1, 15)

    def test_string_with_time_component(self):
        assert parse_date("2024-01-15T10:30:00") == date(2024, 1, 15)

    def test_string_with_timezone(self):
        assert parse_date("2024-01-15T10:30:00+05:00") == date(2024, 1, 15)

    def test_human_readable_string(self):
        assert parse_date("January 15, 2024") == date(2024, 1, 15)

    def test_unparseable_string_raises(self):
        with pytest.raises(Exception):
            parse_date("not a date")


class TestParseDatetime:
    def test_datetime_passthrough(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        assert parse_datetime(dt) == dt

    def test_naive_datetime_passthrough(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = parse_datetime(dt)
        assert result.tzinfo is None

    def test_date_converts_to_midnight(self):
        result = parse_datetime(date(2024, 1, 15))
        assert result == datetime(2024, 1, 15, 0, 0, 0)
        assert result.tzinfo is None

    def test_naive_iso_string(self):
        result = parse_datetime("2024-01-15T10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)
        assert result.tzinfo is None

    def test_aware_string_converts_to_utc_naive(self):
        # +00:00 — already UTC, strips tzinfo
        result = parse_datetime("2024-01-15T10:30:00+00:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)
        assert result.tzinfo is None

    def test_aware_string_shifts_to_utc(self):
        # +05:00 means 10:30 local = 05:30 UTC
        result = parse_datetime("2024-01-15T10:30:00+05:00")
        assert result == datetime(2024, 1, 15, 5, 30, 0)
        assert result.tzinfo is None

    def test_aware_negative_offset_shifts_to_utc(self):
        # -05:00 means 10:30 local = 15:30 UTC
        result = parse_datetime("2024-01-15T10:30:00-05:00")
        assert result == datetime(2024, 1, 15, 15, 30, 0)
        assert result.tzinfo is None

    def test_unparseable_string_raises(self):
        with pytest.raises(Exception):
            parse_datetime("not a datetime")
