"""Orchestrate indexing of UPLOADED tenders into the vector store."""

from __future__ import annotations

import dataclasses
import logging
import tempfile
from pathlib import Path
from typing import Protocol

from core.models import Tender
from downloader import dce_archive_name
from indexing.chunker import DoclingChunker, UnsupportedFileError
from indexing.embedder import Embedder
from indexing.extractor import ExtractedFile, extract_archive
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
            dce_files = [
                self._chunk(extracted) for extracted in extract_archive(archive, Path(work_dir))
            ]
        self._set_status(key, TenderStatus.CHUNKED)

        self._set_status(key, TenderStatus.EMBEDDING)
        embedded_files = [
            dataclasses.replace(dce_file, chunks=self._embed(text_chunks))
            for dce_file, text_chunks in dce_files
        ]
        self._vector_store.replace_tender_files(tender, embedded_files)
        self._set_status(key, TenderStatus.INDEXED)

    def _chunk(self, extracted: ExtractedFile) -> tuple[DceFile, list[TextChunk]]:
        """Chunk one DCE file, recording rather than raising per-file errors.

        Returns:
            The DCE file without chunks, and its text chunks (empty unless
            the file was chunked).
        """
        if extracted.local_path is None:
            status, reason = DceFileStatus.FAILED, extracted.extraction_error
            text_chunks = []
        else:
            try:
                text_chunks = self._chunker.chunk(extracted.local_path)
                status, reason = DceFileStatus.CHUNKED, None
            except UnsupportedFileError as exc:
                status, reason, text_chunks = DceFileStatus.SKIPPED, str(exc), []
            except Exception as exc:
                # A single bad DCE file must never fail the tender.
                status, reason = DceFileStatus.FAILED, f"{type(exc).__name__}: {exc}"
                text_chunks = []
        if reason is not None:
            logger.warning("%s %s: %s", status.value.capitalize(), extracted.archive_path, reason)
        dce_file = DceFile(
            path=extracted.archive_path,
            file_type=extracted.file_type,
            status=status,
            reason=reason,
        )
        return dce_file, text_chunks

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
