"""Read-only aggregate questions over tender records, for the Insights page.

Every query takes "now" as a parameter and never reads the clock itself, so
results are deterministic for a given time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy import select

from persistence.database import Database
from persistence.exceptions import RepositoryError
from persistence.models import TenderRecord, closing_soon

# Closing-soon bucket edges: less than 3 days left, then less than 7, then
# the rest of the 14-day window.
_LT3_EDGE = timedelta(days=3)
_3TO7_EDGE = timedelta(days=7)


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
