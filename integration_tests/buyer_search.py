"""Test search with buyer parameter."""

from core.http import HttpClient
from core.session import SearchSession
from discovery.orchestrator import DiscoveryOrchestrator
from discovery.parser import SearchCriteria

from .config import BASE_URL, logger
from .helpers import log_http_error, log_tenders


def test_buyer_search():
    """Test search with buyer parameter."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Buyer Search")
    logger.info("="*60)

    try:
        with HttpClient(base_url=BASE_URL, timeout=30) as http_client:
            session = SearchSession(http_client)

            # Initialize session
            init_url = f"{BASE_URL}/index.php?page=entreprise.EntrepriseAdvancedSearch"
            logger.info(f"Initializing session with: {init_url}")
            session.initialize(init_url)
            logger.info(f"Session initialized successfully. PRADO state: {session.state.prado_page_state[:50] if session.state.prado_page_state else 'None'}...")

            orchestrator = DiscoveryOrchestrator(session)

            # Search with buyer
            criteria = SearchCriteria(buyer="Commune")
            logger.info(f"Searching with criteria: buyer='Commune'")

            tenders = orchestrator.discover(criteria)
            log_tenders(tenders, "buyer_search")

            return tenders
    except Exception as e:
        log_http_error(e, "buyer_search")
        return []
