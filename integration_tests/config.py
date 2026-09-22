"""Shared logging setup and configuration for the integration test scripts."""

import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integration_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration 
BASE_URL = "https://www.marchespublics.gov.ma"  

# Local directory where downloaded DCE archives are saved during integration tests
DOWNLOAD_DIR = Path("integration_test_downloads")

# Delay (seconds) between requests to avoid tripping the site's rate limiting
# during bursts of sequential DCE downloads
REQUEST_DELAY = 1.5
