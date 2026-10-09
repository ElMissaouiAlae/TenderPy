"""Test the pgvector schema and PgVectorStore against a real Postgres database."""

from datetime import UTC, datetime

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import delete, text

from core.models import Tender
from indexing.models import Chunk, DceFile, DceFileStatus
from indexing.vector_store import PgVectorStore
from persistence import Database, Settings, TenderRecord, TenderRepository

from .config import logger

EMBEDDING_MODEL = "integration-test-model"


def _unit_vector(dim: int, hot: int) -> list[float]:
    vector = [0.0] * dim
    vector[hot] = 1.0
    return vector


def test_vector_store_roundtrip():
    """Check the migration is applied and chunks round-trip through cosine search.

    Verifies the database is at the Alembic head revision with the `vector`
    extension installed, stores a DCE file with three chunks for a throwaway
    tender, and checks a cosine search returns the nearest chunk first with
    its citation metadata.

    Raises on any failure instead of swallowing it - callers must not treat
    a caught exception here as a passing run.
    """
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Vector store round-trip (persists to Postgres)")
    logger.info("=" * 60)

    tender_id = f"VECTOR-TEST-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"
    organization_acronym = "VECTOR-TEST-ORG"

    database = None
    try:
        settings = Settings.from_env()
        database = Database(settings)

        head = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
        with database.session() as session:
            current = session.execute(text("SELECT version_num FROM alembic_version")).scalar()
            extension = session.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
        logger.info(f"Alembic revision={current} (head={head}), pgvector={extension}")
        if current != head:
            raise AssertionError(f"Migrations not applied: at {current}, head is {head}")
        if extension is None:
            raise AssertionError("pgvector extension is not installed")

        TenderRepository(database).save(
            Tender(tender_id=tender_id, organization_acronym=organization_acronym)
        )
        tender = Tender(tender_id=tender_id, organization_acronym=organization_acronym)
        chunks = [
            Chunk(
                index=index,
                text=f"chunk {index}",
                page_numbers=(index + 1,),
                headings=("Article 1", f"Section {index}"),
                embedding_model=EMBEDDING_MODEL,
                embedding=_unit_vector(settings.embedding_dim, index),
            )
            for index in range(3)
        ]
        store = PgVectorStore(database)
        store.replace_tender_files(
            tender,
            [DceFile(path="CPS.pdf", file_type="pdf", status=DceFileStatus.CHUNKED, chunks=chunks)],
        )

        hits = store.search(_unit_vector(settings.embedding_dim, 1), EMBEDDING_MODEL, limit=3)
        logger.info(f"Search hits: {[(h.tender_id, h.chunk_index, h.distance) for h in hits]}")
        nearest = hits[0]
        if (
            nearest.tender_id != tender_id
            or nearest.dce_file_path != "CPS.pdf"
            or nearest.chunk_index != 1
            or nearest.page_numbers != (2,)
            or nearest.headings != ("Article 1", "Section 1")
            or abs(nearest.distance) > 1e-6
        ):
            raise AssertionError(f"Unexpected nearest chunk: {nearest}")

        logger.info("Vector store round-trip verified successfully")
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
