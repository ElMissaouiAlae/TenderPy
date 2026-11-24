"""Test PostgresTenderLookup against a real Postgres database."""

from datetime import UTC, date, datetime

from sqlalchemy import delete, select

from core.dates import MOROCCO
from core.models import Tender
from persistence import Database, Settings, TenderRecord, TenderRepository, TenderStatus
from persistence.tender_lookup import PostgresTenderLookup

from .config import logger

ORGANIZATION_ACRONYM = "TENDER-LOOKUP-TEST-ORG"


def test_tender_lookup():
    """Test which tenders list_with_dce_archive and get_with_dce_archive return.

    Saves tenders in every relevant state, then checks that only those that
    reached UPLOADED (including FAILED after upload) are listed and can be
    fetched by id.

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

        with database.session() as session:
            ids = dict(
                session.execute(
                    select(TenderRecord.reference_number, TenderRecord.id).where(
                        TenderRecord.organization_acronym == ORGANIZATION_ACRONYM,
                        TenderRecord.reference_number.startswith(f"LOOKUP-{run_id}-"),
                    )
                ).all()
            )
        fetched = {
            reference_number
            for reference_number, id in ids.items()
            if lookup.get_with_dce_archive(id) is not None
        }
        logger.info(f"Fetched by id with a DCE archive: {sorted(fetched)}")
        if fetched != expected:
            raise AssertionError(f"Expected {sorted(expected)} by id, got {sorted(fetched)}")

        # Typed dates survive a save and a lookup, the deadline as the same instant.
        dated_reference = f"LOOKUP-{run_id}-DATED"
        publication_date = date(2026, 10, 3)
        deadline = datetime(2026, 11, 4, 10, 0, tzinfo=MOROCCO)
        repository.save(
            Tender(
                tender_id=dated_reference,
                organization_acronym=ORGANIZATION_ACRONYM,
                reference_number=dated_reference,
                publication_date=publication_date,
                deadline=deadline,
            )
        )
        repository.update_status(dated_reference, ORGANIZATION_ACRONYM, TenderStatus.UPLOADED)
        with database.session() as session:
            dated_id = session.scalars(
                select(TenderRecord.id).where(
                    TenderRecord.organization_acronym == ORGANIZATION_ACRONYM,
                    TenderRecord.reference_number == dated_reference,
                )
            ).one()
        dated = lookup.get_with_dce_archive(dated_id)
        if dated is None or (dated.publication_date, dated.deadline) != (publication_date, deadline):
            raise AssertionError(f"Typed dates did not round-trip: {dated}")
        logger.info(f"Typed dates round-tripped: {dated.publication_date}, {dated.deadline.isoformat()}")

        detail = lookup.get_with_dce_archive(ids[f"LOOKUP-{run_id}-UPLOADED"])
        if detail is None or (detail.tender_id, detail.organization_acronym) != (
            f"LOOKUP-{run_id}-UPLOADED",
            ORGANIZATION_ACRONYM,
        ):
            raise AssertionError(f"Unexpected detail for the UPLOADED tender: {detail}")

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
