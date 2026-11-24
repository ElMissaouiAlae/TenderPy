"""Turn the source platform's date text into typed dates.

The platform shows a publication date as ``DD/MM/YYYY`` and a deadline as
``DD/MM/YYYY HH:mm`` in Moroccan local time, with a ``<br>`` between the
date and the time. Both the parser and the migration that converted stored
text use these functions, so their rules can't diverge.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

MOROCCO = ZoneInfo("Africa/Casablanca")

# A deadline without a time closes at the end of that day. Minutes, like the
# platform's own times, so it writes back to the platform's text unchanged.
END_OF_DAY = time(23, 59)

_DATE = r"(?P<day>\d{2})/(?P<month>\d{2})/(?P<year>\d{4})"
_PUBLICATION_DATE = re.compile(_DATE)
# The time may follow a space, a <br> tag, or nothing at all: text stored
# before typed dates ran the two together ("20/10/202611:00").
_DEADLINE = re.compile(
    _DATE + r"(?:(?:\s|<br\s*/?>)*(?P<hour>\d{2}):(?P<minute>\d{2}))?",
    re.IGNORECASE,
)


def parse_publication_date(text: str | None) -> date | None:
    """Read a publication date shown as ``DD/MM/YYYY``.

    Args:
        text: The date text as the platform shows it.

    Returns:
        The calendar date, or None if the text is missing or unreadable.
        Unreadable text is logged, never raised.
    """
    match = _fullmatch(_PUBLICATION_DATE, text)
    if match is None:
        _log_unreadable("publication date", text)
        return None
    try:
        return _date(match)
    except ValueError:
        _log_unreadable("publication date", text)
        return None


def parse_deadline(text: str | None) -> datetime | None:
    """Read a deadline shown as ``DD/MM/YYYY HH:mm``, in Moroccan local time.

    Args:
        text: The deadline text as the platform shows it. The time may be
            separated from the date by whitespace or a ``<br>`` tag, or be
            missing, in which case the deadline is the end of that day.

    Returns:
        A timezone-aware datetime in Africa/Casablanca, or None if the text
        is missing or unreadable. Unreadable text is logged, never raised.
    """
    match = _fullmatch(_DEADLINE, text)
    if match is None:
        _log_unreadable("deadline", text)
        return None
    try:
        if match["hour"] is None:
            time_of_day = END_OF_DAY
        else:
            time_of_day = time(int(match["hour"]), int(match["minute"]))
        return datetime.combine(_date(match), time_of_day, tzinfo=MOROCCO)
    except ValueError:
        _log_unreadable("deadline", text)
        return None


def in_moroccan_time(deadline: datetime | None) -> datetime | None:
    """Express a deadline in Moroccan local time, whatever timezone it was read in.

    Postgres hands timestamps back in the session's timezone (usually UTC);
    converting here, not in SQL, also avoids the database's own timezone
    rules for Africa/Casablanca, which may be out of date.
    """
    return deadline.astimezone(MOROCCO) if deadline is not None else None


def format_publication_date(value: date) -> str:
    """Write a publication date back in the platform's ``DD/MM/YYYY`` form."""
    return value.strftime("%d/%m/%Y")


def format_deadline(value: datetime) -> str:
    """Write a deadline back in the platform's ``DD/MM/YYYY HH:mm`` form, in Moroccan local time."""
    return value.astimezone(MOROCCO).strftime("%d/%m/%Y %H:%M")


def _fullmatch(pattern: re.Pattern[str], text: str | None) -> re.Match[str] | None:
    if text is None:
        return None
    return pattern.fullmatch(text.strip())


def _date(match: re.Match[str]) -> date:
    return date(int(match["year"]), int(match["month"]), int(match["day"]))


def _log_unreadable(kind: str, text: str | None) -> None:
    if text is not None and text.strip():
        logger.warning("Unreadable %s: %r", kind, text)
