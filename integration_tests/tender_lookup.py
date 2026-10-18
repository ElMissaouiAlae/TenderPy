"""Test PostgresTenderLookup.list_with_dce_archive against a real Postgres database."""

from datetime import UTC, datetime

from sqlalchemy import delete

from core.models import Tender
from persistence import Database, Settings, TenderRecord, TenderRepository, TenderStatus
from persistence.tender_lookup import PostgresTenderLookup

from .config import logger

ORGANIZATION_ACRONYM = "TENDER-LOOKUP-TEST-ORG"


def test_tender_lookup():
    """Test which tenders list_with_dce_archive returns.

    Saves tenders in every relevant state, then checks that only those that
    reached UPLOADED (including FAILED after upload) are listed.

    Raises on any failure instead of swallowing it - callers must not treat
    a caught exception here as a passing run.
    """
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Tender Lookup (persists to Postgres)")
    logger.info("=" * 60)

    run_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")

    database = None
    try:
        database = Database(Settings.from_env())
        repository = TenderRepository(database)
        lookup = PostgresTenderLookup(database)

        # (suffix, status, last_status)
        cases = [
            ("DISCOVERED", TenderStatus.DISCOVERED, None),
            ("DOWNLOADING", TenderStatus.DOWNLOADING, None),
            ("FAILED-DOWNLOADING", TenderStatus.FAILED, TenderStatus.DOWNLOADING),
            ("UPLOADED", TenderStatus.UPLOADED, None),
            ("INDEXED", TenderStatus.INDEXED, None),
            ("FAILED-UPLOADED", TenderStatus.FAILED, TenderStatus.UPLOADED),
            ("FAILED-EMBEDDING", TenderStatus.FAILED, TenderStatus.EMBEDDING),
        ]
        for suffix, status, last_status in cases:
            reference_number = f"LOOKUP-{run_id}-{suffix}"
            repository.save(
                Tender(
                    tender_id=reference_number,
                    organization_acronym=ORGANIZATION_ACRONYM,
                    reference_number=reference_number,
                )
            )
            if status != TenderStatus.DISCOVERED:
                repository.update_status(
                    reference_number, ORGANIZATION_ACRONYM, status, last_status=last_status
                )

        # The test tenders have no publication date, so they sort last; a limit
        # larger than the table reaches them whatever else the database holds.
        listed = {
            summary.reference_number
            for summary in lookup.list_with_dce_archive(limit=1_000_000, offset=0)
            if (summary.reference_number or "").startswith(f"LOOKUP-{run_id}-")
        }
        expected = {
            f"LOOKUP-{run_id}-UPLOADED",
            f"LOOKUP-{run_id}-INDEXED",
            f"LOOKUP-{run_id}-FAILED-UPLOADED",
            f"LOOKUP-{run_id}-FAILED-EMBEDDING",
        }
        logger.info(f"Listed with a DCE archive: {sorted(listed)}")
        if listed != expected:
            raise AssertionError(f"Expected {sorted(expected)}, got {sorted(listed)}")

        logger.info("Tender lookup verified successfully")
    finally:
        if database is not None:
            with database.session() as session:
                session.execute(
                    delete(TenderRecord).where(
                        TenderRecord.organization_acronym == ORGANIZATION_ACRONYM
                    )
                )
            database.close()
