"""FastAPI application factory for the dashboard API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, PlainSerializer

from core.dates import in_moroccan_time
from downloader import dce_archive_name
from persistence.database_probe import DatabaseProbe
from persistence.exceptions import DocumentNotFoundError
from persistence.file_storage import DocumentStorage
from persistence.tender_lookup import TenderDetail, TenderLookup

DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 200

# A deadline is sent as ISO 8601 with Morocco's offset, whatever timezone the
# lookup read it in.
Deadline = Annotated[datetime | None, PlainSerializer(in_moroccan_time)]


class TenderSummaryResponse(BaseModel):
    """A tender as shown in the tender list."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_number: str | None
    tender_object: str | None
    public_buyer: str | None
    deadline: Deadline
    has_dce_archive: bool


class TenderDetailResponse(BaseModel):
    """A tender as shown on its own page."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tender_id: str | None
    organization_acronym: str | None
    reference_number: str | None
    tender_object: str | None
    public_buyer: str | None
    location: str | None
    category: str | None
    procurement_type: str | None
    publication_date: date | None
    deadline: Deadline
    has_dce_archive: bool


def create_app(
    tender_lookup: TenderLookup,
    document_storage: DocumentStorage,
    database_probe: DatabaseProbe,
) -> FastAPI:
    """Build the API from its collaborators.

    Args:
        tender_lookup: Read-only access to every discovered tender.
        document_storage: Storage the tenders' DCE archives are loaded from.
        database_probe: Reports whether the database answers, for /health.

    Returns:
        The FastAPI application.
    """
    app = FastAPI(title="TenderPy")

    def require_tender(id: int) -> TenderDetail:
        """Return a tender, or respond 404."""
        detail = tender_lookup.get_tender(id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Tender not found")
        return detail

    @app.get("/health")
    def health() -> JSONResponse:
        """Report whether the database answers: 200 if it does, 503 if not."""
        database_health = database_probe.check()
        if database_health.reachable:
            return JSONResponse({"database": "ok"})
        return JSONResponse(
            {"database": "unreachable", "reason": database_health.reason},
            status_code=503,
        )

    @app.get("/tenders", response_model=list[TenderSummaryResponse])
    def list_tenders(
        limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
        offset: int = Query(0, ge=0),
    ) -> list[TenderSummaryResponse]:
        """List every discovered tender, newest publication first."""
        return [
            TenderSummaryResponse.model_validate(summary)
            for summary in tender_lookup.list_tenders(limit=limit, offset=offset)
        ]

    @app.get("/tenders/{id}", response_model=TenderDetailResponse)
    def get_tender(id: int) -> TenderDetailResponse:
        """Return one tender, whether or not it has a DCE archive."""
        detail = require_tender(id)
        return TenderDetailResponse.model_validate(detail)

    @app.get("/tenders/{id}/dce-archive", response_class=Response)
    def download_dce_archive(id: int) -> Response:
        """Return a tender's DCE archive as a zip attachment."""
        detail = require_tender(id)
        if not detail.has_dce_archive:
            raise HTTPException(status_code=404, detail="DCE archive not found")
        archive_name = dce_archive_name(detail.tender_id, detail.organization_acronym)
        try:
            archive = document_storage.load_document(archive_name)
        except DocumentNotFoundError as error:
            raise HTTPException(status_code=404, detail="DCE archive not found") from error
        return Response(
            content=archive,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{archive_name}"'},
        )

    return app
