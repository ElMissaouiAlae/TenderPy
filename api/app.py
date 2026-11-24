"""FastAPI application factory for the dashboard API."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from core.dates import in_moroccan_time
from downloader import dce_archive_name
from persistence.database_probe import DatabaseProbe
from persistence.exceptions import DocumentNotFoundError
from persistence.file_storage import DocumentStorage
from persistence.insights import Insights
from persistence.tender_lookup import TenderDetail, TenderLookup

DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 200

# Gives the current time (timezone-aware). Injected so tests can fix "now".
Clock = Callable[[], datetime]


def system_clock() -> datetime:
    """The current time, in UTC."""
    return datetime.now(UTC)


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


class ClosingSoonTenderResponse(BaseModel):
    """An open tender closing soon, as listed on the Insights page."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_number: str | None
    tender_object: str | None
    public_buyer: str | None
    deadline: Deadline


class ClosingSoonResponse(BaseModel):
    """Open tenders closing within 14 days, by time left, nearest deadline first."""

    model_config = ConfigDict(from_attributes=True)

    lt3: list[ClosingSoonTenderResponse]
    from_3_to_7: list[ClosingSoonTenderResponse] = Field(serialization_alias="3to7")
    from_7_to_14: list[ClosingSoonTenderResponse] = Field(serialization_alias="7to14")


def create_app(
    tender_lookup: TenderLookup,
    insights: Insights,
    document_storage: DocumentStorage,
    database_probe: DatabaseProbe,
    clock: Clock = system_clock,
) -> FastAPI:
    """Build the API from its collaborators.

    Args:
        tender_lookup: Read-only access to every discovered tender.
        insights: Read-only aggregate answers for the Insights page.
        document_storage: Storage the tenders' DCE archives are loaded from.
        database_probe: Reports whether the database answers, for /health.
        clock: Gives "now" for deadline-based results.

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
        closing_soon: bool = Query(False),
    ) -> list[TenderSummaryResponse]:
        """List every discovered tender, newest publication first.

        With closing_soon, list only open tenders closing within 14 days,
        nearest deadline first.
        """
        summaries = tender_lookup.list_tenders(
            limit=limit,
            offset=offset,
            closing_soon_at=clock() if closing_soon else None,
        )
        return [TenderSummaryResponse.model_validate(summary) for summary in summaries]

    @app.get("/insights/closing-soon", response_model=ClosingSoonResponse)
    def closing_soon() -> ClosingSoonResponse:
        """Open tenders closing within 14 days: lt3, 3to7 and 7to14 days left."""
        return ClosingSoonResponse.model_validate(insights.closing_soon(clock()))

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
