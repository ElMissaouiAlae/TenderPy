"""Test PostgresTenderLookup against a real Postgres database."""

from datetime import UTC, date, datetime

from sqlalchemy import delete, select, update

from core.dates import MOROCCO
from core.models import Tender
from persistence import Database, Settings, TenderRecord, TenderRepository, TenderStatus
from persistence.tender_lookup import PostgresTenderLookup

from .config import logger

ORGANIZATION_ACRONYM = "TENDER-LOOKUP-TEST-ORG"


def test_tender_lookup():
    """Test what list_tenders and get_tender return.

    Saves tenders in every relevant state, then checks that all of them are
    listed and can be fetched by id, and that has_dce_archive is true exactly
    for those that reached UPLOADED (including FAILED after upload).

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

        # (suffix, status, last_status, has_dce_archive)
        cases = [
            ("DISCOVERED", TenderStatus.DISCOVERED, None, False),
            ("DOWNLOADING", TenderStatus.DOWNLOADING, None, False),
            ("FAILED-DOWNLOADING", TenderStatus.FAILED, TenderStatus.DOWNLOADING, False),
            ("UPLOADED", TenderStatus.UPLOADED, None, True),
            ("INDEXED", TenderStatus.INDEXED, None, True),
            ("FAILED-UPLOADED", TenderStatus.FAILED, TenderStatus.UPLOADED, True),
            ("FAILED-EMBEDDING", TenderStatus.FAILED, TenderStatus.EMBEDDING, True),
            # Rows from before last_status existed; the repository no longer
            # writes this state, so it is set directly below.
            ("FAILED-NO-LAST-STATUS", TenderStatus.FAILED, None, False),
        ]
        expected = {
            f"LOOKUP-{run_id}-{suffix}": has_archive for suffix, _, _, has_archive in cases
        }
        for suffix, status, last_status, _ in cases:
            reference_number = f"LOOKUP-{run_id}-{suffix}"
            repository.save(
                Tender(
                    tender_id=reference_number,
                    organization_acronym=ORGANIZATION_ACRONYM,
                    reference_number=reference_number,
                )
            )
            if status == TenderStatus.FAILED and last_status is None:
                with database.session() as session:
                    session.execute(
                        update(TenderRecord)
                        .where(
                            TenderRecord.tender_id == reference_number,
                            TenderRecord.organization_acronym == ORGANIZATION_ACRONYM,
                        )
                        .values(status=TenderStatus.FAILED.value, last_status=None)
                    )
            elif status != TenderStatus.DISCOVERED:
                repository.update_status(
                    reference_number, ORGANIZATION_ACRONYM, status, last_status=last_status
                )

        # The test tenders have no publication date, so they sort last; a limit
        # larger than the table reaches them whatever else the database holds.
        listed = {
            summary.reference_number: summary.has_dce_archive
            for summary in lookup.list_tenders(limit=1_000_000, offset=0)
            if (summary.reference_number or "").startswith(f"LOOKUP-{run_id}-")
        }
        logger.info(f"Listed (reference -> has_dce_archive): {listed}")
        if listed != expected:
            raise AssertionError(f"Expected {expected}, got {listed}")

        with database.session() as session:
            ids = dict(
                session.execute(
                    select(TenderRecord.reference_number, TenderRecord.id).where(
                        TenderRecord.organization_acronym == ORGANIZATION_ACRONYM,
                        TenderRecord.reference_number.startswith(f"LOOKUP-{run_id}-"),
                    )
                ).all()
            )
        fetched = {}
        for reference_number, id in ids.items():
            fetched_detail = lookup.get_tender(id)
            if fetched_detail is not None:
                fetched[reference_number] = fetched_detail.has_dce_archive
        logger.info(f"Fetched by id (reference -> has_dce_archive): {fetched}")
        if fetched != expected:
            raise AssertionError(f"Expected {expected} by id, got {fetched}")

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
        dated = lookup.get_tender(dated_id)
        if dated is None or (dated.publication_date, dated.deadline) != (publication_date, deadline):
            raise AssertionError(f"Typed dates did not round-trip: {dated}")
        logger.info(f"Typed dates round-tripped: {dated.publication_date}, {dated.deadline.isoformat()}")

        detail = lookup.get_tender(ids[f"LOOKUP-{run_id}-DISCOVERED"])
        if detail is None or (detail.tender_id, detail.organization_acronym) != (
            f"LOOKUP-{run_id}-DISCOVERED",
            ORGANIZATION_ACRONYM,
        ):
            raise AssertionError(f"Unexpected detail for the DISCOVERED tender: {detail}")

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
