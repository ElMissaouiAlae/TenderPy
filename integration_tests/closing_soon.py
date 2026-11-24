"""Test closing soon through the HTTP API against a real Postgres database.

The app is built with the real tender lookup and insights module and a
fixed clock, far enough in the future that no real tender closes near it.
"""

import tempfile
from datetime import UTC, datetime, timedelta

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

ORGANIZATION_ACRONYM = "CLOSING-SOON-TEST-ORG"
NOW = datetime(2040, 3, 10, 12, 0, tzinfo=UTC)

# (suffix, deadline), saved in this order so ids don't follow deadlines.
CASES = [
    ("14D", NOW + timedelta(days=14)),
    ("CLOSED", NOW - timedelta(days=1)),
    ("7D", NOW + timedelta(days=7)),
    ("HOUR", NOW + timedelta(hours=1)),
    ("NO-DEADLINE", None),
    ("JUST-OVER-14D", NOW + timedelta(days=14, minutes=1)),
    ("3D", NOW + timedelta(days=3)),
    ("JUST-UNDER-3D", NOW + timedelta(days=3, minutes=-1)),
    ("JUST-UNDER-7D", NOW + timedelta(days=7, minutes=-1)),
]


def test_closing_soon():
    """Test the /tenders closing-soon filter and GET /insights/closing-soon.

    Raises on any failure instead of swallowing it - callers must not treat
    a caught exception here as a passing run.
    """
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Closing soon (HTTP API against Postgres, fixed clock)")
    logger.info("=" * 60)

    run_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    prefix = f"CLOSING-{run_id}-"

    database = None
    try:
        database = Database(Settings.from_env())
        repository = TenderRepository(database)
        for suffix, deadline in CASES:
            reference_number = prefix + suffix
            repository.save(
                Tender(
                    tender_id=reference_number,
                    organization_acronym=ORGANIZATION_ACRONYM,
                    reference_number=reference_number,
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

            def ours(tenders):
                return [
                    tender["reference_number"].removeprefix(prefix)
                    for tender in tenders
                    if (tender["reference_number"] or "").startswith(prefix)
                ]

            # The list filter: open, closing within 14 days, nearest deadline first.
            response = client.get("/tenders", params={"closing_soon": True, "limit": 200})
            if response.status_code != 200:
                raise AssertionError(f"/tenders?closing_soon failed: {response.status_code}")
            listed = ours(response.json())
            expected = ["HOUR", "JUST-UNDER-3D", "3D", "JUST-UNDER-7D", "7D", "14D"]
            logger.info(f"Closing-soon list: {listed}")
            if listed != expected:
                raise AssertionError(f"Expected {expected}, got {listed}")

            # Insights: open tenders in buckets, each nearest deadline first.
            # Exactly 3 or 7 days left falls in the next bucket up; exactly 14
            # days left is still closing soon.
            response = client.get("/insights/closing-soon")
            if response.status_code != 200:
                raise AssertionError(f"/insights/closing-soon failed: {response.status_code}")
            body = response.json()
            buckets = {name: ours(items) for name, items in body.items()}
            expected_buckets = {
                "lt3": ["HOUR", "JUST-UNDER-3D"],
                "3to7": ["3D", "JUST-UNDER-7D"],
                "7to14": ["7D", "14D"],
            }
            logger.info(f"Closing-soon buckets: {buckets}")
            if buckets != expected_buckets:
                raise AssertionError(f"Expected {expected_buckets}, got {buckets}")

            hour = next(
                item for item in body["lt3"] if item["reference_number"] == prefix + "HOUR"
            )
            # 13:00 UTC on 10 March 2040 is 14:00 in Casablanca (UTC+1).
            expected_item = {
                "reference_number": prefix + "HOUR",
                "tender_object": None,
                "public_buyer": None,
                "deadline": "2040-03-10T14:00:00+01:00",
            }
            if set(hour) != {"id", *expected_item} or any(
                hour[key] != value for key, value in expected_item.items()
            ):
                raise AssertionError(f"Unexpected closing-soon item: {hour}")

        logger.info("Closing soon verified successfully")
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
    test_closing_soon()
