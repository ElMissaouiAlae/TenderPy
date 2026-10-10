"""Entry point for running the integration test scripts against the real website.

Run with: python -m integration_tests.main
"""

import sys

from .config import BASE_URL, logger
from .date_range_search import test_date_range_search
from .indexing_selection import test_indexing_selection


from .status_transitions import test_status_transitions
from .vector_store_replace import test_vector_store_replace
from .vector_store_roundtrip import test_vector_store_roundtrip
from .vector_store_scoped_search import test_vector_store_scoped_search


def main():
    """Run integration tests for the crawler."""
    logger.info("Starting integration tests for crawler")
    logger.info(f"Base URL: {BASE_URL}")
    logger.info("Make sure to update BASE_URL with the correct website URL")

    try:
        test_date_range_search()   
        test_status_transitions()
        test_indexing_selection()
        test_vector_store_roundtrip()
        test_vector_store_replace()
        test_vector_store_scoped_search()
    except Exception:
        logger.error("Integration test failed - see above for details")
        sys.exit(1)

    logger.info("\n" + "="*60)
    logger.info("Integration tests completed successfully")
    logger.info("Check integration_test.log for detailed logs")
    logger.info("="*60)


if __name__ == "__main__":
    main()
