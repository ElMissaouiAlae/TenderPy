"""Tests for discovery.orchestrator module."""

from datetime import date
from unittest.mock import Mock

from core.models import Tender
from discovery.orchestrator import DiscoveryOrchestrator

START_DATE = date(2026, 9, 19)
END_DATE = date(2026, 9, 20)


def test_discover_searches_and_persists_tenders():
    playwright = Mock()
    repository = Mock()
    orchestrator = DiscoveryOrchestrator("https://example.test/search", playwright, repository)
    tenders = [Tender(tender_id="1")]
    orchestrator._client.search = Mock(return_value=tenders)

    result = orchestrator.discover(START_DATE, END_DATE)

    assert result == tenders
    orchestrator._client.search.assert_called_once_with(START_DATE, END_DATE)
    repository.save_many.assert_called_once_with(tenders)
