"""Orchestrate indexing of UPLOADED tenders into the vector store."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Protocol

from core.models import Tender
from downloader import dce_archive_name
from indexing.chunker import DoclingChunker
from indexing.embedder import Embedder
from indexing.extractor import extract_archive
from indexing.models import Chunk, DceFile, DceFileStatus, TextChunk
from indexing.vector_store import VectorStore
from persistence.file_storage import DocumentStorage
from persistence.models import TenderStatus

logger = logging.getLogger(__name__)


class IndexingTenderRepository(Protocol):
    """The tender repository operations the pipeline needs."""

    def find_by_status(self, status: TenderStatus, limit: int) -> list[Tender]: ...

    def update_status(
        self,
        tender_id: str,
        organization_acronym: str,
        status: TenderStatus,
        last_status: TenderStatus | None = None,
    ) -> None: ...


class IndexingPipeline:
    """Index UPLOADED tenders: download, extract, chunk, embed, store.

    Each tender moves UPLOADED -> CHUNKING -> CHUNKED -> EMBEDDING -> INDEXED
    and is processed in its own temporary folder, removed afterwards.
    """

    def __init__(
        self,
        repository: IndexingTenderRepository,
        document_storage: DocumentStorage,
        chunker: DoclingChunker,
        embedder: Embedder,
        vector_store: VectorStore,
        work_root: Path | None = None,
    ) -> None:
        """Initialize the pipeline with its collaborators.

        Args:
            repository: Source of UPLOADED tenders and sink for status updates.
            document_storage: Storage the DCE archives are loaded from.
            chunker: Splits a DCE file into chunks.
            embedder: Embeds chunk text.
            vector_store: Persists DCE files and their chunks.
            work_root: Directory per-tender temp folders are created in;
                defaults to the system temp directory.
        """
        self._repository = repository
        self._document_storage = document_storage
        self._chunker = chunker
        self._embedder = embedder
        self._vector_store = vector_store
        self._work_root = work_root

    def run(self, limit: int) -> None:
        """Index the first `limit` UPLOADED tenders."""
        tenders = self._repository.find_by_status(TenderStatus.UPLOADED, limit)
        logger.info("Indexing %d tender(s)", len(tenders))
        for tender in tenders:
            self._index(tender)

    def _index(self, tender: Tender) -> None:
        # Tenders read back from the repository always carry their identity.
        assert tender.tender_id and tender.organization_acronym
        key = (tender.tender_id, tender.organization_acronym)
        archive_name = dce_archive_name(*key)
        logger.info("Indexing tender %s", archive_name)

        self._set_status(key, TenderStatus.CHUNKING)
        with tempfile.TemporaryDirectory(prefix="indexing-", dir=self._work_root) as work_dir:
            archive = self._document_storage.load_document(archive_name)
            chunked_files = [
                (extracted, self._chunker.chunk(extracted.local_path))
                for extracted in extract_archive(archive, Path(work_dir))
            ]
        self._set_status(key, TenderStatus.CHUNKED)

        self._set_status(key, TenderStatus.EMBEDDING)
        dce_files = [
            DceFile(
                path=extracted.archive_path,
                file_type=extracted.file_type,
                status=DceFileStatus.CHUNKED,
                chunks=self._embed(text_chunks),
            )
            for extracted, text_chunks in chunked_files
        ]
        self._vector_store.replace_tender_files(tender, dce_files)
        self._set_status(key, TenderStatus.INDEXED)

    def _embed(self, text_chunks: list[TextChunk]) -> list[Chunk]:
        vectors = self._embedder.embed([chunk.embedding_text for chunk in text_chunks])
        return [
            Chunk(
                index=chunk.index,
                text=chunk.text,
                page_numbers=chunk.page_numbers,
                headings=chunk.headings,
                embedding_model=self._embedder.model_name,
                embedding=vector,
            )
            for chunk, vector in zip(text_chunks, vectors, strict=True)
        ]

    def _set_status(self, key: tuple[str, str], status: TenderStatus) -> None:
        self._repository.update_status(*key, status)
