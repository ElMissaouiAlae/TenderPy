"""Test top counts and response windows through the HTTP API.

Runs against a real Postgres database, with the real insights module and
fixed clocks far enough in the future that no real tender is published in
the 30 or 90 days before them. Top counts and response windows use two
different clocks, years apart, so their tenders never share a period.
"""

import tempfile
from datetime import UTC, date, datetime, time, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import delete

from api.app import create_app
from core.dates import MOROCCO
from core.models import Tender
from persistence import Database, Settings, TenderRecord, TenderRepository
from persistence.database_probe import PostgresDatabaseProbe
from persistence.file_storage import LocalDocumentStorage
from persistence.insights import PostgresInsights
from persistence.tender_lookup import PostgresTenderLookup

from .config import logger

ORGANIZATION_ACRONYM = "TOP-WINDOW-TEST-ORG"

# Noon UTC is the same calendar day in Casablanca.
TOP_NOW = datetime(2041, 6, 15, 12, 0, tzinfo=UTC)
TOP_TODAY = date(2041, 6, 15)
OPEN = TOP_NOW + timedelta(days=10)
CLOSED = TOP_NOW - timedelta(days=1)

# (suffix, public buyer, category, location, days since publication, deadline)
TOP_CASES = [
    ("R1", "commune de rabat", "Travaux", "Rabat", 1, CLOSED),
    ("R2", "Commune de Rabat", "Travaux", "rabat", 2, OPEN),
    ("R3", "Commune de Rabat", "Services", " Rabat ", 3, OPEN),
    ("R4", "  COMMUNE   de Rabat ", "Services", "Rabat", 4, OPEN),
    ("F5", "Province de Fès", "Fournitures", "Fès", 5, OPEN),
    ("F6", "Province de Fès", "Fournitures", "Fès", 6, CLOSED),
    ("F7", "Province de Fès", "Travaux", "Fès", 7, CLOSED),
    ("O8", "ONEE", "Travaux", "Casablanca", 8, OPEN),
    ("NONE", None, None, None, 9, OPEN),
    ("BLANK", "   ", "", " ", 10, OPEN),
    # Exactly 30 days ago is outside the 30-day period; 45 is inside 90.
    ("O30", "ONEE", "Travaux", "Casablanca", 30, OPEN),
    ("O45", "ONEE", "Travaux", "Casablanca", 45, OPEN),
]

WINDOW_NOW = datetime(2045, 6, 15, 12, 0, tzinfo=UTC)
WINDOW_TODAY = date(2045, 6, 15)

# (suffix, public buyer, category, days since publication, response window
# in days or None for no deadline, deadline time in Casablanca)
WINDOW_CASES = [
    # Travaux: 9, 10, 20, 30, 40 -> median 20 (odd group); half is 10, so
    # 9 is short and exactly 10 is not.
    ("T9", "Commune de Rabat", "Travaux", 20, 9, time(10)),
    # Just after midnight in Casablanca is the previous day in UTC: the
    # window is counted on the Moroccan date.
    ("T10", "commune de rabat ", "Travaux", 20, 10, time(0, 30)),
    ("T20", "Province de Fès", "Travaux", 5, 20, time(10)),
    ("T30", "Province de Fès", "Travaux", 5, 30, time(10)),
    ("T40", "ONEE", "Travaux", 5, 40, time(10)),
    # Services: 5, 10, 13, 20 -> median 11.5 (even group); 5 is short.
    ("S5", "ONEE", "Services", 2, 5, time(10)),
    ("S10", "ONEE", "Services", 2, 10, time(10)),
    ("S13", "Province de Fès", "Services", 2, 13, time(10)),
    ("S20", "Commune de Rabat", "Services", 2, 20, time(10)),
    # No category: counted per public buyer, never compared as short.
    ("NC1", "Commune de Rabat", None, 3, 1, time(10)),
    # No deadline: no response window.
    ("ND", "ONEE", "Travaux", 3, None, time(10)),
    # Outside the 30-day period.
    ("OLD", "ONEE", "Travaux", 60, 1, time(10)),
]


def _client(database, storage_dir, now):
    return TestClient(
        create_app(
            tender_lookup=PostgresTenderLookup(database),
            insights=PostgresInsights(database),
            document_storage=LocalDocumentStorage(storage_dir),
            database_probe=PostgresDatabaseProbe(database),
            clock=lambda: now,
        )
    )


def _get(client, path, **params):
    response = client.get(path, params=params)
    if response.status_code != 200:
        raise AssertionError(f"{path} {params} failed: {response.status_code} {response.text}")
    return response.json()


def _expect_status(client, path, status, **params):
    response = client.get(path, params=params)
    if response.status_code != status:
        raise AssertionError(f"{path} {params}: expected {status}, got {response.status_code}")


def _check_top(client):
    def top(**params):
        body = _get(client, "/insights/top", **params)
        return [(item["label"], item["tender_count"]) for item in body]

    # Names that differ only in case or spacing are counted together, under
    # their most frequent spelling. Tenders without a value are left out.
    # Ties are broken by label.
    expectations = [
        (
            {"dimension": "public_buyer"},
            [("Commune de Rabat", 4), ("Province de Fès", 3), ("ONEE", 1)],
        ),
        (
            {"dimension": "category"},
            [("Travaux", 4), ("Fournitures", 2), ("Services", 2)],
        ),
        (
            {"dimension": "location"},
            [("Rabat", 4), ("Fès", 3), ("Casablanca", 1)],
        ),
        (
            {"dimension": "public_buyer", "limit": 2},
            [("Commune de Rabat", 4), ("Province de Fès", 3)],
        ),
        (
            {"dimension": "public_buyer", "period": "90d"},
            [("Commune de Rabat", 4), ("ONEE", 3), ("Province de Fès", 3)],
        ),
        (
            {"dimension": "public_buyer", "open_only": True},
            [("Commune de Rabat", 3), ("ONEE", 1), ("Province de Fès", 1)],
        ),
    ]
    for params, expected in expectations:
        got = top(**params)
        logger.info(f"Top {params}: {got}")
        if got != expected:
            raise AssertionError(f"Top {params}: expected {expected}, got {got}")

    _expect_status(client, "/insights/top", 422, dimension="procurement_type")
    _expect_status(client, "/insights/top", 422)
    _expect_status(client, "/insights/top", 422, dimension="category", limit=0)
    _expect_status(client, "/insights/top", 422, dimension="category", limit=1000)
    _expect_status(client, "/insights/top", 422, dimension="category", period="1y")


def _check_response_window(client, prefix, ids):
    def response_window(**params):
        body = _get(client, "/insights/response-window", **params)
        groups = [
            (group["label"], group["median_days"], group["tender_count"])
            for group in body["groups"]
        ]
        short = [
            (
                item["reference_number"].removeprefix(prefix),
                item["response_window_days"],
                item["category_median_days"],
            )
            for item in body["short_response_windows"]
        ]
        return body, groups, short

    body, groups, short = response_window(dimension="category")
    logger.info(f"Response window by category: {groups}, short: {short}")
    if groups != [("Travaux", 20, 5), ("Services", 11.5, 4)]:
        raise AssertionError(f"Unexpected category medians: {groups}")
    # Shortest window first. Exactly half the median is not short; a
    # tender with no category is never short.
    if short != [("S5", 5, 11.5), ("T9", 9, 20)]:
        raise AssertionError(f"Unexpected short response windows: {short}")

    item = body["short_response_windows"][0]
    expected_item = {
        "id": ids["S5"],
        "reference_number": prefix + "S5",
        "tender_object": "Object S5",
        "public_buyer": "ONEE",
        "category": "Services",
        "response_window_days": 5,
        "category_median_days": 11.5,
    }
    if item != expected_item:
        raise AssertionError(f"Unexpected short-window item: {item}")

    # Per public buyer, names that differ only in case or spacing together;
    # tenders without a category count here.
    _, groups, short_by_public_buyer = response_window(dimension="public_buyer")
    logger.info(f"Response window by public buyer: {groups}")
    expected = [
        ("Commune de Rabat", 9.5, 4),
        ("ONEE", 10, 3),
        ("Province de Fès", 20, 3),
    ]
    if groups != expected:
        raise AssertionError(f"Unexpected public buyer medians: expected {expected}, got {groups}")
    # The short list always compares with the category median.
    if short_by_public_buyer != short:
        raise AssertionError(f"Short list depends on the dimension: {short_by_public_buyer}")

    # Open only: the closed Travaux tenders (9 and 10) drop out, so the
    # Travaux median becomes 30 and nothing in Travaux is short.
    _, groups, short = response_window(dimension="category", open_only=True)
    logger.info(f"Response window by category, open only: {groups}, short: {short}")
    if groups != [("Services", 11.5, 4), ("Travaux", 30, 3)]:
        raise AssertionError(f"Unexpected open-only medians: {groups}")
    if short != [("S5", 5, 11.5)]:
        raise AssertionError(f"Unexpected open-only short windows: {short}")

    _expect_status(client, "/insights/response-window", 422, dimension="location")
    _expect_status(client, "/insights/response-window", 422)
    _expect_status(
        client, "/insights/response-window", 422, dimension="category", period="1y"
    )


def test_top_and_response_window():
    """Test GET /insights/top and GET /insights/response-window.

    Raises on any failure instead of swallowing it - callers must not treat
    a caught exception here as a passing run.
    """
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Top counts and response window (HTTP API against Postgres, fixed clock)")
    logger.info("=" * 60)

    run_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    prefix = f"TOPWIN-{run_id}-"

    database = None
    try:
        database = Database(Settings.from_env())
        repository = TenderRepository(database)

        def save(suffix, public_buyer, category, location, publication_date, deadline):
            reference_number = prefix + suffix
            repository.save(
                Tender(
                    tender_id=reference_number,
                    organization_acronym=ORGANIZATION_ACRONYM,
                    reference_number=reference_number,
                    tender_object=f"Object {suffix}",
                    public_buyer=public_buyer,
                    category=category,
                    location=location,
                    publication_date=publication_date,
                    deadline=deadline,
                )
            )

        for suffix, public_buyer, category, location, days_ago, deadline in TOP_CASES:
            save(suffix, public_buyer, category, location, TOP_TODAY - timedelta(days=days_ago), deadline)

        for suffix, public_buyer, category, days_ago, window, deadline_time in WINDOW_CASES:
            published = WINDOW_TODAY - timedelta(days=days_ago)
            deadline = (
                None
                if window is None
                else datetime.combine(
                    published + timedelta(days=window), deadline_time, tzinfo=MOROCCO
                )
            )
            save(suffix, public_buyer, category, "Rabat", published, deadline)

        with database.session() as session:
            ids = {
                record.reference_number.removeprefix(prefix): record.id
                for record in session.query(TenderRecord).filter(
                    TenderRecord.organization_acronym == ORGANIZATION_ACRONYM
                )
            }

        with tempfile.TemporaryDirectory() as storage_dir:
            _check_top(_client(database, storage_dir, TOP_NOW))
            _check_response_window(_client(database, storage_dir, WINDOW_NOW), prefix, ids)

        logger.info("Top counts and response window verified successfully")
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
    test_top_and_response_window()
