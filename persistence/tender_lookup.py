"""Read-only lookup over tender records, for tenders that have a DCE archive."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from sqlalchemy import select

from persistence.database import Database
from persistence.exceptions import RepositoryError
from persistence.models import TenderRecord, has_dce_archive


@dataclass(frozen=True)
class TenderSummary:
    """The fields shown for a tender in a list.

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
    deadline: datetime | None


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


class TenderLookup(Protocol):
    """Read-only access to tenders that have a DCE archive."""

    def list_with_dce_archive(self, limit: int, offset: int) -> list[TenderSummary]:
        """Return a page of tenders that have a DCE archive.

        Args:
            limit: Maximum number of tenders to return.
            offset: Number of tenders to skip.

        Returns:
            Tender summaries, newest publication first, then by id.
        """

    def get_with_dce_archive(self, id: int) -> TenderDetail | None:
        """Return one tender by database id, if it has a DCE archive.

        Args:
            id: Database primary key of the tender record.

        Returns:
            The tender's detail, or None if it does not exist or has no DCE archive.
        """


class PostgresTenderLookup:
    """TenderLookup that queries tender records directly."""

    def __init__(self, database: Database) -> None:
        """Initialize the lookup with a database instance.

        Args:
            database: Database instance for connection management.
        """
        self._database = database

    def list_with_dce_archive(self, limit: int, offset: int) -> list[TenderSummary]:
        """Return a page of tenders that have a DCE archive.

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
                    select(TenderRecord)
                    .where(has_dce_archive())
                    .order_by(TenderRecord.publication_date.desc().nulls_last(), TenderRecord.id)
                    .limit(limit)
                    .offset(offset)
                )
                return [
                    TenderSummary(
                        id=record.id,
                        reference_number=record.reference_number,
                        tender_object=record.tender_object,
                        public_buyer=record.public_buyer,
                        deadline=record.deadline,
                    )
                    for record in session.scalars(stmt)
                ]
        except Exception as exc:
            raise RepositoryError(f"Failed to list tenders with a DCE archive: {exc}") from exc

    def get_with_dce_archive(self, id: int) -> TenderDetail | None:
        """Return one tender by database id, if it has a DCE archive.

        Args:
            id: Database primary key of the tender record.

        Returns:
            The tender's detail, or None if it does not exist or has no DCE archive.

        Raises:
            RepositoryError: if the query fails.
        """
        try:
            with self._database.session() as session:
                stmt = select(TenderRecord).where(TenderRecord.id == id, has_dce_archive())
                record = session.scalars(stmt).one_or_none()
                if record is None:
                    return None
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
                )
        except Exception as exc:
            raise RepositoryError(f"Failed to get tender {id} with a DCE archive: {exc}") from exc
