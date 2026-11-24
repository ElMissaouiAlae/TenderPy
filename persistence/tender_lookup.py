"""Read-only lookup over every discovered tender record."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from sqlalchemy import false, func, select

from persistence.database import Database
from persistence.exceptions import RepositoryError
from persistence.models import TenderRecord, has_dce_archive


def _select_with_dce_archive_flag():
    """Select tender records alongside whether each has a DCE archive.

    The rule yields NULL for a FAILED record without a last status (rows from
    before last_status existed); such a record has no DCE archive.
    """
    return select(
        TenderRecord,
        func.coalesce(has_dce_archive(), false()).label("has_dce_archive"),
    )


@dataclass(frozen=True)
class TenderSummary:
    """The fields shown for a tender in a list.

    Attributes:
        id: Database primary key of the tender record.
        reference_number: Reference number of the tender.
        tender_object: Description/object of the tender.
        public_buyer: Name of the public buyer.
        deadline: When bid submissions close (timezone-aware).
        has_dce_archive: Whether the tender's DCE archive is in document storage.
    """

    id: int
    reference_number: str | None
    tender_object: str | None
    public_buyer: str | None
    deadline: datetime | None
    has_dce_archive: bool


@dataclass(frozen=True)
class TenderDetail:
    """The fields shown on a tender's own page.

    Attributes:
        id: Database primary key of the tender record.
        tender_id: Tender identifier on the source platform.
        organization_acronym: Acronym of the organization publishing the tender.
        reference_number: Reference number of the tender.
        tender_object: Description/object of the tender.
        public_buyer: Name of the public buyer.
        location: Location of the tender.
        category: Category of the tender.
        procurement_type: Type of procurement.
        publication_date: Calendar day the tender was published.
        deadline: When bid submissions close (timezone-aware).
        has_dce_archive: Whether the tender's DCE archive is in document storage.
    """

    id: int
    tender_id: str | None
    organization_acronym: str | None
    reference_number: str | None
    tender_object: str | None
    public_buyer: str | None
    location: str | None
    category: str | None
    procurement_type: str | None
    publication_date: date | None
    deadline: datetime | None
    has_dce_archive: bool


class TenderLookup(Protocol):
    """Read-only access to every discovered tender, whatever its status."""

    def list_tenders(self, limit: int, offset: int) -> list[TenderSummary]:
        """Return a page of tenders.

        Args:
            limit: Maximum number of tenders to return.
            offset: Number of tenders to skip.

        Returns:
            Tender summaries, newest publication first, then by id.
        """

    def get_tender(self, id: int) -> TenderDetail | None:
        """Return one tender by database id.

        Args:
            id: Database primary key of the tender record.

        Returns:
            The tender's detail, or None if it does not exist.
        """


class PostgresTenderLookup:
    """TenderLookup that queries tender records directly."""

    def __init__(self, database: Database) -> None:
        """Initialize the lookup with a database instance.

        Args:
            database: Database instance for connection management.
        """
        self._database = database

    def list_tenders(self, limit: int, offset: int) -> list[TenderSummary]:
        """Return a page of tenders, in every status.

        Tenders without a publication date come last.

        Args:
            limit: Maximum number of tenders to return.
            offset: Number of tenders to skip.

        Returns:
            Tender summaries, newest publication first, then by id.

        Raises:
            RepositoryError: if the query fails.
        """
        try:
            with self._database.session() as session:
                stmt = (
                    _select_with_dce_archive_flag()
                    .order_by(TenderRecord.publication_date.desc().nulls_last(), TenderRecord.id)
                    .limit(limit)
                    .offset(offset)
                )
                return [
                    TenderSummary(
                        id=row.TenderRecord.id,
                        reference_number=row.TenderRecord.reference_number,
                        tender_object=row.TenderRecord.tender_object,
                        public_buyer=row.TenderRecord.public_buyer,
                        deadline=row.TenderRecord.deadline,
                        has_dce_archive=row.has_dce_archive,
                    )
                    for row in session.execute(stmt)
                ]
        except Exception as exc:
            raise RepositoryError(f"Failed to list tenders: {exc}") from exc

    def get_tender(self, id: int) -> TenderDetail | None:
        """Return one tender by database id, in any status.

        Args:
            id: Database primary key of the tender record.

        Returns:
            The tender's detail, or None if it does not exist.

        Raises:
            RepositoryError: if the query fails.
        """
        try:
            with self._database.session() as session:
                stmt = _select_with_dce_archive_flag().where(TenderRecord.id == id)
                row = session.execute(stmt).one_or_none()
                if row is None:
                    return None
                record = row.TenderRecord
                return TenderDetail(
                    id=record.id,
                    tender_id=record.tender_id,
                    organization_acronym=record.organization_acronym,
                    reference_number=record.reference_number,
                    tender_object=record.tender_object,
                    public_buyer=record.public_buyer,
                    location=record.location,
                    category=record.category,
                    procurement_type=record.procurement_type,
                    publication_date=record.publication_date,
                    deadline=record.deadline,
                    has_dce_archive=row.has_dce_archive,
                )
        except Exception as exc:
            raise RepositoryError(f"Failed to get tender {id}: {exc}") from exc
