"""SQLAlchemy ORM models for the persistence layer."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import ClassVar

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class TenderStatus(str, Enum):
    """Enumeration of possible tender processing statuses.

    Stored as VARCHAR in database for flexibility, validated at application level.
    """

    DISCOVERED = "DISCOVERED"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    CHUNKING = "CHUNKING"
    CHUNKED = "CHUNKED"
    EMBEDDING = "EMBEDDING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


class TenderRecord(Base):
    """ORM model representing a tender record in the database.

    This model mirrors the domain Tender model with additional metadata fields
    for tracking discovery and processing state.

    Attributes:
        id: Primary key.
        tender_id: Tender identifier from the procurement platform.
        organization_acronym: Acronym of the organization.
        procurement_type: Type of procurement procedure.
        category: Category of the tender.
        publication_date: Date when tender was published.
        reference_number: Reference number of the tender.
        tender_object: Description/object of the tender.
        public_buyer: Name of the public buyer.
        location: Location where tender will be executed.
        tender_end_date: Deadline for tender submission.
        status: Current processing status (VARCHAR for flexibility).
        last_status: Last status successfully reached before a failure;
            null unless status is FAILED.
        created_at: Timestamp when record was first created.
        updated_at: Timestamp when record was last updated.
    """

    __tablename__ = "tender_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    tender_id: Mapped[str | None] = mapped_column(String(50), index=True)
    organization_acronym: Mapped[str | None] = mapped_column(String(50), index=True)
    procurement_type: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(100))
    publication_date: Mapped[str | None] = mapped_column(String(20), index=True)
    reference_number: Mapped[str | None] = mapped_column(String(100))
    tender_object: Mapped[str | None] = mapped_column(String)
    public_buyer: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(500))
    tender_end_date: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(
        String(20), default=TenderStatus.DISCOVERED.value, index=True
    )
    last_status: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)

    __table_args__: ClassVar[tuple] = (
        Index("ix_tender_records_tender_id_org_acronym", "tender_id", "organization_acronym", unique=True),
    )


class DceFileRecord(Base):
    """ORM model for a DCE file extracted from a tender's DCE archive.

    Attributes:
        id: Primary key.
        tender_record_id: The tender whose DCE archive contained the file.
        path: Path of the file inside the DCE archive.
        file_type: Lower-case file extension without the dot.
        status: Chunking outcome: "chunked", "skipped" or "failed".
        reason: Why the file was skipped or failed; null when chunked.
        created_at: Timestamp when the record was created.
    """

    __tablename__ = "dce_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    tender_record_id: Mapped[int] = mapped_column(
        ForeignKey("tender_records.id", ondelete="CASCADE"), index=True
    )
    path: Mapped[str] = mapped_column(Text)
    file_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ChunkRecord(Base):
    """ORM model for an embedded chunk of a DCE file.

    The embedding column is declared without a dimension so the dimension
    lives only in the migration (see ADR 0001).

    Attributes:
        id: Primary key.
        dce_file_id: The DCE file the chunk was taken from.
        chunk_index: Position of the chunk within its DCE file.
        text: The chunk's text.
        page_numbers: Pages of the DCE file the chunk spans.
        heading_path: Section headings enclosing the chunk, outermost first.
        embedding_model: Name of the model that produced the embedding.
        embedding: The chunk's embedding vector.
        created_at: Timestamp when the record was created.
    """

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    dce_file_id: Mapped[int] = mapped_column(
        ForeignKey("dce_files.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    page_numbers: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    heading_path: Mapped[list[str]] = mapped_column(ARRAY(Text))
    embedding_model: Mapped[str] = mapped_column(String(200))
    embedding: Mapped[list[float]] = mapped_column(Vector())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__: ClassVar[tuple] = (
        UniqueConstraint("dce_file_id", "chunk_index", name="uq_chunks_dce_file_chunk_index"),
    )
