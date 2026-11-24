"""Read-only aggregate questions over tender records, for the Insights page.

Every query takes "now" as a parameter and never reads the clock itself, so
results are deterministic for a given time.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Protocol

from sqlalchemy import ColumnElement, func, select

from core.dates import in_moroccan_time
from persistence.database import Database
from persistence.exceptions import RepositoryError
from persistence.models import TenderRecord, closing_soon

# Closing-soon bucket edges: less than 3 days left, then less than 7, then
# the rest of the 14-day window.
_LT3_EDGE = timedelta(days=3)
_3TO7_EDGE = timedelta(days=7)


class Period(str, Enum):
    """How far back, by publication date, the period-aware insights look."""

    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    LAST_90_DAYS = "90d"
    ALL = "all"

    @property
    def days(self) -> int | None:
        """Number of calendar days the period covers, or None for all time."""
        return _PERIOD_DAYS[self]


_PERIOD_DAYS = {
    Period.LAST_7_DAYS: 7,
    Period.LAST_30_DAYS: 30,
    Period.LAST_90_DAYS: 90,
    Period.ALL: None,
}


@dataclass(frozen=True)
class InsightsFilter:
    """Which tenders a period-aware insight counts.

    The one place insights filters are built, so a later filter (a business
    profile's categories and locations) is added once and applies everywhere.

    Attributes:
        period: How far back, by publication date, to look.
        open_only: Count only open tenders (deadline still in the future).
    """

    period: Period = Period.LAST_30_DAYS
    open_only: bool = False

    def conditions(self, now: datetime) -> list[ColumnElement[bool]]:
        """SQL conditions selecting the tenders this filter counts at now.

        A period of N days covers the N calendar days ending today (the
        Moroccan local date): exactly N days ago is outside it. All time
        covers every publication date. A tender without a publication date
        is in no period.

        Args:
            now: The current time (timezone-aware), from the caller's clock.
        """
        conditions: list[ColumnElement[bool]] = [TenderRecord.publication_date.is_not(None)]
        if self.period.days is not None:
            today = in_moroccan_time(now).date()
            first_day_before = today - timedelta(days=self.period.days)
            conditions.append(TenderRecord.publication_date > first_day_before)
            conditions.append(TenderRecord.publication_date <= today)
        if self.open_only:
            conditions.append(TenderRecord.deadline > now)
        return conditions


@dataclass(frozen=True)
class Coverage:
    """What the period-aware insights are based on.

    Attributes:
        tender_count: Number of tenders counted.
        earliest_publication_date: Earliest publication date among them,
            or None when there are none.
        latest_publication_date: Latest publication date among them, or
            None when there are none.
        without_deadline_count: How many tenders in the period have no
            deadline, whether or not only open tenders are counted: they
            are missing from every deadline-based figure.
    """

    tender_count: int
    earliest_publication_date: date | None
    latest_publication_date: date | None
    without_deadline_count: int


@dataclass(frozen=True)
class NewTender:
    """A tender published in the last 7 days, as listed on the Insights page.

    Attributes:
        id: Database primary key of the tender record.
        reference_number: Reference number of the tender.
        tender_object: Description/object of the tender.
        public_buyer: Name of the public buyer.
        publication_date: Calendar day the tender was published.
        deadline: When bid submissions close (timezone-aware), if known.
    """

    id: int
    reference_number: str | None
    tender_object: str | None
    public_buyer: str | None
    publication_date: date
    deadline: datetime | None


@dataclass(frozen=True)
class ClosingSoonTender:
    """An open tender closing soon, as listed on the Insights page.

    Attributes:
        id: Database primary key of the tender record.
        reference_number: Reference number of the tender.
        tender_object: Description/object of the tender.
        public_buyer: Name of the public buyer.
        deadline: When bid submissions close (timezone-aware).
    """

    id: int
    reference_number: str | None
    tender_object: str | None
    public_buyer: str | None
    deadline: datetime


@dataclass(frozen=True)
class ClosingSoon:
    """Open tenders closing within 14 days, by time left, nearest deadline first.

    Attributes:
        lt3: Less than 3 days left.
        from_3_to_7: At least 3 and less than 7 days left.
        from_7_to_14: At least 7 and at most 14 days left.
    """

    lt3: list[ClosingSoonTender] = field(default_factory=list)
    from_3_to_7: list[ClosingSoonTender] = field(default_factory=list)
    from_7_to_14: list[ClosingSoonTender] = field(default_factory=list)


class Insights(Protocol):
    """Read-only, market-wide answers about discovered tenders."""

    def closing_soon(self, now: datetime) -> ClosingSoon:
        """Return open tenders closing within 14 days of now, by time left.

        Args:
            now: The current time (timezone-aware).
        """

    def coverage(self, now: datetime, insights_filter: InsightsFilter) -> Coverage:
        """Return how many tenders the filter counts, and their date range.

        Args:
            now: The current time (timezone-aware).
            insights_filter: Which tenders to count.
        """

    def new_this_week(self, now: datetime, open_only: bool) -> list[NewTender]:
        """Return tenders published in the last 7 days, newest first.

        Args:
            now: The current time (timezone-aware).
            open_only: Only open tenders.
        """


class PostgresInsights:
    """Insights computed with SQL against tender records."""

    def __init__(self, database: Database) -> None:
        """Initialize the insights with a database instance.

        Args:
            database: Database instance for connection management.
        """
        self._database = database

    def closing_soon(self, now: datetime) -> ClosingSoon:
        """Return open tenders closing within 14 days of now, by time left.

        Args:
            now: The current time (timezone-aware).

        Returns:
            The tenders in their buckets, each nearest deadline first, then by id.

        Raises:
            RepositoryError: if the query fails.
        """
        try:
            with self._database.session() as session:
                stmt = (
                    select(TenderRecord)
                    .where(closing_soon(now))
                    .order_by(TenderRecord.deadline, TenderRecord.id)
                )
                records = session.scalars(stmt).all()
                tenders = [
                    ClosingSoonTender(
                        id=record.id,
                        reference_number=record.reference_number,
                        tender_object=record.tender_object,
                        public_buyer=record.public_buyer,
                        deadline=record.deadline,
                    )
                    for record in records
                ]
        except Exception as exc:
            raise RepositoryError(f"Failed to list tenders closing soon: {exc}") from exc

        # Bucketed here, by instant, so no timezone rules apply in SQL.
        result = ClosingSoon()
        for tender in tenders:
            time_left = tender.deadline - now
            if time_left < _LT3_EDGE:
                result.lt3.append(tender)
            elif time_left < _3TO7_EDGE:
                result.from_3_to_7.append(tender)
            else:
                result.from_7_to_14.append(tender)
        return result

    def coverage(self, now: datetime, insights_filter: InsightsFilter) -> Coverage:
        """Return how many tenders the filter counts, and their date range.

        The range is that of the tenders counted, so it never extends beyond
        the data, whatever the period.

        Args:
            now: The current time (timezone-aware).
            insights_filter: Which tenders to count.

        Returns:
            The count, the range, and how many tenders in the period (open
            or not) have no deadline.

        Raises:
            RepositoryError: if the query fails.
        """
        # A tender without a deadline is never open, so it is counted with
        # "open only" switched off.
        in_period = replace(insights_filter, open_only=False)
        try:
            with self._database.session() as session:
                counted = select(
                    func.count(),
                    func.min(TenderRecord.publication_date),
                    func.max(TenderRecord.publication_date),
                ).where(*insights_filter.conditions(now))
                count, earliest, latest = session.execute(counted).one()
                without_deadline = session.scalar(
                    select(func.count()).where(
                        *in_period.conditions(now), TenderRecord.deadline.is_(None)
                    )
                )
        except Exception as exc:
            raise RepositoryError(f"Failed to compute coverage: {exc}") from exc
        return Coverage(
            tender_count=count,
            earliest_publication_date=earliest,
            latest_publication_date=latest,
            without_deadline_count=without_deadline,
        )

    def new_this_week(self, now: datetime, open_only: bool) -> list[NewTender]:
        """Return tenders published in the last 7 days, newest first.

        Args:
            now: The current time (timezone-aware).
            open_only: Only open tenders.

        Returns:
            The tenders, newest publication first, then newest id first.

        Raises:
            RepositoryError: if the query fails.
        """
        insights_filter = InsightsFilter(period=Period.LAST_7_DAYS, open_only=open_only)
        try:
            with self._database.session() as session:
                stmt = (
                    select(TenderRecord)
                    .where(*insights_filter.conditions(now))
                    .order_by(TenderRecord.publication_date.desc(), TenderRecord.id.desc())
                )
                return [
                    NewTender(
                        id=record.id,
                        reference_number=record.reference_number,
                        tender_object=record.tender_object,
                        public_buyer=record.public_buyer,
                        publication_date=record.publication_date,
                        deadline=record.deadline,
                    )
                    for record in session.scalars(stmt).all()
                ]
        except Exception as exc:
            raise RepositoryError(f"Failed to list new tenders: {exc}") from exc
