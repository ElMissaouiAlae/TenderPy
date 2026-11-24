"""Test coverage, periods, open only and New this week through the HTTP API.

Runs against a real Postgres database, with the real insights module and a
fixed clock far enough in the future that no real tender is published in
the 7, 30 or 90 days before it.
"""

import tempfile
from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import delete

from api.app import create_app
from core.models import Tender
from persistence import Database, Settings, TenderRecord, TenderRepository
from persistence.database_probe import PostgresDatabaseProbe
from persistence.file_storage import LocalDocumentStorage
from persistence.insights import PostgresInsights
from persistence.tender_lookup import PostgresTenderLookup

from .config import logger

ORGANIZATION_ACRONYM = "COVERAGE-TEST-ORG"
# Noon UTC is the same calendar day in Casablanca.
NOW = datetime(2041, 6, 15, 12, 0, tzinfo=UTC)
TODAY = date(2041, 6, 15)

OPEN = NOW + timedelta(days=10)
CLOSED = NOW - timedelta(days=1)

# (suffix, publication date, deadline), saved in this order so ids don't
# follow publication dates.
CASES = [
    ("7D", TODAY - timedelta(days=7), OPEN),
    ("TODAY", TODAY, OPEN),
    ("60D", TODAY - timedelta(days=60), CLOSED),
    ("6D", TODAY - timedelta(days=6), CLOSED),
    ("29D-NO-DEADLINE", TODAY - timedelta(days=29), None),
    ("30D", TODAY - timedelta(days=30), OPEN),
    ("NO-PUBLICATION-DATE", None, OPEN),
]


def _coverage(count, earliest, latest, without_deadline):
    return {
        "tender_count": count,
        "earliest_publication_date": earliest.isoformat() if earliest else None,
        "latest_publication_date": latest.isoformat() if latest else None,
        "without_deadline_count": without_deadline,
    }


def test_coverage_and_new_this_week():
    """Test GET /insights/coverage and GET /insights/new-this-week.

    Raises on any failure instead of swallowing it - callers must not treat
    a caught exception here as a passing run.
    """
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Coverage and New this week (HTTP API against Postgres, fixed clock)")
    logger.info("=" * 60)

    run_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    prefix = f"COVERAGE-{run_id}-"

    database = None
    try:
        database = Database(Settings.from_env())
        repository = TenderRepository(database)
        for suffix, publication_date, deadline in CASES:
            reference_number = prefix + suffix
            repository.save(
                Tender(
                    tender_id=reference_number,
                    organization_acronym=ORGANIZATION_ACRONYM,
                    reference_number=reference_number,
                    tender_object=f"Object {suffix}",
                    public_buyer=f"Buyer {suffix}",
                    publication_date=publication_date,
                    deadline=deadline,
                )
            )

        with tempfile.TemporaryDirectory() as storage_dir:
            client = TestClient(
                create_app(
                    tender_lookup=PostgresTenderLookup(database),
                    insights=PostgresInsights(database),
                    document_storage=LocalDocumentStorage(storage_dir),
                    database_probe=PostgresDatabaseProbe(database),
                    clock=lambda: NOW,
                )
            )

            def coverage(**params):
                response = client.get("/insights/coverage", params=params)
                if response.status_code != 200:
                    raise AssertionError(
                        f"/insights/coverage {params} failed: {response.status_code}"
                    )
                return response.json()

            # A period of N days is N calendar days ending today: exactly N
            # days ago is outside it. The range is that of the tenders found,
            # so a period reaching past the data is capped to it. Tenders
            # without a publication date belong to no period. The count
            # without a deadline ignores "open only": it warns that those
            # tenders are missing from deadline-based figures.
            expectations = [
                ({"period": "7d"}, _coverage(2, TODAY - timedelta(days=6), TODAY, 0)),
                ({}, _coverage(4, TODAY - timedelta(days=29), TODAY, 1)),
                ({"period": "30d"}, _coverage(4, TODAY - timedelta(days=29), TODAY, 1)),
                ({"period": "90d"}, _coverage(6, TODAY - timedelta(days=60), TODAY, 1)),
                (
                    {"period": "30d", "open_only": True},
                    _coverage(2, TODAY - timedelta(days=7), TODAY, 1),
                ),
                (
                    {"period": "90d", "open_only": True},
                    _coverage(3, TODAY - timedelta(days=30), TODAY, 1),
                ),
                (
                    {"period": "7d", "open_only": True},
                    _coverage(1, TODAY, TODAY, 0),
                ),
            ]
            for params, expected in expectations:
                got = coverage(**params)
                logger.info(f"Coverage {params}: {got}")
                if got != expected:
                    raise AssertionError(f"Coverage {params}: expected {expected}, got {got}")

            # All time includes the real data, which is all published earlier.
            got = coverage(period="all")
            logger.info(f"Coverage all: {got}")
            if (
                got["tender_count"] < 6
                or got["without_deadline_count"] < 1
                or got["latest_publication_date"] != TODAY.isoformat()
                or got["earliest_publication_date"] > (TODAY - timedelta(days=60)).isoformat()
            ):
                raise AssertionError(f"Unexpected all-time coverage: {got}")

            response = client.get("/insights/coverage", params={"period": "1y"})
            if response.status_code != 422:
                raise AssertionError(f"Expected 422 for period=1y, got {response.status_code}")

            # New this week: published in the last 7 days, newest first;
            # exactly 7 days ago is outside it.
            response = client.get("/insights/new-this-week")
            if response.status_code != 200:
                raise AssertionError(f"/insights/new-this-week failed: {response.status_code}")
            body = response.json()
            if any(
                not (item["reference_number"] or "").startswith(prefix) for item in body
            ):
                raise AssertionError(f"New this week has tenders that aren't ours: {body}")
            listed = [item["reference_number"].removeprefix(prefix) for item in body]
            logger.info(f"New this week: {listed}")
            if listed != ["TODAY", "6D"]:
                raise AssertionError(f"Expected ['TODAY', '6D'], got {listed}")

            today_item = body[0]
            expected_item = {
                "reference_number": prefix + "TODAY",
                "tender_object": "Object TODAY",
                "public_buyer": "Buyer TODAY",
                "publication_date": TODAY.isoformat(),
                # 12:00 UTC on 25 June 2041 is 13:00 in Casablanca (UTC+1).
                "deadline": "2041-06-25T13:00:00+01:00",
            }
            if set(today_item) != {"id", *expected_item} or any(
                today_item[key] != value for key, value in expected_item.items()
            ):
                raise AssertionError(f"Unexpected new-this-week item: {today_item}")

            # Open only applies to New this week too.
            response = client.get("/insights/new-this-week", params={"open_only": True})
            listed = [item["reference_number"].removeprefix(prefix) for item in response.json()]
            if listed != ["TODAY"]:
                raise AssertionError(f"Open only: expected ['TODAY'], got {listed}")

        logger.info("Coverage and New this week verified successfully")
    finally:
        if database is not None:
            with database.session() as session:
                session.execute(
                    delete(TenderRecord).where(
                        TenderRecord.organization_acronym == ORGANIZATION_ACRONYM
                    )
                )
            database.close()


if __name__ == "__main__":
    test_coverage_and_new_this_week()
