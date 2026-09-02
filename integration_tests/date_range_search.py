"""Test search with date range parameters, persisting directly to Postgres."""

from datetime import date, timedelta

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from core.exceptions import HttpRequestError
from core.http import HttpClient
from core.session import SearchSession
from discovery.orchestrator import DiscoveryOrchestrator
from discovery.parser import SearchCriteria
from downloader import TenderDownloader
from persistence import Database, Settings, TenderRepository, TenderStatus
from uploader import TenderUploader

from .config import BASE_URL, DOWNLOAD_DIR, REQUEST_DELAY, logger
from .helpers import log_http_error


def test_date_range_search():
    """Test search with date range parameters (last 2 days), persisting directly to Postgres.

    Unlike the other test_* functions here, this one doesn't dump results to a
    JSON file - discover() persists to the 'tender_records' table as a side
    effect, and this then reads back from the database to confirm it landed.

    Raises on any failure (connection errors, write failures, missing
    persisted records) instead of swallowing them - callers must not treat
    a caught exception here as a passing run.
    """
    logger.info("\n" + "="*60)
    logger.info("TEST: Date Range Search (persists to Postgres)")
    logger.info("="*60)

    database = None
    try:
        settings = Settings.from_env()
        database = Database(settings)
        repository = TenderRepository(database)

        bucket_name, region = settings.require_s3()
        s3_client = boto3.client("s3", region_name=region)

        with HttpClient(base_url=BASE_URL, timeout=30, request_delay=REQUEST_DELAY) as http_client:
            session = SearchSession(http_client)

            # Initialize session
            init_url = f"{BASE_URL}/index.php?page=entreprise.EntrepriseAdvancedSearch"
            logger.info(f"Initializing session with: {init_url}")
            session.initialize(init_url)
            logger.info(f"Session initialized successfully. PRADO state: {session.state.prado_page_state[:50] if session.state.prado_page_state else 'None'}...")

            orchestrator = DiscoveryOrchestrator(session, repository)

            # Search with date range (last 2 days)
            end_date = date.today()
            start_date = end_date - timedelta(days=2)

            criteria = SearchCriteria(
                publication_date_from=start_date,
                publication_date_to=end_date
            )
            logger.info(f"Searching with date range: {start_date} to {end_date}")

            tenders = orchestrator.discover(criteria)
            logger.info(f"Discovered {len(tenders)} tenders - persisted to 'tender_records' as a side effect of discover()")

            # Verify persistence by reading each discovered tender back from the database,
            # and download its DCE archive to the local downloads directory
            DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

            verified = 0
            downloaded = 0
            for tender in tenders:
                if not tender.tender_id or not tender.organization_acronym:
                    continue
                if repository.exists(tender.tender_id, tender.organization_acronym):
                    verified += 1
                else:
                    logger.warning(
                        f"Tender {tender.tender_id}/{tender.organization_acronym} "
                        "was not found in the database after discover()"
                    )
                    continue

                downloader = TenderDownloader(
                    http_client, tender.tender_id, tender.organization_acronym
                )
                repository.update_status(
                    tender.tender_id, tender.organization_acronym, TenderStatus.DOWNLOADING
                )
                try:
                    response = downloader.download()
                    dce_path = DOWNLOAD_DIR / f"{tender.tender_id}_{tender.organization_acronym}.zip"
                    dce_path.write_bytes(response.content)
                    downloaded += 1
                    logger.info(f"Downloaded DCE for {tender.tender_id}/{tender.organization_acronym} to {dce_path}")
                except HttpRequestError as exc:
                    log_http_error(
                        exc, f"download DCE for {tender.tender_id}/{tender.organization_acronym}"
                    )
                    repository.update_status(
                        tender.tender_id,
                        tender.organization_acronym,
                        TenderStatus.FAILED,
                        last_status=TenderStatus.DOWNLOADING,
                    )
                    continue
                repository.update_status(
                    tender.tender_id, tender.organization_acronym, TenderStatus.DOWNLOADED
                )

                uploader = TenderUploader(
                    s3_client, tender.tender_id, tender.organization_acronym, bucket_name
                )
                repository.update_status(
                    tender.tender_id, tender.organization_acronym, TenderStatus.UPLOADING
                )
                try:
                    uploader.upload(dce_path)
                    logger.info(f"Uploaded DCE for {tender.tender_id}/{tender.organization_acronym} to S3")
                except (ClientError, BotoCoreError) as exc:
                    log_http_error(
                        exc, f"upload DCE for {tender.tender_id}/{tender.organization_acronym}"
                    )
                    repository.update_status(
                        tender.tender_id,
                        tender.organization_acronym,
                        TenderStatus.FAILED,
                        last_status=TenderStatus.UPLOADING,
                    )
                    continue
                repository.update_status(
                    tender.tender_id, tender.organization_acronym, TenderStatus.UPLOADED
                )
                repository.update_status(
                    tender.tender_id, tender.organization_acronym, TenderStatus.INDEXED
                )
            logger.info(f"Verified {verified}/{len(tenders)} discovered tenders are present in the database")
            logger.info(f"Downloaded {downloaded}/{len(tenders)} DCE archives to {DOWNLOAD_DIR}")
            if verified != len(tenders):
                raise AssertionError(
                    f"Persistence verification failed: {verified}/{len(tenders)} records found"
                )

            for i, tender in enumerate(tenders[:5], 1):
                logger.info(f"Tender {i}:")
                logger.info(f"  ID: {tender.tender_id}")
                logger.info(f"  Organization: {tender.organization_acronym}")
                logger.info(f"  Object: {tender.tender_object}")
                logger.info(f"  Buyer: {tender.public_buyer}")
                logger.info(f"  Publication Date: {tender.publication_date}")

            if len(tenders) > 5:
                logger.info(f"... and {len(tenders) - 5} more tenders")

            return tenders
    except Exception as exc:
        log_http_error(exc, "date_range_search")
        raise
    finally:
        if database is not None:
            database.close()
