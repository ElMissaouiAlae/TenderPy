"""Upload a tender's downloaded DCE (Dossier de Consultation des Entreprises) zip archive to S3."""

from __future__ import annotations

from pathlib import Path


class TenderUploader:
    """Push a tender's downloaded DCE zip archive to S3 via a single put_object call."""

    def __init__(
        self,
        s3_client,
        tender_id: str,
        organization_acronym: str,
        bucket_name: str,
    ) -> None:
        """Initialize the uploader with an S3 client, the target tender's identity, and the destination bucket."""
        self._s3_client = s3_client
        self._tender_id = tender_id
        self._organization_acronym = organization_acronym
        self._bucket_name = bucket_name

    @property
    def object_key(self) -> str:
        """Build the deterministic S3 object key for this tender's archive.

        Mirrors TenderDownloader.download_url in deriving from the same two
        values (tender_id, organization_acronym), and matches the local
        filename convention already used when archives are written to disk.
        """
        return f"{self._tender_id}_{self._organization_acronym}.zip"

    def upload(self, file_path: Path | str) -> None:
        """Upload the local DCE archive at file_path to S3 under object_key."""
        with open(file_path, "rb") as file_obj:
            self._s3_client.put_object(
                Bucket=self._bucket_name,
                Key=self.object_key,
                Body=file_obj.read(),
            )
