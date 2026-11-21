"""Tests for the HTTP API, driven through FastAPI's test client.

The app is built by create_app with an in-memory tender lookup and
LocalDocumentStorage on a temp directory. Which tenders have a DCE archive is
decided by the lookup and checked against the real database in
integration_tests/tender_lookup.py.
"""

from collections.abc import Sequence

import pytest
from fastapi.testclient import TestClient

from api.app import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT, create_app
from persistence.database_probe import DatabaseHealth
from persistence.file_storage import LocalDocumentStorage
from persistence.tender_lookup import TenderDetail, TenderSummary


class InMemoryTenderLookup:
    """Holds tenders that have a DCE archive: summaries in list order, details by id."""

    def __init__(self, tenders: Sequence[TenderSummary], details: Sequence[TenderDetail]) -> None:
        self._tenders = list(tenders)
        self._details = {detail.id: detail for detail in details}

    def list_with_dce_archive(self, limit: int, offset: int) -> list[TenderSummary]:
        return self._tenders[offset : offset + limit]

    def get_with_dce_archive(self, id: int) -> TenderDetail | None:
        return self._details.get(id)


class FakeDatabaseProbe:
    """Reports a fixed database health."""

    def __init__(self, health: DatabaseHealth) -> None:
        self._health = health

    def check(self) -> DatabaseHealth:
        return self._health


REACHABLE = DatabaseHealth(reachable=True)


def summary(id: int) -> TenderSummary:
    return TenderSummary(
        id=id,
        reference_number=f"REF-{id}",
        tender_object=f"Object {id}",
        public_buyer=f"Buyer {id}",
        tender_end_date="04/11/2026 10:00",
    )


def detail(id: int) -> TenderDetail:
    return TenderDetail(
        id=id,
        tender_id=f"T-{id}",
        organization_acronym="ORG",
        reference_number=f"REF-{id}",
        tender_object=f"Object {id}",
        public_buyer=f"Buyer {id}",
        location="Casablanca",
        category="Travaux",
        procurement_type="Appel d'offres ouvert",
        publication_date="03/10/2026",
        tender_end_date="04/11/2026 10:00",
    )


@pytest.fixture
def make_client(tmp_path):
    def make(
        tenders: Sequence[TenderSummary] = (),
        details: Sequence[TenderDetail] = (),
        database_health: DatabaseHealth = REACHABLE,
    ) -> TestClient:
        app = create_app(
            tender_lookup=InMemoryTenderLookup(tenders, details),
            document_storage=LocalDocumentStorage(tmp_path),
            database_probe=FakeDatabaseProbe(database_health),
        )
        return TestClient(app)

    return make


def test_list_returns_the_lookups_tenders_in_order(make_client):
    client = make_client([summary(4), summary(2), summary(6)])

    response = client.get("/tenders")

    assert response.status_code == 200
    assert [tender["id"] for tender in response.json()] == [4, 2, 6]


def test_list_returns_summary_fields_only(make_client):
    client = make_client([summary(7)])

    response = client.get("/tenders")

    assert response.json() == [
        {
            "id": 7,
            "reference_number": "REF-7",
            "tender_object": "Object 7",
            "public_buyer": "Buyer 7",
            "tender_end_date": "04/11/2026 10:00",
        }
    ]


def test_list_honours_limit_and_offset(make_client):
    client = make_client([summary(id) for id in range(1, 11)])

    response = client.get("/tenders", params={"limit": 3, "offset": 4})

    assert [tender["id"] for tender in response.json()] == [5, 6, 7]


def test_list_applies_a_default_limit(make_client):
    client = make_client([summary(id) for id in range(1, DEFAULT_LIST_LIMIT + 11)])

    response = client.get("/tenders")

    assert len(response.json()) == DEFAULT_LIST_LIMIT


def test_list_allows_the_maximum_limit(make_client):
    client = make_client([summary(id) for id in range(1, MAX_LIST_LIMIT + 11)])

    response = client.get("/tenders", params={"limit": MAX_LIST_LIMIT})

    assert len(response.json()) == MAX_LIST_LIMIT


@pytest.mark.parametrize("params", [{"limit": MAX_LIST_LIMIT + 1}, {"limit": 0}, {"offset": -1}])
def test_list_rejects_out_of_range_paging(make_client, params):
    client = make_client([summary(1)])

    response = client.get("/tenders", params=params)

    assert response.status_code == 422


def test_detail_returns_the_detail_fields_only(make_client):
    client = make_client(details=[detail(3)])

    response = client.get("/tenders/3")

    assert response.status_code == 200
    assert response.json() == {
        "id": 3,
        "tender_id": "T-3",
        "organization_acronym": "ORG",
        "reference_number": "REF-3",
        "tender_object": "Object 3",
        "public_buyer": "Buyer 3",
        "location": "Casablanca",
        "category": "Travaux",
        "procurement_type": "Appel d'offres ouvert",
        "publication_date": "03/10/2026",
        "tender_end_date": "04/11/2026 10:00",
    }


def test_detail_is_not_found_when_the_lookup_has_no_such_tender(make_client):
    client = make_client(details=[detail(3)])

    response = client.get("/tenders/4")

    assert response.status_code == 404


ARCHIVE_BYTES = b"PK\x03\x04archive-bytes"


def test_archive_download_returns_the_stored_zip_as_an_attachment(make_client, tmp_path):
    (tmp_path / "T-3_ORG.zip").write_bytes(ARCHIVE_BYTES)
    client = make_client(details=[detail(3)])

    response = client.get("/tenders/3/dce-archive")

    assert response.status_code == 200
    assert response.content == ARCHIVE_BYTES
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"] == 'attachment; filename="T-3_ORG.zip"'


def test_archive_download_is_not_found_for_an_unknown_tender_or_one_without_a_dce_archive(
    make_client, tmp_path
):
    # The lookup returns no tender in both cases; which tenders have a DCE
    # archive is checked against the real database in
    # integration_tests/tender_lookup.py. The stored zip shows that a file in
    # storage alone is not enough.
    (tmp_path / "T-4_ORG.zip").write_bytes(ARCHIVE_BYTES)
    client = make_client(details=[detail(3)])

    response = client.get("/tenders/4/dce-archive")

    assert response.status_code == 404


def test_archive_download_is_not_found_when_the_archive_is_missing_from_storage(make_client):
    client = make_client(details=[detail(3)])

    response = client.get("/tenders/3/dce-archive")

    assert response.status_code == 404


def test_health_is_ok_when_the_database_is_reachable(make_client):
    client = make_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"database": "ok"}


def test_health_is_unavailable_with_the_reason_when_the_database_is_unreachable(make_client):
    client = make_client(
        database_health=DatabaseHealth(reachable=False, reason="host does not resolve")
    )

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"database": "unreachable", "reason": "host does not resolve"}


def test_health_never_carries_the_database_url_or_credentials(make_client):
    # The Postgres probe keeps the URL out of its reason (checked in
    # integration_tests/database_probe.py); /health must not add it back.
    database_url = "postgresql://avnadmin:s3cret@pg-tenderpy.aivencloud.com:12345/defaultdb"
    for database_health in (REACHABLE, DatabaseHealth(reachable=False, reason="timed out")):
        client = make_client(database_health=database_health)

        response = client.get("/health")

        assert set(response.json()) <= {"database", "reason"}
        for secret in (database_url, "avnadmin", "s3cret", "aivencloud"):
            assert secret not in response.text
