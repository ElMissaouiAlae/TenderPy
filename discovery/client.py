"""Playwright client for discovering tenders from the procurement site."""

from __future__ import annotations

from datetime import date

from playwright.sync_api import Playwright

from core.models import Tender

from .parser import SearchResultParser


class DiscoveryClient:
    """Execute date-filtered tender searches and follow result pagination."""

    START_DATE_SELECTOR = (
        'input[name="ctl0$CONTENU_PAGE$AdvancedSearch$dateMiseEnLigneCalculeStart"]'
    )
    END_DATE_SELECTOR = (
        'input[name="ctl0$CONTENU_PAGE$AdvancedSearch$dateMiseEnLigneCalculeEnd"]'
    )
    SEARCH_BUTTON_SELECTOR = (
        'input[name="ctl0$CONTENU_PAGE$AdvancedSearch$lancerRecherche"]'
    )
    NEXT_PAGE_SELECTOR = "a#ctl0_CONTENU_PAGE_resultSearch_PagerBottom_ctl2"

    def __init__(self, url: str, playwright: Playwright) -> None:
        """Initialize the client with a search URL and Playwright instance."""
        self._url = url
        self._playwright = playwright

    def search(self, start_date: date, end_date: date) -> list[Tender]:
        """Search for tenders and return results from every result page."""
        browser = self._playwright.webkit.launch()
        context = browser.new_context()

        try:
            page = context.new_page()
            page.goto(self._url, wait_until="networkidle")
            response = self._submit_search(page, start_date, end_date)
            parser = SearchResultParser()
            all_tenders: list[Tender] = []

            while True:
                result_page = parser.parse(response.text())
                all_tenders.extend(result_page.tenders)

                if not self._has_next_page(result_page.current_page, result_page.total_pages):
                    return all_tenders

                with page.expect_response(self._response_predicate) as response_info:
                    page.locator(self.NEXT_PAGE_SELECTOR).click()
                response = response_info.value
        finally:
            context.close()
            browser.close()

    def _submit_search(self, page: object, start_date: date, end_date: date) -> object:
        """Fill the date filters and submit the initial search request."""
        with page.expect_response(self._response_predicate) as response_info:
            page.locator(self.START_DATE_SELECTOR).fill(start_date.strftime("%d/%m/%Y"))
            page.locator(self.END_DATE_SELECTOR).fill(end_date.strftime("%d/%m/%Y"))
            page.locator(self.SEARCH_BUTTON_SELECTOR).click(timeout=0)
        return response_info.value

    def _response_predicate(self, response: object) -> bool:
        """Return whether a response is the successful search postback."""
        return (
            response.url == self._url
            and response.status == 200
            and response.request.method == "POST"
        )

    @staticmethod
    def _has_next_page(current_page: int | None, total_pages: int | None) -> bool:
        """Return whether pagination metadata indicates another result page."""
        return (
            current_page is not None
            and total_pages is not None
            and current_page < total_pages
        )
