"""Test date-range discovery and DCE persistence."""

from datetime import UTC, datetime, timedelta

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from core.exceptions import HttpRequestError
from core.http import HttpClient
from core.session import SearchSession
from discovery.orchestrator import DiscoveryOrchestrator
from downloader import TenderDownloader
from persistence import Database, Settings, TenderRepository, TenderStatus

from .config import BASE_URL, REQUEST_DELAY, logger
from .helpers import log_http_error

BATCH_SIZE = 5


def test_date_range_search():
    """Discover tenders with Playwright and download a verification batch."""
    database = None
    try:
        database = Database(Settings.from_env())
        repository = TenderRepository(database)
        search_url = (
            f"{BASE_URL}/index.php?"
            "page=entreprise.EntrepriseAdvancedSearch&searchAnnCons"
        )
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=2)

        with (
            HttpClient(base_url=BASE_URL, timeout=30, request_delay=REQUEST_DELAY) as http_client,
            sync_playwright() as playwright,
        ):
            SearchSession(http_client).initialize(search_url)
            orchestrator = DiscoveryOrchestrator(search_url, playwright, repository)
            tenders = orchestrator.discover(start_date, end_date)
            logger.info("Discovered %d tenders", len(tenders))

            verified = 0
            downloaded = 0
            for tender in tenders:
                if verified >= BATCH_SIZE:
                    break
                if not tender.tender_id or not tender.organization_acronym:
                    continue
                if not repository.exists(tender.tender_id, tender.organization_acronym):
                    continue
                verified += 1
                repository.update_status(
                    tender.tender_id, tender.organization_acronym, TenderStatus.DOWNLOADING
                )
                try:
                    TenderDownloader(
                        http_client,
                        tender.tender_id,
                        tender.organization_acronym,
                    ).download()
                    downloaded += 1
                    repository.update_status(
                        tender.tender_id, tender.organization_acronym, TenderStatus.DOWNLOADED
                    )
                except (HttpRequestError, PlaywrightError) as exc:
                    log_http_error(exc, f"download DCE for {tender.tender_id}")
                    repository.update_status(
                        tender.tender_id,
                        tender.organization_acronym,
                        TenderStatus.FAILED,
                        last_status=TenderStatus.DOWNLOADING,
                    )

            logger.info("Verified %d tenders; downloaded %d archives", verified, downloaded)
            return tenders
    except Exception as exc:
        log_http_error(exc, "date_range_search")
        raise
    finally:
        if database is not None:
            database.close()
