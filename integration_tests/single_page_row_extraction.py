"""Diagnostic test for the parser's per-page row extraction."""

from core.http import HttpClient
from core.session import SearchSession
from discovery.client import DiscoveryClient
from discovery.parser import SearchCriteria

from .config import BASE_URL, logger
from .helpers import log_http_error


def test_single_page_row_extraction():
    """Diagnostic: call DiscoveryClient.search() directly (no pagination) and
    compare the returned tender count against the row count the parser logs,
    to check whether the parser is dropping rows on a single page."""
    logger.info("\n" + "="*60)
    logger.info("TEST: Single Page Row Extraction (no pagination)")
    logger.info("="*60)

    try:
        with HttpClient(base_url=BASE_URL, timeout=30) as http_client:
            session = SearchSession(http_client)

            init_url = f"{BASE_URL}/index.php?page=entreprise.EntrepriseAdvancedSearch"
            logger.info(f"Initializing session with: {init_url}")
            session.initialize(init_url)

            client = DiscoveryClient(session)

            criteria = SearchCriteria(keyword="travaux")
            logger.info("Searching with criteria: keyword='travaux' (single page, no pagination)")

            page = client.search(criteria)

            logger.info(f"page.tenders count: {len(page.tenders)}")
            logger.info(f"page.current_page: {page.current_page}, page.total_pages: {page.total_pages}")
            logger.info(f"page.total_results: {page.total_results}")

            return page
    except Exception as e:
        log_http_error(e, "single_page_row_extraction")
        return None
