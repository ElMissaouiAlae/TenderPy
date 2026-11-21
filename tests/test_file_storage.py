"""Tests for document storage adapters."""

from io import BytesIO
from unittest.mock import ANY, Mock

import boto3
import pytest
from botocore.stub import Stubber

from persistence.config import Settings
from persistence.exceptions import ConfigurationError, DocumentNotFoundError
from persistence.file_storage import (
    DocumentStorage,
    LocalDocumentStorage,
    S3DocumentStorage,
)


def test_local_document_storage_saves_binary_documents(tmp_path):
    storage = LocalDocumentStorage(str(tmp_path))
    content = b"PK\x03\x04archive-bytes"

    storage.save_document("tender-123.zip", content)

    assert storage.load_document("tender-123.zip") == content
    storage.delete_document("tender-123.zip")
    assert not (tmp_path / "tender-123.zip").exists()


def test_storage_providers_follow_document_storage_interface():
    local_storage = LocalDocumentStorage("/tmp")
    s3_storage = S3DocumentStorage(
        Settings(
            database_url="postgresql://user:pass@localhost/db", s3_bucket_name="bucket"
        ),
        Mock(),
    )

    assert isinstance(local_storage, DocumentStorage)
    assert isinstance(s3_storage, DocumentStorage)


def test_s3_document_storage_uploads_document_to_configured_bucket():
    settings = Settings(
        database_url="postgresql://user:pass@localhost/db",
        s3_bucket_name="tenders-bucket",
    )
    s3_client = Mock()
    storage = S3DocumentStorage(settings, s3_client)

    storage.save_document("tender-123.zip", b"archive-bytes")

    s3_client.upload_fileobj.assert_called_once_with(
        Fileobj=ANY,
        Bucket="tenders-bucket",
        Key="tender-123.zip",
    )
    uploaded_file = s3_client.upload_fileobj.call_args.kwargs["Fileobj"]
    assert uploaded_file.read() == b"archive-bytes"


def test_s3_document_storage_requires_a_configured_bucket():
    settings = Settings(database_url="postgresql://user:pass@localhost/db")
    storage = S3DocumentStorage(settings, Mock())

    with pytest.raises(ConfigurationError, match="S3_BUCKET_NAME"):
        storage.save_document("tender-123.zip", b"archive-bytes")


def test_s3_document_storage_loads_document_from_configured_bucket():
    settings = Settings(
        database_url="postgresql://user:pass@localhost/db",
        s3_bucket_name="tenders-bucket",
    )
    s3_client = Mock()
    s3_client.get_object.return_value = {"Body": BytesIO(b"archive-bytes")}
    storage = S3DocumentStorage(settings, s3_client)

    content = storage.load_document("tender-123.zip")

    assert content == b"archive-bytes"
    s3_client.get_object.assert_called_once_with(
        Bucket="tenders-bucket",
        Key="tender-123.zip",
    )


def test_s3_document_storage_load_requires_a_configured_bucket():
    settings = Settings(database_url="postgresql://user:pass@localhost/db")
    storage = S3DocumentStorage(settings, Mock())

    with pytest.raises(ConfigurationError, match="S3_BUCKET_NAME"):
        storage.load_document("tender-123.zip")


def test_document_storage_interface_exposes_loading():
    assert hasattr(DocumentStorage, "load_document")


def test_local_document_storage_load_of_a_missing_document_is_not_found(tmp_path):
    storage = LocalDocumentStorage(tmp_path)

    with pytest.raises(DocumentNotFoundError, match="tender-123.zip"):
        storage.load_document("tender-123.zip")


def test_s3_document_storage_load_of_a_missing_key_is_not_found():
    settings = Settings(
        database_url="postgresql://user:pass@localhost/db",
        s3_bucket_name="tenders-bucket",
    )
    s3_client = boto3.client(
        "s3", region_name="eu-west-3", aws_access_key_id="test", aws_secret_access_key="test"
    )
    storage = S3DocumentStorage(settings, s3_client)

    with Stubber(s3_client) as stubber:
        stubber.add_client_error(
            "get_object", service_error_code="NoSuchKey", http_status_code=404
        )
        with pytest.raises(DocumentNotFoundError, match="tender-123.zip"):
            storage.load_document("tender-123.zip")
