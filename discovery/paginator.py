"""Pagination logic for discovery searches."""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import PaginationError
from discovery.parser import SearchResultPage


@dataclass
class PageParams:
    """Represents pagination parameters for a POST request."""

    current_page: int
    total_pages: int | None = None


class Paginator:
    """Manage pagination state and generate next page payloads."""

    PAGE_NUMBER_TOP_PARAM = "ctl0$CONTENU_PAGE$resultSearch$numPageTop" 
    PAGE_NUMBER_BOTTOM_PARAM = "ctl0$CONTENU_PAGE$resultSearch$numPageBottom"

    # Safety cap: if the site's HTML never yields a parseable total-pages count,
    # has_next_page() would otherwise assume more pages exist forever.
    MAX_PAGES_WITHOUT_TOTAL = 1000

    def __init__(self) -> None:
        """Initialize paginator to a pre-search state.

        All fields are placeholders until the first `sync_from_page()` call,
        which is the sole source of truth for pagination state — see
        `Client.search()`.
        """
        self._current_page = 0
        self._page_number = 0
        self._total_pages: int | None = None

    def has_next_page(self) -> bool:
        """Check if another page exists."""
        if self._total_pages is None:
            # If total pages unknown, assume more pages exist, but bound it so a
            # parsing regression can't spin the crawler forever.
            return self._current_page < self.MAX_PAGES_WITHOUT_TOTAL
        return self._current_page < self._total_pages

    def set_total_pages(self, total_pages: int | None) -> None:
        """Update total pages from search results."""
        self._total_pages = total_pages

    @property
    def current_page(self) -> int:
        """Get the current page number."""
        return self._current_page

    @property
    def total_pages(self) -> int | None:
        """Get the total number of pages."""
        return self._total_pages

    def sync_from_page(self, page: SearchResultPage) -> None:
        """Reconcile paginator state with the server's authoritative response.

        This is the ONLY path by which current_page/page_size are updated
        post-request. Called after every request, first page or not.
        """
        if page.current_page is not None:
            self._current_page = page.current_page
        self.set_total_pages(page.total_pages)

    def next_page_payload(self) -> dict[str, str]:
        """Generate POST payload parameters for the next page."""
        if not self.has_next_page():
            raise PaginationError("No more pages available")

        self._page_number += 1

        return {
            self.PAGE_NUMBER_TOP_PARAM: str(self._page_number),
            "ctl0$CONTENU_PAGE$resultSearch$listePageSizeTop" : '10',
            self.PAGE_NUMBER_BOTTOM_PARAM: str(self._page_number),
            "ctl0$CONTENU_PAGE$resultSearch$listePageSizeBottom" : '10',
        }

    def reset(self) -> None:
        """Reset pagination to the first page."""
        self._current_page = 0
        self._total_pages = None
        self._page_number = 0
