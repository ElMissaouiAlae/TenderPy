"""Shared helpers used across the integration test scripts."""

import json
from datetime import datetime
from pathlib import Path

from .config import logger


def tender_to_dict(tender):
    """Convert Tender object to dictionary for JSON serialization."""
    return {
        'tender_id': tender.tender_id,
        'organization_acronym': tender.organization_acronym,
        'procurement_type': tender.procurement_type,
        'category': tender.category,
        'publication_date': tender.publication_date.isoformat() if tender.publication_date else None,
        'reference_number': tender.reference_number,
        'tender_object': tender.tender_object,
        'public_buyer': tender.public_buyer,
        'location': tender.location,
        'deadline': tender.deadline.isoformat() if tender.deadline else None,
    }


def log_tenders(tenders, test_name):
    """Log tender details to both console and file."""
    logger.info(f"=== {test_name} - Found {len(tenders)} tenders ===")

    # Create output directory if it doesn't exist
    output_dir = Path('test_results')
    output_dir.mkdir(exist_ok=True)

    # Save to JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # noqa: DTZ005 - local time for filenames
    output_file = output_dir / f'{test_name}_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([tender_to_dict(t) for t in tenders], f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to {output_file}")

    # Log summary
    for i, tender in enumerate(tenders[:5], 1):  # Log first 5 tenders
        logger.info(f"Tender {i}:")
        logger.info(f"  ID: {tender.tender_id}")
        logger.info(f"  Organization: {tender.organization_acronym}")
        logger.info(f"  Object: {tender.tender_object}")
        logger.info(f"  Buyer: {tender.public_buyer}")
        logger.info(f"  Publication Date: {tender.publication_date}")

    if len(tenders) > 5:
        logger.info(f"... and {len(tenders) - 5} more tenders")


def log_http_error(error, context=""):
    """Log detailed HTTP error information including response details."""
    logger.error(f"HTTP Error in {context}")
    logger.error(f"Error type: {type(error).__name__}")
    logger.error(f"Error message: {error!s}")

    # Try to extract response details if available
    if hasattr(error, 'args') and error.args:
        for arg in error.args:
            if isinstance(arg, str):
                logger.error(f"Error details: {arg}")

    # Try to access response object if it's a requests-related error
    if hasattr(error, '__cause__') and error.__cause__:
        cause = error.__cause__
        logger.error(f"Cause: {type(cause).__name__} - {cause!s}")

        # If it's a requests.Response, log headers and body
        if hasattr(cause, 'response') and cause.response is not None:
            response = cause.response
            logger.error(f"HTTP Status Code: {response.status_code}")
            logger.error("Response Headers:")
            for key, value in response.headers.items():
                logger.error(f"  {key}: {value}")

            # Log response body (truncated if too long)
            body = response.text
            if body:
                logger.error("Response Body (first 1000 chars):")
                logger.error(body[:1000])
                if len(body) > 1000:
                    logger.error(f"... (body truncated, total length: {len(body)} chars)")

    # Log the full traceback
    logger.error("Full traceback:", exc_info=True)
