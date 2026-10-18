"""Calendar math for deadlines. Pure functions, no time zones: deadlines are calendar dates."""

import calendar
import datetime as dt
import re
from typing import Optional, Tuple

# Finds "180 calendar days", "4 months", "10 business days" or "60 (sixty) days" anywhere in a phrase.
_DURATION = re.compile(r"\b(\d{1,3})\s*(?:\([a-z -]+\)\s*)?(?:(calendar|business|working)\s+)?(days?|months?|weeks?|hours?)\b")


def parse_duration(normalized: Optional[str]) -> Optional[Tuple[int, str, str]]:
    """'180 calendar days of the date ...' -> (180, 'days', 'calendar'). None for anything we don't compute (e.g. hours)."""
    if not normalized:
        return None
    m = _DURATION.search(normalized.lower())
    if not m:
        return None
    qty, qualifier, unit = int(m.group(1)), (m.group(2) or "calendar"), m.group(3)
    unit = unit if unit.endswith("s") else unit + "s"
    if unit == "hours" or qty <= 0:
        return None
    return qty, unit, "business" if qualifier in {"business", "working"} else "calendar"


def add_months(d: dt.date, months: int) -> dt.date:
    """Same day-of-month N months later, clamped to month end (Oct 31 + 4 months = Feb 28/29)."""
    index = d.month - 1 + months
    year, month = d.year + index // 12, index % 12 + 1
    return dt.date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def add_business_days(d: dt.date, days: int) -> dt.date:
    """Skips Saturdays and Sundays. Public holidays are not skipped (callers must say so)."""
    current, remaining = d, days
    while remaining > 0:
        current += dt.timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def apply_duration(start: dt.date, duration: Tuple[int, str, str]) -> dt.date:
    qty, unit, kind = duration
    if unit == "months":
        return add_months(start, qty)
    if unit == "weeks":
        return start + dt.timedelta(weeks=qty)
    if kind == "business":
        return add_business_days(start, qty)
    return start + dt.timedelta(days=qty)


def describe(d: dt.date) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"
