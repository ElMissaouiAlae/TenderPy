"""Store DCE files and embedded chunks, and search them by similarity."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import delete, select

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
        self, query_embedding: Sequence[float], embedding_model: str, limit: int = 10
    ) -> list[SearchHit]:
        """Return the chunks nearest to query_embedding by cosine distance.

        Only chunks embedded with embedding_model are considered, so vectors
        from different models are never compared.
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
        self, query_embedding: Sequence[float], embedding_model: str, limit: int = 10
    ) -> list[SearchHit]:
        """Return the chunks nearest to query_embedding by cosine distance.

        Args:
            query_embedding: Vector to search with.
            embedding_model: Only chunks embedded with this model are compared.
            limit: Maximum number of hits.

        Returns:
            Hits ordered nearest first.

        Raises:
            RepositoryError: if the query fails.
        """
        distance = ChunkRecord.embedding.cosine_distance(list(query_embedding))
        stmt = (
            select(
                TenderRecord.tender_id,
                TenderRecord.organization_acronym,
                DceFileRecord.path,
                ChunkRecord.chunk_index,
                ChunkRecord.text,
                ChunkRecord.page_numbers,
                ChunkRecord.heading_path,
                distance.label("distance"),
            )
            .join(DceFileRecord, ChunkRecord.dce_file_id == DceFileRecord.id)
            .join(TenderRecord, DceFileRecord.tender_record_id == TenderRecord.id)
            .where(ChunkRecord.embedding_model == embedding_model)
            .order_by(distance)
            .limit(limit)
        )
        try:
            with self._database.session() as session:
                rows = session.execute(stmt).all()
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
