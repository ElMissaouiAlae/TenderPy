"""Read-only aggregate questions over tender records, for the Insights page.

Every query takes "now" as a parameter and never reads the clock itself, so
results are deterministic for a given time.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from enum import Enum
from statistics import median
from typing import Protocol

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import InstrumentedAttribute

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


class TopDimension(str, Enum):
    """What tenders can be counted by on the Insights page."""

    PUBLIC_BUYER = "public_buyer"
    CATEGORY = "category"
    LOCATION = "location"




class ResponseWindowDimension(str, Enum):
    """What median response windows can be grouped by."""

    CATEGORY = "category"
    PUBLIC_BUYER = "public_buyer"


# The column each dimension groups by, keyed by the dimensions' shared values.
_DIMENSION_COLUMNS: dict[str, InstrumentedAttribute[str | None]] = {
    "public_buyer": TenderRecord.public_buyer,
    "category": TenderRecord.category,
    "location": TenderRecord.location,
}


def _spelling(column: ColumnElement[str | None]) -> ColumnElement[str | None]:
    """SQL: the value trimmed, with every run of whitespace made one space."""
    return func.btrim(func.regexp_replace(column, r"\s+", " ", "g"))


def _group_key(column: ColumnElement[str | None]) -> ColumnElement[str | None]:
    """SQL: the value as grouped, so names that differ only in case or spacing match."""
    return func.lower(_spelling(column))


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
class TopValue:
    """One value of a dimension and how many tenders have it.

    Attributes:
        label: The value's most frequent spelling (trimmed, single-spaced).
        tender_count: Number of tenders with the value, whatever its case
            or spacing.
    """

    label: str
    tender_count: int


@dataclass(frozen=True)
class ResponseWindowGroup:
    """The median response window of one category or public buyer.

    Attributes:
        label: The group's most frequent spelling (trimmed, single-spaced).
        median_days: Median response window in days. Windows are whole
            days; the median of an even-sized group may end in .5.
        tender_count: Number of tenders with a response window in the group.
    """

    label: str
    median_days: float
    tender_count: int


@dataclass(frozen=True)
class ShortResponseWindow:
    """A tender whose response window is under half its category's median.

    Attributes:
        id: Database primary key of the tender record.
        reference_number: Reference number of the tender.
        tender_object: Description/object of the tender.
        public_buyer: Name of the public buyer.
        category: Category of the tender.
        response_window_days: Days from publication date to deadline date.
        category_median_days: Median response window of the tender's
            category over the same tenders.
    """

    id: int
    reference_number: str | None
    tender_object: str | None
    public_buyer: str | None
    category: str
    response_window_days: int
    category_median_days: float


@dataclass(frozen=True)
class ResponseWindows:
    """Median response windows per group, and the short response windows.

    Attributes:
        groups: One per category or public buyer, most tenders first.
        short_response_windows: Tenders under half their category's
            median, shortest window first.
    """

    groups: list[ResponseWindowGroup]
    short_response_windows: list[ShortResponseWindow]


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

    def top(
        self, now: datetime, insights_filter: InsightsFilter, dimension: TopDimension, limit: int
    ) -> list[TopValue]:
        """Return the values of a dimension with the most tenders, most first.

        Args:
            now: The current time (timezone-aware).
            insights_filter: Which tenders to count.
            dimension: What to count tenders by.
            limit: Maximum number of values returned.
        """

    def response_windows(
        self, now: datetime, insights_filter: InsightsFilter, dimension: ResponseWindowDimension
    ) -> ResponseWindows:
        """Return median response windows per group, and the short ones.

        Args:
            now: The current time (timezone-aware).
            insights_filter: Which tenders to count.
            dimension: What to group the medians by.
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

    def top(
        self, now: datetime, insights_filter: InsightsFilter, dimension: TopDimension, limit: int
    ) -> list[TopValue]:
        """Return the values of a dimension with the most tenders, most first.

        Values that differ only in case or spacing are counted together,
        under their most frequent spelling. Tenders with no value (missing
        or blank) are left out.

        Args:
            now: The current time (timezone-aware).
            insights_filter: Which tenders to count.
            dimension: What to count tenders by.
            limit: Maximum number of values returned.

        Returns:
            The values, most tenders first, ties by label.

        Raises:
            RepositoryError: if the query fails.
        """
        column = _DIMENSION_COLUMNS[dimension.value]
        key = _group_key(column).label("key")
        spelling = _spelling(column).label("spelling")
        # Tender count per spelling, within each group.
        spellings = (
            select(key, spelling, func.count().label("spelling_count"))
            .where(*insights_filter.conditions(now), key != "")
            .group_by(key, spelling)
            .subquery()
        )
        ranked = select(
            spellings.c.spelling,
            func.sum(spellings.c.spelling_count)
            .over(partition_by=spellings.c.key)
            .label("tender_count"),
            func.row_number()
            .over(
                partition_by=spellings.c.key,
                order_by=(spellings.c.spelling_count.desc(), spellings.c.spelling),
            )
            .label("rank"),
        ).subquery()
        stmt = (
            select(ranked.c.spelling, ranked.c.tender_count)
            .where(ranked.c.rank == 1)
            .order_by(ranked.c.tender_count.desc(), ranked.c.spelling)
            .limit(limit)
        )
        try:
            with self._database.session() as session:
                rows = session.execute(stmt).all()
        except Exception as exc:
            raise RepositoryError(f"Failed to count tenders by {dimension.value}: {exc}") from exc
        return [TopValue(label=label, tender_count=int(count)) for label, count in rows]

    def response_windows(
        self, now: datetime, insights_filter: InsightsFilter, dimension: ResponseWindowDimension
    ) -> ResponseWindows:
        """Return median response windows per group, and the short ones.

        A response window is the deadline's date (in Moroccan local time)
        minus the publication date, in days. Tenders without a deadline
        have none and are left out. Groups merge names that differ only in
        case or spacing, like top(). A window is short when it is under
        half the median of its category over the same tenders, whatever
        the dimension; tenders with no category are never short.

        Args:
            now: The current time (timezone-aware).
            insights_filter: Which tenders to count.
            dimension: What to group the medians by.

        Returns:
            The groups, most tenders first then by label, and the short
            response windows, shortest first then by id.

        Raises:
            RepositoryError: if the query fails.
        """
        group_column = _DIMENSION_COLUMNS[dimension.value]
        stmt = select(
            TenderRecord.id,
            TenderRecord.reference_number,
            TenderRecord.tender_object,
            TenderRecord.public_buyer,
            TenderRecord.category,
            TenderRecord.publication_date,
            TenderRecord.deadline,
            _group_key(group_column).label("group_key"),
            _spelling(group_column).label("group_spelling"),
            _group_key(TenderRecord.category).label("category_key"),
            _spelling(TenderRecord.category).label("category_spelling"),
        ).where(*insights_filter.conditions(now), TenderRecord.deadline.is_not(None))
        try:
            with self._database.session() as session:
                rows = session.execute(stmt).all()
        except Exception as exc:
            raise RepositoryError(f"Failed to compute response windows: {exc}") from exc

        # Computed here, not in SQL, so the deadline's Moroccan date doesn't
        # depend on the database's timezone rules.
        windowed = [
            (row, (in_moroccan_time(row.deadline).date() - row.publication_date).days)
            for row in rows
        ]
        groups = _medians((row.group_key, row.group_spelling, window) for row, window in windowed)
        category_medians = {
            key: group_median
            for key, (_, group_median, _) in _median_by_key(
                (row.category_key, row.category_spelling, window) for row, window in windowed
            ).items()
        }

        short = [
            ShortResponseWindow(
                id=row.id,
                reference_number=row.reference_number,
                tender_object=row.tender_object,
                public_buyer=row.public_buyer,
                category=row.category,
                response_window_days=window,
                category_median_days=category_medians[row.category_key],
            )
            for row, window in windowed
            if row.category_key and window < category_medians[row.category_key] / 2
        ]
        short.sort(key=lambda tender: (tender.response_window_days, tender.id))
        return ResponseWindows(groups=groups, short_response_windows=short)


def _median_by_key(
    values: Iterable[tuple[str | None, str | None, int]],
) -> dict[str, tuple[str, float, int]]:
    """Group (key, spelling, window) by key: label, median window and count.

    Blank or missing keys are left out. The label is the most frequent
    spelling, ties by spelling.
    """
    windows: dict[str, list[int]] = defaultdict(list)
    spellings: dict[str, Counter[str]] = defaultdict(Counter)
    for key, spelling, window in values:
        if not key:
            continue
        windows[key].append(window)
        spellings[key][spelling] += 1
    return {
        key: (
            min(spellings[key].items(), key=lambda item: (-item[1], item[0]))[0],
            float(median(key_windows)),
            len(key_windows),
        )
        for key, key_windows in windows.items()
    }


def _medians(values: Iterable[tuple[str | None, str | None, int]]) -> list[ResponseWindowGroup]:
    """Median response window per group, most tenders first, then by label."""
    groups = [
        ResponseWindowGroup(label=label, median_days=group_median, tender_count=count)
        for label, group_median, count in _median_by_key(values).values()
    ]
    groups.sort(key=lambda group: (-group.tender_count, group.label))
    return groups
