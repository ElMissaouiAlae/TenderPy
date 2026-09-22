"""High-level discovery orchestration."""

from __future__ import annotations

from datetime import date

from playwright.sync_api import Playwright

from core.models import Tender
from persistence.repository import TenderRepository

from .client import DiscoveryClient


class DiscoveryOrchestrator:
    """High-level orchestration that hides pagination complexity from callers."""

    def __init__(self, url: str, playwright: Playwright, repository: TenderRepository) -> None:
        """Initialize the orchestrator with Playwright and a repository."""
        self._client = DiscoveryClient(url, playwright)
        self._repository = repository

    def discover(self, start_date: date, end_date: date) -> list[Tender]:
        """Discover all tenders in the date range and persist them."""
        tenders = self._client.search(start_date, end_date)
        self._repository.save_many(tenders)
        return tenders
