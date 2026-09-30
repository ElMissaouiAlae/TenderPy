"""Tests for discovery.client module."""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from core.models import Tender
from discovery.client import DiscoveryClient
from discovery.parser import SearchCriteria, SearchResultPage
from core.exceptions import PaginationError, SearchExecutionError


def test_discovery_client_initialization():
    session = Mock()
    client = DiscoveryClient(session)
    assert client._session is session
    assert client._paginator is not None
    assert client._parser is not None


def test_discovery_client_constants():
    assert DiscoveryClient.SEARCH_URL == "index.php?page=entreprise.EntrepriseAdvancedSearch&searchAnnCons"
    assert "ctl0$CONTENU_PAGE$resultSearch$PagerBottom" in DiscoveryClient.PAGER_BOTTOM_PREFIX


def test_build_search_payload_with_keyword():
    session = Mock()
    session.state.to_payload = Mock(return_value={"PRADO_PAGESTATE": "test"})
    client = DiscoveryClient(session)
    
    criteria = SearchCriteria(keyword="infrastructure")
    payload = client._build_search_payload(criteria)
    
    assert payload[client.KEYWORD_PARAM] == "infrastructure"
    assert "PRADO_POSTBACK_TARGET" in payload


def test_build_search_payload_with_all_fields():
    session = Mock()
    session.state.to_payload = Mock(return_value={"PRADO_PAGESTATE": "test"})
    client = DiscoveryClient(session)
    
    criteria = SearchCriteria(
        keyword="test",
        buyer="City Hall",
        organization="Public Works",
        publication_date_from=date(2026, 1, 15),
        publication_date_to=date(2026, 1, 30)
    )
    payload = client._build_search_payload(criteria)
    
    assert payload[client.KEYWORD_PARAM] == "test"
    assert payload[client.BUYER_PARAM] == "City Hall"
    assert payload[client.ORGANIZATION_PARAM] == "Public Works"
    assert payload[client.DATE_FROM_PARAM] == "15/01/2026"
    assert payload[client.DATE_TO_PARAM] == "30/01/2026"


def test_build_search_payload_with_empty_criteria():
    session = Mock()
    session.state.to_payload = Mock(return_value={"PRADO_PAGESTATE": "test"})
    client = DiscoveryClient(session)
    
    criteria = SearchCriteria()
    payload = client._build_search_payload(criteria)
    
    # Should have default payload but no user-specific fields
    assert client.KEYWORD_PARAM not in payload
    assert client.BUYER_PARAM not in payload


def test_build_row_echo_payload():
    session = Mock()
    client = DiscoveryClient(session)
    
    page = SearchResultPage(tenders=[
        Tender(tender_id="123", organization_acronym="ORG1"),
        Tender(tender_id="456", organization_acronym="ORG2")
    ])
    
    payload = client._build_row_echo_payload(page)
    
    assert payload["ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl1$refCons"] == "123"
    assert payload["ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl1$orgCons"] == "ORG1"
    assert payload["ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl2$refCons"] == "456"
    assert payload["ctl0$CONTENU_PAGE$resultSearch$tableauResultSearch$ctl2$orgCons"] == "ORG2"


def test_build_row_echo_payload_empty():
    session = Mock()
    client = DiscoveryClient(session)
    
    page = SearchResultPage(tenders=[])
    payload = client._build_row_echo_payload(page)
    
    assert payload == {}


@patch("discovery.client.SearchResultParser")
def test_search_success(mock_parser_class):
    session = Mock()
    session.state.to_payload = Mock(return_value={"PRADO_PAGESTATE": "test"})
    session.post = Mock(return_value=Mock(text="<html></html>"))
    
    mock_parser = Mock()
    mock_parser.parse = Mock(return_value=SearchResultPage(
        tenders=[Tender(tender_id="123")],
        current_page=1,
        total_pages=1,
    ))
    mock_parser_class.return_value = mock_parser
    
    client = DiscoveryClient(session)
    criteria = SearchCriteria(keyword="test")
    
    page = client.search(criteria)
    
    assert len(page.tenders) == 1
    session.post.assert_called_once()
    mock_parser.parse.assert_called_once()


@patch("discovery.client.SearchResultParser")
def test_search_raises_on_http_error(mock_parser_class):
    from core.exceptions import HttpRequestError
    
    session = Mock()
    session.state.to_payload = Mock(return_value={"PRADO_PAGESTATE": "test"})
    session.post = Mock(side_effect=HttpRequestError("Request failed"))
    
    client = DiscoveryClient(session)
    criteria = SearchCriteria(keyword="test")
    
    with pytest.raises(SearchExecutionError, match="Search request failed"):
        client.search(criteria)


@patch("discovery.client.SearchResultParser")
def test_next_page_success(mock_parser_class):
    session = Mock()
    session.state.to_payload = Mock(return_value={"PRADO_PAGESTATE": "test"})
    session.post = Mock(return_value=Mock(text="<html></html>"))
    
    mock_parser = Mock()
    mock_parser.parse = Mock(return_value=SearchResultPage(
        tenders=[Tender(tender_id="456")],
        current_page=2,
        total_pages=3,
    ))
    mock_parser_class.return_value = mock_parser
    
    client = DiscoveryClient(session)
    client._paginator._current_page = 1
    client._paginator._total_pages = 3
    client._last_row_echo = {}
    
    current_page = SearchResultPage(tenders=[Tender(tender_id="123")])
    page = client.next_page(current_page)
    
    assert len(page.tenders) == 1
    assert client._paginator.current_page == 2


def test_next_page_raises_when_no_more_pages():
    session = Mock()
    client = DiscoveryClient(session)
    client._paginator._current_page = 5
    client._paginator._total_pages = 5
    
    current_page = SearchResultPage()
    with pytest.raises(PaginationError, match="No more pages available"):
        client.next_page(current_page)


@patch("discovery.client.SearchResultParser")
def test_search_all_multiple_pages(mock_parser_class):
    session = Mock()
    session.state.to_payload = Mock(return_value={"PRADO_PAGESTATE": "test"})
    session.post = Mock(return_value=Mock(text="<html></html>"))
    
    mock_parser = Mock()
    mock_parser.parse = Mock(side_effect=[
        SearchResultPage(tenders=[Tender(tender_id="1")], current_page=1, total_pages=2),
        SearchResultPage(tenders=[Tender(tender_id="2")], current_page=2, total_pages=2)
    ])
    mock_parser_class.return_value = mock_parser
    
    client = DiscoveryClient(session)
    criteria = SearchCriteria(keyword="test")
    
    pages = client.search_all(criteria)
    
    assert len(pages) == 2
    assert pages[0].tenders[0].tender_id == "1"
    assert pages[1].tenders[0].tender_id == "2"
