"""Tests for the HTTP API, driven through FastAPI's test client.

The app is built by create_app with an in-memory tender lookup and
LocalDocumentStorage on a temp directory. Which tenders have a DCE archive is
decided by the lookup and checked against the real database in
integration_tests/tender_lookup.py.
"""

import pytest
from fastapi.testclient import TestClient

from api.app import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT, create_app
from persistence.file_storage import LocalDocumentStorage
from persistence.tender_lookup import TenderSummary


class InMemoryTenderLookup:
    """Holds tenders that have a DCE archive, in list order."""

    def __init__(self, tenders: list[TenderSummary]) -> None:
        self._tenders = tenders

    def list_with_dce_archive(self, limit: int, offset: int) -> list[TenderSummary]:
        return self._tenders[offset : offset + limit]


def summary(id: int) -> TenderSummary:
    return TenderSummary(
        id=id,
        reference_number=f"REF-{id}",
        tender_object=f"Object {id}",
        public_buyer=f"Buyer {id}",
        tender_end_date="04/11/2026 10:00",
    )


@pytest.fixture
def make_client(tmp_path):
    def make(tenders: list[TenderSummary]) -> TestClient:
        app = create_app(
            tender_lookup=InMemoryTenderLookup(tenders),
            document_storage=LocalDocumentStorage(tmp_path),
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
