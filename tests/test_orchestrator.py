"""Tests for discovery.orchestrator module."""

from unittest.mock import Mock

import pytest

from core.models import Tender
from discovery.orchestrator import DiscoveryOrchestrator
from discovery.parser import SearchCriteria, SearchResultPage


def test_discovery_orchestrator_initialization():
    session = Mock()
    repository = Mock()
    orchestrator = DiscoveryOrchestrator(session, repository)
    assert orchestrator._client is not None
    assert orchestrator._repository is repository


def test_discover_returns_all_tenders():
    session = Mock()
    repository = Mock()
    orchestrator = DiscoveryOrchestrator(session, repository)

    # Mock the client to return multiple pages
    mock_pages = [
        SearchResultPage(tenders=[Tender(tender_id="1"), Tender(tender_id="2")]),
        SearchResultPage(tenders=[Tender(tender_id="3"), Tender(tender_id="4")]),
        SearchResultPage(tenders=[Tender(tender_id="5")])
    ]
    orchestrator._client.search_all = Mock(return_value=mock_pages)

    criteria = SearchCriteria(keyword="test")
    tenders = orchestrator.discover(criteria)

    assert len(tenders) == 5
    assert tenders[0].tender_id == "1"
    assert tenders[4].tender_id == "5"
    orchestrator._client.search_all.assert_called_once_with(criteria)
    repository.save_many.assert_called_once_with(tenders)


def test_discover_with_empty_results():
    session = Mock()
    repository = Mock()
    orchestrator = DiscoveryOrchestrator(session, repository)

    mock_pages = [SearchResultPage(tenders=[])]
    orchestrator._client.search_all = Mock(return_value=mock_pages)

    criteria = SearchCriteria(keyword="test")
    tenders = orchestrator.discover(criteria)

    assert len(tenders) == 0
    repository.save_many.assert_called_once_with([])


def test_discover_paginated_returns_pages():
    session = Mock()
    repository = Mock()
    orchestrator = DiscoveryOrchestrator(session, repository)

    mock_pages = [
        SearchResultPage(tenders=[Tender(tender_id="1"), Tender(tender_id="2")]),
        SearchResultPage(tenders=[Tender(tender_id="3")])
    ]
    orchestrator._client.search_all = Mock(return_value=mock_pages)

    criteria = SearchCriteria(keyword="test")
    pages = orchestrator.discover_paginated(criteria)

    assert len(pages) == 2
    assert len(pages[0]) == 2
    assert len(pages[1]) == 1
    assert pages[0][0].tender_id == "1"
    assert pages[1][0].tender_id == "3"
    orchestrator._client.search_all.assert_called_once_with(criteria)


def test_discover_paginated_with_empty_pages():
    session = Mock()
    repository = Mock()
    orchestrator = DiscoveryOrchestrator(session, repository)

    mock_pages = [SearchResultPage(tenders=[]), SearchResultPage(tenders=[])]
    orchestrator._client.search_all = Mock(return_value=mock_pages)

    criteria = SearchCriteria(keyword="test")
    pages = orchestrator.discover_paginated(criteria)

    assert len(pages) == 2
    assert all(len(page) == 0 for page in pages)
