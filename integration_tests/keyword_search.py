"""Test search with keyword parameter."""

from core.http import HttpClient
from core.session import SearchSession
from discovery.orchestrator import DiscoveryOrchestrator
from discovery.parser import SearchCriteria

from .config import BASE_URL, logger
from .helpers import log_http_error, log_tenders


def test_keyword_search():
    """Test search with keyword parameter."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Keyword Search")
    logger.info("="*60)

    try:
        with HttpClient(base_url=BASE_URL, timeout=30) as http_client:
            session = SearchSession(http_client)

            # Initialize session with the search page
            init_url = f"{BASE_URL}/index.php?page=entreprise.EntrepriseAdvancedSearch"
            logger.info(f"Initializing session with: {init_url}")
            session.initialize(init_url)
            logger.info(f"Session initialized successfully. PRADO state: {session.state.prado_page_state[:50] if session.state.prado_page_state else 'None'}...")

            orchestrator = DiscoveryOrchestrator(session)

            # Search with keyword
            criteria = SearchCriteria(keyword="construction")
            logger.info(f"Searching with criteria: keyword='construction'")

            tenders = orchestrator.discover(criteria)
            log_tenders(tenders, "keyword_search")

            return tenders
    except Exception as e:
        log_http_error(e, "keyword_search")
        return []
