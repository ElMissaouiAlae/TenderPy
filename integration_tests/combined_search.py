"""Test search with multiple parameters combined."""

from datetime import date, timedelta

from core.http import HttpClient
from core.session import SearchSession
from discovery.orchestrator import DiscoveryOrchestrator
from discovery.parser import SearchCriteria

from .config import BASE_URL, logger
from .helpers import log_http_error, log_tenders


def test_combined_search():
    """Test search with multiple parameters combined."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Combined Search")
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

            # Search with multiple parameters
            end_date = date.today()
            start_date = end_date - timedelta(days=7)

            criteria = SearchCriteria(
                keyword="travaux",
                publication_date_from=start_date,
                publication_date_to=end_date
            )
            logger.info(f"Searching with combined criteria: keyword='travaux', date range: {start_date} to {end_date}")

            tenders = orchestrator.discover(criteria)
            log_tenders(tenders, "combined_search")

            return tenders
    except Exception as e:
        log_http_error(e, "combined_search")
        return []
