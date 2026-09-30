"""Entry point for running the integration test scripts against the real website.

Run with: python -m integration_tests.main
"""

import sys

from .config import BASE_URL, logger
from .date_range_search import test_date_range_search

# Kept but not invoked here; analyze_results() operates on the JSON files
# test_keyword_search / test_buyer_search / test_combined_search / test_pagination
# produce, so it's likewise not invoked here.
from .analyze_results import analyze_results  # noqa: F401
from .buyer_search import test_buyer_search  # noqa: F401
from .combined_search import test_combined_search  # noqa: F401
from .keyword_search import test_keyword_search  # noqa: F401
from .pagination import test_pagination  # noqa: F401
from .single_page_row_extraction import test_single_page_row_extraction  # noqa: F401
from .status_transitions import test_status_transitions  # noqa: F401


def main():
    """Run integration tests for the crawler."""
    logger.info("Starting integration tests for crawler")
    logger.info(f"Base URL: {BASE_URL}")
    logger.info("Make sure to update BASE_URL with the correct website URL")

    try:
        test_date_range_search()   
        test_status_transitions()
    except Exception:
        logger.error("Integration test failed - see above for details")
        sys.exit(1)

    logger.info("\n" + "="*60)
    logger.info("Integration tests completed successfully")
    logger.info("Check integration_test.log for detailed logs")
    logger.info("="*60)


if __name__ == "__main__":
    main()
