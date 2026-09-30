"""Tests for discovery.paginator module."""

import pytest

from core.exceptions import PaginationError
from discovery.paginator import Paginator, PageParams
from discovery.parser import SearchResultPage


def test_page_params_creation():
    params = PageParams(current_page=1,total_pages=5)
    assert params.current_page == 1
    assert params.total_pages == 5


def test_page_params_without_total_pages():
    params = PageParams(current_page=1)
    assert params.current_page == 1
    assert params.total_pages is None


def test_paginator_initialization():
    paginator = Paginator()
    assert paginator.current_page == 0
    assert paginator.total_pages is None


def test_paginator_has_next_page_when_total_unknown():
    paginator = Paginator()
    assert paginator.has_next_page() is True


def test_paginator_has_next_page_when_more_pages_exist():
    paginator = Paginator()
    paginator._current_page = 1
    paginator._total_pages = 5
    assert paginator.has_next_page() is True


def test_paginator_has_next_page_when_on_last_page():
    paginator = Paginator()
    paginator._current_page = 5
    paginator._total_pages = 5
    assert paginator.has_next_page() is False


def test_paginator_set_total_pages():
    paginator = Paginator()
    paginator.set_total_pages(10)
    assert paginator.total_pages == 10


def test_paginator_sync_from_page():
    paginator = Paginator()
    page = SearchResultPage(
        current_page=2,
        total_pages=10,
        total_results=150
    )
    
    paginator.sync_from_page(page)
    
    assert paginator.current_page == 2
    assert paginator.total_pages == 10


def test_paginator_sync_from_page_with_none_values():
    paginator = Paginator()
    page = SearchResultPage()
    
    paginator.sync_from_page(page)
    
    assert paginator.current_page == 0  # default unchanged
    assert paginator.total_pages is None


def test_paginator_next_page_payload():
    paginator = Paginator()
    paginator._page_number = 0
    paginator._total_pages = 5
    
    payload = paginator.next_page_payload()
    
    assert payload["ctl0$CONTENU_PAGE$resultSearch$numPageTop"] == "1"
    assert payload["ctl0$CONTENU_PAGE$resultSearch$listePageSizeTop"] == "10"
    assert payload["ctl0$CONTENU_PAGE$resultSearch$numPageBottom"] == "1"
    assert payload["ctl0$CONTENU_PAGE$resultSearch$listePageSizeBottom"] == "10"


def test_paginator_next_page_payload_increments_page():
    paginator = Paginator()
    paginator._page_number = 0
    paginator._total_pages = 5
    
    paginator.next_page_payload()
    assert paginator._page_number == 1


def test_paginator_next_page_payload_raises_when_no_next_page():
    paginator = Paginator()
    paginator._current_page = 5
    paginator._total_pages = 5
    
    with pytest.raises(PaginationError, match="No more pages available"):
        paginator.next_page_payload()


def test_paginator_reset():
    paginator = Paginator()
    paginator._current_page = 5
    paginator._total_pages = 10
    
    paginator.reset()
    
    assert paginator.current_page == 0
    assert paginator.total_pages is None
    assert paginator._page_number == 0