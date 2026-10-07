"""Test that PgVectorStore replaces a tender's DCE files atomically on a real Postgres database."""

from datetime import UTC, datetime

from sqlalchemy import delete, select

from core.models import Tender
from indexing.models import Chunk, DceFile, DceFileStatus
from indexing.vector_store import PgVectorStore
from persistence import (
    Database,
    RepositoryError,
    Settings,
    TenderRecord,
    TenderRepository,
)
from persistence.models import ChunkRecord, DceFileRecord

from .config import logger

EMBEDDING_MODEL = "integration-test-model"


def _dce_file(path: str, chunk_count: int, dim: int) -> DceFile:
    return DceFile(
        path=path,
        file_type="pdf",
        status=DceFileStatus.CHUNKED,
        chunks=[
            Chunk(
                index=index,
                text=f"{path} chunk {index}",
                page_numbers=(index + 1,),
                headings=("Article 1",),
                embedding_model=EMBEDDING_MODEL,
                embedding=[0.0] * (dim - 1) + [1.0],
            )
            for index in range(chunk_count)
        ],
    )


def _stored_rows(database: Database, tender: Tender) -> list[tuple]:
    """Return the tender's stored (DCE file path, chunk index, chunk text) rows, sorted.

    A DCE file without chunks appears once with None for index and text, so
    duplicated DCE files or chunks show up as repeated rows.
    """
    with database.session() as session:
        rows = session.execute(
            select(DceFileRecord.path, ChunkRecord.chunk_index, ChunkRecord.text)
            .join(TenderRecord, DceFileRecord.tender_record_id == TenderRecord.id)
            .outerjoin(ChunkRecord, ChunkRecord.dce_file_id == DceFileRecord.id)
            .where(
                TenderRecord.tender_id == tender.tender_id,
                TenderRecord.organization_acronym == tender.organization_acronym,
            )
            .order_by(DceFileRecord.path, ChunkRecord.chunk_index)
        ).all()
    return [tuple(row) for row in rows]


def test_vector_store_replace():
    """Test that re-indexing a tender replaces its DCE files and chunks atomically.

    Stores two DCE files for a throwaway tender, stores the same set again
    and checks nothing is duplicated, then attempts a write that fails
    mid-transaction (a chunk whose embedding has the wrong dimension, in the
    second DCE file) and checks the previous set is still there unchanged.

    Raises on any failure instead of swallowing it - callers must not treat
    a caught exception here as a passing run.
    """
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Vector store replace (persists to Postgres)")
    logger.info("=" * 60)

    tender_id = f"REPLACE-TEST-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
    organization_acronym = "REPLACE-TEST-ORG"

    database = None
    try:
        settings = Settings.from_env()
        dim = settings.embedding_dim
        database = Database(settings)
        tender = Tender(tender_id=tender_id, organization_acronym=organization_acronym)
        TenderRepository(database).save(tender)
        store = PgVectorStore(database)
        dce_files = [_dce_file("CPS.pdf", 2, dim), _dce_file("RC.pdf", 3, dim)]
        expected = [
            *(("CPS.pdf", index, f"CPS.pdf chunk {index}") for index in range(2)),
            *(("RC.pdf", index, f"RC.pdf chunk {index}") for index in range(3)),
        ]

        store.replace_tender_files(tender, dce_files)
        after_write = _stored_rows(database, tender)
        store.replace_tender_files(tender, dce_files)
        after_rewrite = _stored_rows(database, tender)
        logger.info(f"Rows after write={len(after_write)}, after re-write={len(after_rewrite)}")
        if after_write != expected or after_rewrite != expected:
            raise AssertionError(
                f"Expected {expected} after each write, got {after_write}, {after_rewrite}"
            )

        # The second DCE file's embedding has the wrong dimension, so the
        # write fails after the old rows were deleted and the first file inserted.
        failing_write = [
            _dce_file("NEW.pdf", 2, dim),
            _dce_file("WRONG-DIM.pdf", 1, dim=dim - 1),
        ]
        try:
            store.replace_tender_files(tender, failing_write)
        except RepositoryError as exc:
            logger.info(f"Broken write rejected as expected: {exc}")
        else:
            raise AssertionError("Write with a wrong-dimension embedding was not rejected")
        after_failure = _stored_rows(database, tender)
        logger.info(f"Rows after failed write={after_failure}")
        if after_failure != expected:
            raise AssertionError(f"Failed write changed stored files: {after_failure}")

        logger.info("Vector store replace verified successfully")
    finally:
        if database is not None:
            # Deleting the tender cascades to its DCE files and chunks.
            with database.session() as session:
                session.execute(
                    delete(TenderRecord).where(
                        TenderRecord.tender_id == tender_id,
                        TenderRecord.organization_acronym == organization_acronym,
                    )
                )
            database.close()
