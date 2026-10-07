"""Orchestrate indexing of uploaded tenders into the vector store."""

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

    def find_for_indexing(self, limit: int) -> list[Tender]: ...

    def update_status(
        self,
        tender_id: str,
        organization_acronym: str,
        status: TenderStatus,
        last_status: TenderStatus | None = None,
    ) -> None: ...


class IndexingPipeline:
    """Index uploaded tenders: download, extract, chunk, embed, store.

    Each tender moves UPLOADED -> CHUNKING -> CHUNKED -> EMBEDDING -> INDEXED
    and is processed in its own temporary folder, removed afterwards. A
    tender-level error (S3, unreadable archive, database) marks that tender
    FAILED with last_status set to the last status it completed, and the
    batch moves on to the next tender. Any error not tied to a single DCE
    file counts as tender-level.
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
            repository: Source of tenders to index and sink for status updates.
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
        """Index the first `limit` tenders that are UPLOADED or failed after upload.

        A retried FAILED tender restarts from the download of its DCE archive.
        """
        tenders = self._repository.find_for_indexing(limit)
        logger.info("Indexing %d tender(s)", len(tenders))
        for tender in tenders:
            self._index_or_fail(tender)

    def _index_or_fail(self, tender: Tender) -> None:
        # Tenders read back from the repository always carry their identity.
        assert tender.tender_id and tender.organization_acronym
        key = (tender.tender_id, tender.organization_acronym)
        archive_name = dce_archive_name(*key)
        logger.info("Indexing tender %s", archive_name)

        # A retry restarts from the download, so it has only completed UPLOADED.
        last_status = TenderStatus.UPLOADED
        try:
            dce_files = self._chunk_tender(key, archive_name)
            last_status = TenderStatus.CHUNKED
            self._embed_and_store(tender, key, dce_files)
        except Exception:
            logger.exception("Tender %s failed after %s", archive_name, last_status.value)
            self._mark_failed(key, archive_name, last_status)

    def _chunk_tender(
        self, key: tuple[str, str], archive_name: str
    ) -> list[tuple[DceFile, list[TextChunk]]]:
        # Moving to CHUNKING clears a retried tender's last_status.
        self._set_status(key, TenderStatus.CHUNKING)
        with tempfile.TemporaryDirectory(prefix="indexing-", dir=self._work_root) as work_dir:
            archive = self._document_storage.load_document(archive_name)
            dce_files = [
                self._chunk(extracted) for extracted in extract_archive(archive, Path(work_dir))
            ]
        self._set_status(key, TenderStatus.CHUNKED)
        return dce_files

    def _embed_and_store(
        self,
        tender: Tender,
        key: tuple[str, str],
        dce_files: list[tuple[DceFile, list[TextChunk]]],
    ) -> None:
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

    def _mark_failed(
        self, key: tuple[str, str], archive_name: str, last_status: TenderStatus
    ) -> None:
        try:
            self._repository.update_status(*key, TenderStatus.FAILED, last_status=last_status)
        except Exception:
            # The database may be the reason the tender failed; leave the
            # tender as it is and carry on with the batch.
            logger.exception("Could not mark tender %s FAILED", archive_name)
