from typing import Annotated, Any
from datetime import date, datetime, timezone
from dateutil.parser import parse

from pydantic import BeforeValidator


def parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return parse(value).date()


def parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    dt = parse(value)
    if dt.tzinfo is not None:
        # Convert to UTC, then strip tzinfo to produce a naive UTC datetime
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


ReportDate = Annotated[date, BeforeValidator(parse_date)]
ReportDateTime = Annotated[datetime, BeforeValidator(parse_datetime)]