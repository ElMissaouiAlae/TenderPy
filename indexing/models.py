"""Domain models produced and persisted by the indexing pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DceFileStatus(str, Enum):
    """Outcome of chunking a single DCE file."""

    CHUNKED = "chunked"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class TextChunk:
    """A chunk of a DCE file's text, before embedding.

    Attributes:
        index: Position of the chunk within its DCE file, starting at 0.
        text: The chunk's text as stored and cited.
        embedding_text: The text fed to the embedder (chunk text prefixed
            with its headings, so the vector carries the section context).
        page_numbers: Pages of the DCE file the chunk was taken from.
        headings: Section headings enclosing the chunk, outermost first.
    """

    index: int
    text: str
    embedding_text: str
    page_numbers: tuple[int, ...]
    headings: tuple[str, ...]


@dataclass(frozen=True)
class Chunk:
    """An embedded chunk, ready to be persisted and cited.

    Attributes:
        index: Position of the chunk within its DCE file, starting at 0.
        text: The chunk's text.
        page_numbers: Pages of the DCE file the chunk was taken from.
        headings: Section headings enclosing the chunk, outermost first.
        embedding_model: Name of the model that produced the embedding.
        embedding: The chunk's embedding vector.
    """

    index: int
    text: str
    page_numbers: tuple[int, ...]
    headings: tuple[str, ...]
    embedding_model: str
    embedding: list[float]


@dataclass(frozen=True)
class DceFile:
    """A DCE file extracted from a tender's DCE archive, with its chunks.

    Attributes:
        path: Path of the file inside the DCE archive.
        file_type: Lower-case file extension without the dot (e.g. "pdf").
        status: Outcome of chunking the file.
        reason: Why the file was skipped or failed; None when chunked.
        chunks: Embedded chunks; empty unless status is CHUNKED.
    """

    path: str
    file_type: str
    status: DceFileStatus
    reason: str | None = None
    chunks: list[Chunk] = field(default_factory=list)


@dataclass(frozen=True)
class SearchHit:
    """A chunk returned by a similarity search, with its citation.

    Attributes:
        tender_id: Tender the chunk belongs to.
        organization_acronym: Organization owning the tender.
        dce_file_path: Path of the chunk's DCE file inside the DCE archive.
        chunk_index: Position of the chunk within its DCE file.
        text: The chunk's text.
        page_numbers: Pages of the DCE file the chunk was taken from.
        headings: Section headings enclosing the chunk, outermost first.
        distance: Cosine distance from the query (0 = identical direction).
    """

    tender_id: str
    organization_acronym: str
    dce_file_path: str
    chunk_index: int
    text: str
    page_numbers: tuple[int, ...]
    headings: tuple[str, ...]
    distance: float
