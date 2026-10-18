"""FastAPI application factory for the dashboard API."""

from __future__ import annotations

from fastapi import FastAPI, Query
from pydantic import BaseModel, ConfigDict

from persistence.file_storage import DocumentStorage
from persistence.tender_lookup import TenderLookup

DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 200


class TenderSummaryResponse(BaseModel):
    """A tender as shown in the tender list."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_number: str | None
    tender_object: str | None
    public_buyer: str | None
    tender_end_date: str | None


def create_app(tender_lookup: TenderLookup, document_storage: DocumentStorage) -> FastAPI:
    """Build the API from its collaborators.

    Args:
        tender_lookup: Read-only access to tenders that have a DCE archive.
        document_storage: Storage the tenders' DCE archives are loaded from.

    Returns:
        The FastAPI application.
    """
    app = FastAPI(title="TenderPy")

    @app.get("/tenders", response_model=list[TenderSummaryResponse])
    def list_tenders(
        limit: int = Query(DEFAULT_LIST_LIMIT, ge=1, le=MAX_LIST_LIMIT),
        offset: int = Query(0, ge=0),
    ) -> list[TenderSummaryResponse]:
        """List tenders that have a DCE archive, newest publication first."""
        return [
            TenderSummaryResponse.model_validate(summary)
            for summary in tender_lookup.list_with_dce_archive(limit=limit, offset=offset)
        ]

    return app
