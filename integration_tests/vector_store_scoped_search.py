"""Test PgVectorStore.search scoped to one tender on a real Postgres database."""

import math
from datetime import UTC, datetime

from sqlalchemy import delete, event

from core.models import Tender
from indexing.models import Chunk, DceFile, DceFileStatus, SearchHit
from indexing.vector_store import PgVectorStore
from persistence import (
    Database,
    RecordNotFoundError,
    Settings,
    TenderRecord,
    TenderRepository,
)

from .config import logger

EMBEDDING_MODEL = "integration-test-scoped-search-model"
DECOY_CHUNKS = 60


def _vector(dim: int, weights: dict[int, float]) -> list[float]:
    """Unit vector with the given weights on the given axes."""
    norm = math.sqrt(sum(weight * weight for weight in weights.values()))
    vector = [0.0] * dim
    for axis, weight in weights.items():
        vector[axis] = weight / norm
    return vector


def _dce_file(path: str, embeddings: list[list[float]]) -> DceFile:
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
                embedding=embedding,
            )
            for index, embedding in enumerate(embeddings)
        ],
    )


def _prefer_index_ordered_scans(database: Database) -> None:
    """Make the planner favour the HNSW index over sorting, as it does on a large store.

    On a small store Postgres sorts a sequential scan and the HNSW index is
    never used, which would hide approximate-search post-filtering.
    """

    @event.listens_for(database.engine, "connect")
    def _disable_sort(dbapi_connection, connection_record):
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET enable_sort = off")


def _hit_keys(hits: list[SearchHit]) -> list[tuple[str, int]]:
    return [(hit.tender_id, hit.chunk_index) for hit in hits]


def test_vector_store_scoped_search():
    """Check a search scoped to one tender returns that tender's nearest chunks.

    Stores a target tender with 4 chunks, a decoy tender with many chunks all
    nearer the query than any of the target's, and a tender with no chunks.
    An approximate index search filtered afterwards would only see decoy
    chunks, so this verifies scoped searches are exact. Also checks the
    unscoped search, an unknown tender and a tender without chunks.

    Raises on any failure instead of swallowing it - callers must not treat
    a caught exception here as a passing run.
    """
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Vector store scoped search (persists to Postgres)")
    logger.info("=" * 60)

    run_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    organization_acronym = "SCOPED-TEST-ORG"
    target = Tender(tender_id=f"SCOPED-TARGET-{run_id}", organization_acronym=organization_acronym)
    decoy = Tender(tender_id=f"SCOPED-DECOY-{run_id}", organization_acronym=organization_acronym)
    empty = Tender(tender_id=f"SCOPED-EMPTY-{run_id}", organization_acronym=organization_acronym)

    database = None
    try:
        settings = Settings.from_env()
        database = Database(settings)
        _prefer_index_ordered_scans(database)
        dim = settings.embedding_dim
        query = _vector(dim, {0: 1.0})

        repository = TenderRepository(database)
        for tender in (target, decoy, empty):
            repository.save(tender)
        store = PgVectorStore(database)
        # Target chunks lean further from the query as their index grows.
        store.replace_tender_files(
            target,
            [_dce_file("CPS.pdf", [_vector(dim, {0: 1.0, 1 + i: i + 1.0}) for i in range(4)])],
        )
        # Every decoy chunk is nearer the query than any target chunk.
        store.replace_tender_files(
            decoy,
            [
                _dce_file(
                    "RC.pdf",
                    [_vector(dim, {0: 1.0, 10 + i: 0.01 * (i + 1)}) for i in range(DECOY_CHUNKS)],
                )
            ],
        )

        scoped = store.search(query, EMBEDDING_MODEL, limit=3, tender=target)
        logger.info(f"Scoped hits: {_hit_keys(scoped)}")
        if _hit_keys(scoped) != [
            (target.tender_id, 0),
            (target.tender_id, 1),
            (target.tender_id, 2),
        ]:
            raise AssertionError(f"Expected target chunks 0, 1, 2 nearest first, got {scoped}")

        unscoped = store.search(query, EMBEDDING_MODEL, limit=3)
        logger.info(f"Unscoped hits: {_hit_keys(unscoped)}")
        if _hit_keys(unscoped) != [
            (decoy.tender_id, 0),
            (decoy.tender_id, 1),
            (decoy.tender_id, 2),
        ]:
            raise AssertionError(f"Expected decoy chunks 0, 1, 2 nearest first, got {unscoped}")

        if store.search(query, EMBEDDING_MODEL, limit=3, tender=empty) != []:
            raise AssertionError("Expected no hits for a tender without chunks")

        missing = Tender(tender_id=f"SCOPED-MISSING-{run_id}", organization_acronym=organization_acronym)
        try:
            store.search(query, EMBEDDING_MODEL, limit=3, tender=missing)
        except RecordNotFoundError:
            pass
        else:
            raise AssertionError("Expected RecordNotFoundError for an unknown tender")

        logger.info("Vector store scoped search verified successfully")
    finally:
        if database is not None:
            # Deleting the tenders cascades to their DCE files and chunks.
            with database.session() as session:
                session.execute(
                    delete(TenderRecord).where(
                        TenderRecord.organization_acronym == organization_acronym,
                        TenderRecord.tender_id.in_(
                            [target.tender_id, decoy.tender_id, empty.tender_id]
                        ),
                    )
                )
            database.close()


if __name__ == "__main__":
    test_vector_store_scoped_search()
