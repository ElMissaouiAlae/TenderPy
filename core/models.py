"""Domain model for tenders discovered by the crawler."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .exceptions import MissingTenderFieldError


@dataclass
class Tender:
    """Represents a single tender discovered in search results."""

    tender_id: str | None = None
    organization_acronym: str | None = None
    procurement_type: str | None = None
    category: str | None = None
    publication_date: date | None = None
    reference_number: str | None = None
    tender_object: str | None = None
    public_buyer: str | None = None
    location: str | None = None
    # Timezone-aware, in Moroccan local time (Africa/Casablanca).
    deadline: datetime | None = None

    def validate(self) -> None:
        """Ensure identity fields are populated before persistence.

        Raises:
            MissingTenderFieldError: if tender_id or organization_acronym is
                missing. Both are required for the (tender_id, organization_acronym)
                uniqueness constraint the persistence layer relies on to dedupe records.
        """
        if not self.tender_id:
            raise MissingTenderFieldError("Tender.tender_id is required")
        if not self.organization_acronym:
            raise MissingTenderFieldError("Tender.organization_acronym is required")
