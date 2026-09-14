"""Repository implementation for tender persistence operations."""

from __future__ import annotations

from typing import List

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from core.models import Tender
from persistence.database import Database
from persistence.exceptions import RecordNotFoundError, RepositoryError
from persistence.mapper import to_domain, to_record
from persistence.models import TenderRecord, TenderStatus


class TenderRepository:
    """Repository for managing tender persistence operations.

    This class implements the Repository Pattern, hiding all database
    implementation details from the rest of the application. It accepts
    and returns domain Tender objects only.

    Attributes:
        database: Database instance for connection management.
    """

    def __init__(self, database: Database) -> None:
        """Initialize the repository with a database instance.

        Args:
            database: Database instance for connection management.
        """
        self._database = database

    def save(self, tender: Tender) -> None:
        """Save a single tender to the database.

        Performs an upsert operation: if the tender already exists
        (identified by tender_id and organization_acronym), it updates
        the tender_object, public_buyer, publication_date, and updated_at.
        Otherwise, it inserts a new record.

        Args:
            tender: Domain Tender object to persist.

        Raises:
            RepositoryError: if the save operation fails.
        """
        tender.validate()
        try:
            with self._database.session() as session:
                record = to_record(tender)

                stmt = (
                    insert(TenderRecord)
                    .values(
                        tender_id=record.tender_id,
                        organization_acronym=record.organization_acronym,
                        procurement_type=record.procurement_type,
                        category=record.category,
                        publication_date=record.publication_date,
                        reference_number=record.reference_number,
                        tender_object=record.tender_object,
                        public_buyer=record.public_buyer,
                        location=record.location,
                        tender_end_date=record.tender_end_date,
                        status=record.status,
                    )
                    .on_conflict_do_update(
                        index_elements=["tender_id", "organization_acronym"],
                        set_=dict(
                            tender_object=record.tender_object,
                            public_buyer=record.public_buyer,
                            publication_date=record.publication_date,
                            updated_at=func.now(),
                        ),
                    )
                )

                session.execute(stmt)
        except Exception as exc:
            raise RepositoryError(f"Failed to save tender: {exc}") from exc

    def save_many(self, tenders: List[Tender]) -> None:
        """Save multiple tenders to the database in a single transaction.

        Uses PostgreSQL INSERT ... ON CONFLICT for efficient bulk upserts.
        If a tender already exists (identified by tender_id and organization_acronym),
        it updates the tender_object, public_buyer, publication_date, and updated_at.

        Args:
            tenders: List of domain Tender objects to persist.

        Raises:
            RepositoryError: if the bulk save operation fails.
        """
        if not tenders:
            return

        for tender in tenders:
            tender.validate()

        try:
            with self._database.session() as session:
                # ON CONFLICT DO UPDATE can't hit the same key twice in one statement.
                # Dedupe by (tender_id, organization_acronym); last occurrence wins.
                deduped: dict[tuple[str, str], Tender] = {}
                for tender in tenders:
                    deduped[(tender.tender_id, tender.organization_acronym)] = tender

                records = [to_record(tender) for tender in deduped.values()]

                insert_stmt = insert(TenderRecord).values(
                    [
                        dict(
                            tender_id=record.tender_id,
                            organization_acronym=record.organization_acronym,
                            procurement_type=record.procurement_type,
                            category=record.category,
                            publication_date=record.publication_date,
                            reference_number=record.reference_number,
                            tender_object=record.tender_object,
                            public_buyer=record.public_buyer,
                            location=record.location,
                            tender_end_date=record.tender_end_date,
                            status=record.status,
                        )
                        for record in records
                    ]
                )

                stmt = insert_stmt.on_conflict_do_update(
                    index_elements=["tender_id", "organization_acronym"],
                    set_=dict(
                        tender_object=insert_stmt.excluded.tender_object,
                        public_buyer=insert_stmt.excluded.public_buyer,
                        publication_date=insert_stmt.excluded.publication_date,
                        updated_at=func.now(),
                    ),
                )

                session.execute(stmt)
        except Exception as exc:
            raise RepositoryError(f"Failed to save tenders: {exc}") from exc

    def update_status(
        self,
        tender_id: str,
        organization_acronym: str,
        status: TenderStatus,
        last_status: TenderStatus | None = None,
    ) -> None:
        """Update a tender's status after its initial insert.

        On a failure transition (`status=TenderStatus.FAILED`), pass the
        last status the tender successfully reached as `last_status`. On any
        successful transition, omit `last_status` (or pass None) to clear it
        back to null.

        Args:
            tender_id: Tender identifier.
            organization_acronym: Organization acronym.
            status: New status to set.
            last_status: Last successfully reached status, recorded only on
                a failure transition. Defaults to None, clearing the column.

        Raises:
            ValueError: if `last_status` is given for a non-FAILED status.
            RecordNotFoundError: if no tender matches the given identity.
            RepositoryError: if the update operation fails.
        """
        if status == TenderStatus.FAILED and (
            last_status is None or last_status == TenderStatus.FAILED
        ):
            raise ValueError("FAILED status requires a non-FAILED last_status")
        if last_status is not None and status != TenderStatus.FAILED:
            raise ValueError(
                f"last_status is only meaningful when status=FAILED, got status={status!r}"
            )
        try:
            with self._database.session() as session:
                stmt = (
                    update(TenderRecord)
                    .where(
                        TenderRecord.tender_id == tender_id,
                        TenderRecord.organization_acronym == organization_acronym,
                    )
                    .values(
                        status=status.value,
                        last_status=last_status.value if last_status is not None else None,
                        updated_at=func.now(),
                    )
                )
                result = session.execute(stmt)
                if result.rowcount == 0:
                    raise RecordNotFoundError(
                        f"No tender found for tender_id={tender_id!r}, "
                        f"organization_acronym={organization_acronym!r}"
                    )
        except RecordNotFoundError:
            raise
        except Exception as exc:
            raise RepositoryError(f"Failed to update tender status: {exc}") from exc

    def exists(self, tender_id: str, organization_acronym: str) -> bool:
        """Check if a tender exists in the database.

        Args:
            tender_id: Tender identifier.
            organization_acronym: Organization acronym.

        Returns:
            True if the tender exists, False otherwise.

        Raises:
            RepositoryError: if the query fails.
        """
        try:
            with self._database.session() as session:
                stmt = select(TenderRecord).where(
                    TenderRecord.tender_id == tender_id,
                    TenderRecord.organization_acronym == organization_acronym,
                )
                result = session.execute(stmt).first()
                return result is not None
        except Exception as exc:
            raise RepositoryError(f"Failed to check tender existence: {exc}") from exc
