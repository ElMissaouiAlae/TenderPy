"""Tests for the HTTP API, driven through FastAPI's test client.

The app is built by create_app with an in-memory tender lookup and
LocalDocumentStorage on a temp directory.
"""

import pytest
from fastapi.testclient import TestClient

from api.app import MAX_LIST_LIMIT, create_app
from persistence.file_storage import LocalDocumentStorage
from persistence.models import INDEXABLE_LAST_STATUSES, TenderStatus
from persistence.tender_lookup import TenderSummary

SUMMARY_FIELDS = {"id", "reference_number", "tender_object", "public_buyer", "tender_end_date"}


class InMemoryTenderLookup:
    """Tenders in list order; each entry is (summary, status) or (summary, FAILED, last_status)."""

    def __init__(self, tenders: list[tuple]) -> None:
        self._tenders = tenders

    def list_with_dce_archive(self, limit: int, offset: int) -> list[TenderSummary]:
        matching = [summary for summary, *statuses in self._tenders if self._has_archive(*statuses)]
        return matching[offset : offset + limit]

    @staticmethod
    def _has_archive(status: TenderStatus, last_status: TenderStatus | None = None) -> bool:
        return status in INDEXABLE_LAST_STATUSES or (
            status == TenderStatus.FAILED and last_status in INDEXABLE_LAST_STATUSES
        )


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
    def make(tenders: list[tuple]) -> TestClient:
        app = create_app(
            tender_lookup=InMemoryTenderLookup(tenders),
            document_storage=LocalDocumentStorage(tmp_path),
        )
        return TestClient(app)

    return make


def test_list_returns_only_tenders_with_a_dce_archive(make_client):
    client = make_client(
        [
            (summary(1), TenderStatus.DISCOVERED),
            (summary(2), TenderStatus.UPLOADED),
            (summary(3), TenderStatus.DOWNLOADING),
            (summary(4), TenderStatus.INDEXED),
            (summary(5), TenderStatus.FAILED, TenderStatus.DOWNLOADING),
            (summary(6), TenderStatus.FAILED, TenderStatus.CHUNKED),
        ]
    )

    response = client.get("/tenders")

    assert response.status_code == 200
    assert [tender["id"] for tender in response.json()] == [2, 4, 6]


def test_list_returns_summary_fields_only(make_client):
    client = make_client([(summary(7), TenderStatus.UPLOADED)])

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
    assert set(response.json()[0]) == SUMMARY_FIELDS


def test_list_honours_limit_and_offset(make_client):
    client = make_client([(summary(id), TenderStatus.UPLOADED) for id in range(1, 11)])

    response = client.get("/tenders", params={"limit": 3, "offset": 4})

    assert [tender["id"] for tender in response.json()] == [5, 6, 7]


def test_list_applies_a_default_limit(make_client):
    client = make_client(
        [(summary(id), TenderStatus.UPLOADED) for id in range(1, MAX_LIST_LIMIT + 2)]
    )

    response = client.get("/tenders")

    assert 0 < len(response.json()) <= MAX_LIST_LIMIT


@pytest.mark.parametrize("params", [{"limit": MAX_LIST_LIMIT + 1}, {"limit": 0}, {"offset": -1}])
def test_list_rejects_out_of_range_paging(make_client, params):
    client = make_client([(summary(1), TenderStatus.UPLOADED)])

    response = client.get("/tenders", params=params)

    assert response.status_code == 422
