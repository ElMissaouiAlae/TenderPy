"""High-level discovery orchestration."""

from __future__ import annotations

from core.models import Tender
from core.session import SearchSession
from persistence.repository import TenderRepository

from .client import DiscoveryClient
from .parser import SearchCriteria


class DiscoveryOrchestrator:
    """High-level orchestration that hides pagination complexity from callers."""

    def __init__(self, session: SearchSession, repository: TenderRepository) -> None:
        """Initialize the orchestrator with an active SearchSession and a TenderRepository."""
        self._client = DiscoveryClient(session)
        self._repository = repository

    def discover(self, criteria: SearchCriteria) -> list[Tender]:
        """Discover all tenders matching the criteria and persist them as a side effect."""
        all_pages = self._client.search_all(criteria)

        tenders: list[Tender] = []
        for page in all_pages:
            tenders.extend(page.tenders)

        self._repository.save_many(tenders)

        return tenders

    def discover_paginated(self, criteria: SearchCriteria) -> list[list[Tender]]:
        """Discover all tenders, yielding pages of tenders."""
        all_pages = self._client.search_all(criteria)
            
        return [page.tenders for page in all_pages]
