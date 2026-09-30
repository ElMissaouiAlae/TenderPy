"""Download the DCE (Dossier de Consultation des Entreprises) zip archive for a tender."""

from __future__ import annotations

from urllib.parse import urlencode

from core.http import HttpClient
from persistence.file_storage import DocumentStorage


class TenderDownloader:
    """Fetch a tender's DCE archive and pass it to document storage."""
    DOWNLOAD_PAGE = "entreprise.EntrepriseDownloadCompleteDce"

    def __init__(
        self,
        http_client: HttpClient,
        tender_id: str,
        organization_acronym: str,
        document_storage: DocumentStorage,
    ) -> None:
        """Initialize the downloader with its HTTP and storage collaborators.

        Args:
            http_client: Client used to fetch the DCE archive.
            tender_id: Identifier used to locate the tender archive.
            organization_acronym: Organization owning the tender.
            document_storage: Storage adapter used to persist archive bytes.
        """
        self._http_client = http_client
        self._tender_id = tender_id
        self._organization_acronym = organization_acronym
        self._document_storage = document_storage

    @property
    def download_url(self) -> str:
        query = urlencode({
            "page": self.DOWNLOAD_PAGE,
            "reference": self._tender_id,
            "orgAcronym": self._organization_acronym,
        })
        return f"?{query}"

    @property
    def filename(self) -> str:
        return f"{self._tender_id}_{self._organization_acronym}.zip"

    def download(self) -> None:
        """Download the DCE archive and store it through the configured adapter."""

        response = self._http_client.get(self.download_url)
        response.raise_for_status()
        self._document_storage.save_document(self.filename, response.content)

