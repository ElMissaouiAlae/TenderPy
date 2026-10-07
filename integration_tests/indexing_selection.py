"""Test TenderRepository.find_for_indexing against a real Postgres database."""

from datetime import UTC, datetime

from sqlalchemy import delete

from core.models import Tender
from persistence import Database, Settings, TenderRecord, TenderRepository, TenderStatus

from .config import logger

ORGANIZATION_ACRONYM = "INDEXING-SELECTION-TEST-ORG"


def test_indexing_selection():
    """Test which tenders find_for_indexing picks.

    Saves tenders that are UPLOADED, FAILED after upload, FAILED before
    upload and DISCOVERED, then checks that only the first two kinds are
    selected, oldest record first.

    Raises on any failure instead of swallowing it - callers must not treat
    a caught exception here as a passing run.
    """
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Indexing Selection (persists to Postgres)")
    logger.info("=" * 60)

    run_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")

    database = None
    try:
        database = Database(Settings.from_env())
        repository = TenderRepository(database)

        # (suffix, status, last_status) in record order.
        cases = [
            ("UPLOADED", TenderStatus.UPLOADED, None),
            ("FAILED-CHUNKED", TenderStatus.FAILED, TenderStatus.CHUNKED),
            ("FAILED-DOWNLOADED", TenderStatus.FAILED, TenderStatus.DOWNLOADED),
            ("DISCOVERED", TenderStatus.DISCOVERED, None),
            ("FAILED-UPLOADED", TenderStatus.FAILED, TenderStatus.UPLOADED),
        ]
        for suffix, status, last_status in cases:
            tender_id = f"SELECT-{run_id}-{suffix}"
            repository.save(Tender(tender_id=tender_id, organization_acronym=ORGANIZATION_ACRONYM))
            if status != TenderStatus.DISCOVERED:
                repository.update_status(
                    tender_id, ORGANIZATION_ACRONYM, status, last_status=last_status
                )

        # The test tenders are the newest records, so a limit larger than the
        # table reaches them whatever else the database holds.
        selected = [
            tender.tender_id
            for tender in repository.find_for_indexing(limit=1_000_000)
            if tender.organization_acronym == ORGANIZATION_ACRONYM
            and tender.tender_id.startswith(f"SELECT-{run_id}-")
        ]
        expected = [
            f"SELECT-{run_id}-UPLOADED",
            f"SELECT-{run_id}-FAILED-CHUNKED",
            f"SELECT-{run_id}-FAILED-UPLOADED",
        ]
        logger.info(f"Selected for indexing: {selected}")
        if selected != expected:
            raise AssertionError(f"Expected {expected}, got {selected}")

        logger.info("Indexing selection verified successfully")
    finally:
        if database is not None:
            with database.session() as session:
                session.execute(
                    delete(TenderRecord).where(
                        TenderRecord.organization_acronym == ORGANIZATION_ACRONYM
                    )
                )
            database.close()
