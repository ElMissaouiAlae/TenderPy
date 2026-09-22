"""Download the DCE (Dossier de Consultation des Entreprises) archive."""

from __future__ import annotations

import os
from io import BytesIO
from urllib.parse import urlencode

import boto3

from core.http import HttpClient


class TenderDownloader:
    """Fetch a tender's DCE archive with HTTP and upload it to S3."""

    DOWNLOAD_PAGE = "entreprise.EntrepriseDownloadCompleteDce"

    def __init__(
        self,
        http_client: HttpClient,
        tender_id: str,
        organization_acronym: str,
    ) -> None:
        """Initialize the downloader with an HTTP client and tender identity."""
        self._http_client = http_client
        self._tender_id = tender_id
        self._organization_acronym = organization_acronym
        self._s3 = boto3.client("s3")

    @property
    def download_url(self) -> str:
        """Return the encoded archive endpoint URL."""
        query = urlencode({
            "page": self.DOWNLOAD_PAGE,
            "reference": self._tender_id,
            "orgAcronym": self._organization_acronym,
        })
        return f"?{query}"

    @property
    def filename(self) -> str:
        """Return the S3 object name for the tender archive."""
        return f"{self._tender_id}_{self._organization_acronym}.zip"

    def download(self) -> None:
        """Download the DCE archive and upload it to S3."""
        response = self._http_client.get(self.download_url)
        response.raise_for_status()

        bucket_name = os.environ.get("S3_BUCKET_NAME")
        if not bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable is not set")

        self._s3.upload_fileobj(
            Fileobj=BytesIO(response.content),
            Bucket=bucket_name,
            Key=self.filename,
        )
