"""Tests for the Playwright-backed discovery client."""

from datetime import date
from unittest.mock import Mock

from core.models import Tender
from discovery.client import DiscoveryClient
from discovery.parser import SearchResultPage

URL = "https://example.test/search"


def _mocks() -> tuple[Mock, Mock, Mock, Mock]:
    playwright = Mock()
    browser = playwright.webkit.launch.return_value
    context = browser.new_context.return_value
    page = context.new_page.return_value
    return playwright, browser, context, page


def test_search_submits_dates_and_collects_pages(monkeypatch):
    playwright, browser, context, page = _mocks()
    responses = [Mock(text=Mock(return_value="first")), Mock(text=Mock(return_value="last"))]
    contexts = []
    for response in responses:
        response_context = Mock()
        response_context.__enter__ = Mock(return_value=response_context)
        response_context.__exit__ = Mock(return_value=False)
        response_context.value = response
        contexts.append(response_context)
    page.expect_response.side_effect = contexts
    parser = Mock()
    parser.parse.side_effect = [
        SearchResultPage(tenders=[Tender(tender_id="1")], current_page=1, total_pages=2),
        SearchResultPage(tenders=[Tender(tender_id="2")], current_page=2, total_pages=2),
    ]
    monkeypatch.setattr("discovery.client.SearchResultParser", Mock(return_value=parser))

    client = DiscoveryClient(URL, playwright)
    result = client.search(date(2026, 9, 19), date(2026, 9, 20))

    assert [tender.tender_id for tender in result] == ["1", "2"]
    browser.close.assert_called_once_with()
    context.close.assert_called_once_with()
