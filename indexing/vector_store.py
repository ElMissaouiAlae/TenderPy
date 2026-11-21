"""Store DCE files and embedded chunks, and search them by similarity."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import Select, delete, select
from sqlalchemy.orm import Session

from core.models import Tender
from indexing.models import DceFile, SearchHit
from persistence.database import Database
from persistence.exceptions import RecordNotFoundError, RepositoryError
from persistence.models import ChunkRecord, DceFileRecord, TenderRecord


class VectorStore(Protocol):
    """Persistence for DCE files and their embedded chunks."""

    def replace_tender_files(self, tender: Tender, dce_files: Sequence[DceFile]) -> None:
        """Replace all DCE files and chunks of a tender in one transaction."""
        ...

    def search(
        self,
        query_embedding: Sequence[float],
        embedding_model: str,
        limit: int = 10,
        tender: Tender | None = None,
    ) -> list[SearchHit]:
        """Return the chunks nearest to query_embedding by cosine distance.

        Only chunks embedded with embedding_model are considered, so vectors
        from different models are never compared. When tender is given, only
        that tender's chunks are searched, exactly.
        """
        ...


class PgVectorStore:
    """VectorStore on Postgres with the pgvector extension."""

    def __init__(self, database: Database) -> None:
        """Initialize the store with a database instance.

        Args:
            database: Database instance for connection management.
        """
        self._database = database

    def replace_tender_files(self, tender: Tender, dce_files: Sequence[DceFile]) -> None:
        """Replace all DCE files and chunks of a tender in one transaction.

        Existing DCE files of the tender are deleted (cascading to their
        chunks) and the new set inserted; on any error nothing changes.

        Args:
            tender: The tender the DCE files belong to.
            dce_files: The tender's complete set of DCE files, with chunks.

        Raises:
            RecordNotFoundError: if no tender matches the given identity.
            RepositoryError: if the write fails.
        """
        try:
            self._replace_tender_files(tender, dce_files)
        except RecordNotFoundError:
            raise
        except Exception as exc:
            raise RepositoryError(f"Failed to store DCE files: {exc}") from exc

    def _replace_tender_files(self, tender: Tender, dce_files: Sequence[DceFile]) -> None:
        with self._database.session() as session:
            tender_record_id = _tender_record_id(session, tender)

            session.execute(
                delete(DceFileRecord).where(DceFileRecord.tender_record_id == tender_record_id)
            )
            for dce_file in dce_files:
                file_record = DceFileRecord(
                    tender_record_id=tender_record_id,
                    path=dce_file.path,
                    file_type=dce_file.file_type,
                    status=dce_file.status.value,
                    reason=dce_file.reason,
                )
                session.add(file_record)
                session.flush()
                session.add_all(
                    ChunkRecord(
                        dce_file_id=file_record.id,
                        chunk_index=chunk.index,
                        text=chunk.text,
                        page_numbers=list(chunk.page_numbers),
                        heading_path=list(chunk.headings),
                        embedding_model=chunk.embedding_model,
                        embedding=chunk.embedding,
                    )
                    for chunk in dce_file.chunks
                )

    def search(
        self,
        query_embedding: Sequence[float],
        embedding_model: str,
        limit: int = 10,
        tender: Tender | None = None,
    ) -> list[SearchHit]:
        """Return the chunks nearest to query_embedding by cosine distance.

        Without a tender, every tender's chunks are searched through the HNSW
        index (approximate). With a tender, only its chunks are searched, by
        an exact scan: filtering an approximate index scan afterwards would
        drop most of one tender's chunks once the store holds many tenders.

        Args:
            query_embedding: Vector to search with.
            embedding_model: Only chunks embedded with this model are compared.
            limit: Maximum number of hits.
            tender: When given, only this tender's chunks are searched.

        Returns:
            Hits ordered nearest first.

        Raises:
            RecordNotFoundError: if tender is given and does not exist.
            RepositoryError: if the query fails.
        """
        try:
            with self._database.session() as session:
                tender_record_id = None if tender is None else _tender_record_id(session, tender)
                stmt = _search_statement(query_embedding, embedding_model, limit, tender_record_id)
                rows = session.execute(stmt).all()
        except RecordNotFoundError:
            raise
        except Exception as exc:
            raise RepositoryError(f"Failed to search chunks: {exc}") from exc
        return [
            SearchHit(
                tender_id=row.tender_id,
                organization_acronym=row.organization_acronym,
                dce_file_path=row.path,
                chunk_index=row.chunk_index,
                text=row.text,
                page_numbers=tuple(row.page_numbers),
                headings=tuple(row.heading_path),
                distance=row.distance,
            )
            for row in rows
        ]


def _tender_record_id(session: Session, tender: Tender) -> int:
    """Return the id of the tender's record.

    Raises:
        RecordNotFoundError: if no tender matches the given identity.
    """
    tender_record_id = session.scalar(
        select(TenderRecord.id).where(
            TenderRecord.tender_id == tender.tender_id,
            TenderRecord.organization_acronym == tender.organization_acronym,
        )
    )
    if tender_record_id is None:
        raise RecordNotFoundError(
            f"No tender found for tender_id={tender.tender_id!r}, "
            f"organization_acronym={tender.organization_acronym!r}"
        )
    return tender_record_id


def _search_statement(
    query_embedding: Sequence[float],
    embedding_model: str,
    limit: int,
    tender_record_id: int | None,
) -> Select:
    """Build the nearest-chunks query, scoped to one tender record when given."""
    distance = ChunkRecord.embedding.cosine_distance(list(query_embedding))
    chunks = select(
        ChunkRecord.dce_file_id,
        ChunkRecord.chunk_index,
        ChunkRecord.text,
        ChunkRecord.page_numbers,
        ChunkRecord.heading_path,
        distance.label("distance"),
    ).where(ChunkRecord.embedding_model == embedding_model)
    if tender_record_id is None:
        # Ordering by the distance expression lets Postgres use the HNSW index.
        nearest = chunks.order_by(distance).limit(limit).subquery("nearest")
    else:
        # The HNSW index cannot be read through a materialized CTE, so the
        # tender's chunks are always scanned and sorted exactly.
        nearest = (
            chunks.join(DceFileRecord, ChunkRecord.dce_file_id == DceFileRecord.id)
            .where(DceFileRecord.tender_record_id == tender_record_id)
            .cte("nearest")
            .prefix_with("MATERIALIZED")
        )
    return (
        select(
            TenderRecord.tender_id,
            TenderRecord.organization_acronym,
            DceFileRecord.path,
            nearest.c.chunk_index,
            nearest.c.text,
            nearest.c.page_numbers,
            nearest.c.heading_path,
            nearest.c.distance,
        )
        .join(DceFileRecord, nearest.c.dce_file_id == DceFileRecord.id)
        .join(TenderRecord, DceFileRecord.tender_record_id == TenderRecord.id)
        .order_by(nearest.c.distance)
        .limit(limit)
    )
