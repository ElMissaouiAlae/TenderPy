"""Entry point for running the integration test scripts against the real website.

Run with: python -m integration_tests.main
"""

import sys

from .config import BASE_URL, logger
from .date_range_search import test_date_range_search

from .analyze_results import analyze_results  
from .status_transitions import test_status_transitions  


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
