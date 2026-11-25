"""Mapper functions for converting between domain and ORM models."""

from __future__ import annotations

from core.dates import in_moroccan_time
from core.models import Tender
from persistence.models import TenderRecord, TenderStatus


def to_record(tender: Tender) -> TenderRecord:
    """Convert a domain Tender to a TenderRecord ORM instance.

    Args:
        tender: Domain Tender object.

    Returns:
        TenderRecord ORM instance with fields mapped from the domain model.
        Status defaults to DISCOVERED, created_at/updated_at are set by database.
    """
    return TenderRecord(
        tender_id=tender.tender_id,
        organization_acronym=tender.organization_acronym,
        procurement_type=tender.procurement_type,
        category=tender.category,
        publication_date=tender.publication_date,
        reference_number=tender.reference_number,
        tender_object=tender.tender_object,
        public_buyer=tender.public_buyer,
        location=tender.location,
        deadline=tender.deadline,
        status=TenderStatus.DISCOVERED.value,
    )


def to_domain(record: TenderRecord) -> Tender:
    """Convert a TenderRecord ORM instance to a domain Tender.

    Args:
        record: TenderRecord ORM instance.

    Returns:
        Domain Tender object with fields mapped from the ORM model.
    """
    return Tender(
        tender_id=record.tender_id,
        organization_acronym=record.organization_acronym,
        procurement_type=record.procurement_type,
        category=record.category,
        publication_date=record.publication_date,
        reference_number=record.reference_number,
        tender_object=record.tender_object,
        public_buyer=record.public_buyer,
        location=record.location,
        deadline=in_moroccan_time(record.deadline),
    )
