"""Test pagination functionality."""

import json
from datetime import datetime
from pathlib import Path

from core.http import HttpClient
from core.session import SearchSession
from discovery.orchestrator import DiscoveryOrchestrator
from discovery.parser import SearchCriteria

from .config import BASE_URL, logger
from .helpers import log_http_error, tender_to_dict


def test_pagination():
    """Test pagination functionality."""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: Pagination")
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

            # Search with a broad criteria to get multiple pages
            criteria = SearchCriteria(keyword="services")
            logger.info(f"Testing pagination with keyword='services'")

            # Use discover_paginated to get pages separately
            pages = orchestrator.discover_paginated(criteria)

            logger.info(f"Found {len(pages)} pages")

            total_tenders = 0
            for i, page_tenders in enumerate(pages, 1):
                logger.info(f"Page {i}: {len(page_tenders)} tenders")
                total_tenders += len(page_tenders)

            logger.info(f"Total tenders across all pages: {total_tenders}")

            # Save pagination results
            output_dir = Path('test_results')
            output_dir.mkdir(exist_ok=True)

            pagination_file = output_dir / f'pagination_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(pagination_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'total_pages': len(pages),
                    'total_tenders': total_tenders,
                    'tenders_per_page': [len(page) for page in pages],
                    'all_tenders': [tender_to_dict(t) for page in pages for t in page]
                }, f, indent=2, ensure_ascii=False)

            logger.info(f"Pagination results saved to {pagination_file}")

            return pages
    except Exception as e:
        log_http_error(e, "pagination")
        return []
