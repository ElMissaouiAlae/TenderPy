"""Local and S3-backed storage for downloaded documents."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import boto3

from persistence.config import Settings
from persistence.exceptions import ConfigurationError


@runtime_checkable
class DocumentStorage(Protocol):
    """Storage interface used by document-producing modules."""

    def save_document(self, document_name: str, content: bytes) -> None:
        """Save document bytes under the supplied document name.

        Args:
            document_name: Name or object key to store the document under.
            content: Document data to persist.
        """


class LocalDocumentStorage:
    """Store documents on the local filesystem.

    Attributes:
        storage_path: Directory where local documents are saved.
    """

    def __init__(self, storage_path: str | Path) -> None:
        """Initialize local storage.

        Args:
            storage_path: Directory where documents will be stored.
        """
        self.storage_path = Path(storage_path)

    def save_document(self, document_name: str, content: bytes) -> None:
        """Save document bytes to the local filesystem.

        Args:
            document_name: File name to store the document under.
            content: Document data to persist.
        """
        file_path = self.storage_path / document_name
        with file_path.open("wb") as file:
            file.write(content)

    def load_document(self, document_name: str) -> bytes:
        """Load document bytes from local storage.

        Args:
            document_name: File name of the document to load.

        Returns:
            The stored document bytes.
        """
        file_path = self.storage_path / document_name
        with file_path.open("rb") as file:
            return file.read()

    def delete_document(self, document_name: str) -> None:
        """Delete a document from local storage.

        Args:
            document_name: File name of the document to delete.
        """
        file_path = self.storage_path / document_name
        file_path.unlink()


class S3DocumentStorage:
    """Store downloaded documents in the S3 bucket from application settings.

    Attributes:
        settings: Application settings containing the S3 bucket name.
    """

    def __init__(self, settings: Settings, s3_client: Any | None = None) -> None:
        """Initialize S3 storage with settings and an optional client.

        Args:
            settings: Settings used to select the destination S3 bucket.
            s3_client: Optional S3-compatible client, primarily for testing.
        """
        self._settings = settings
        self._s3 = s3_client if s3_client is not None else boto3.client("s3")

    def save_document(self, document_name: str, content: bytes) -> None:
        """Upload document bytes to the configured S3 bucket.

        Args:
            document_name: S3 object key to store the document under.
            content: Document data to upload.

        Raises:
            ConfigurationError: If no S3 bucket is configured.
        """
        bucket_name = self._settings.s3_bucket_name
        if not bucket_name:
            raise ConfigurationError("S3_BUCKET_NAME environment variable is required")

        self._s3.upload_fileobj(
            Fileobj=BytesIO(content),
            Bucket=bucket_name,
            Key=document_name,
        )
