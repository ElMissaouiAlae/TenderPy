"""Tests for the uploader module."""

from unittest.mock import Mock

from uploader import TenderUploader


def test_tender_uploader_initialization():
    s3_client = Mock()
    uploader = TenderUploader(s3_client, "1032737", "j0w", "tenders-bucket")

    assert uploader._s3_client is s3_client
    assert uploader._tender_id == "1032737"
    assert uploader._organization_acronym == "j0w"
    assert uploader._bucket_name == "tenders-bucket"


def test_object_key_builds_expected_key():
    s3_client = Mock()
    uploader = TenderUploader(s3_client, "1032737", "j0w", "tenders-bucket")

    assert uploader.object_key == "1032737_j0w.zip"


def test_upload_calls_s3_client_put_object_with_bucket_key_and_body(tmp_path):
    s3_client = Mock()
    archive_path = tmp_path / "archive.zip"
    archive_path.write_bytes(b"PK\x03\x04fake-zip-bytes")

    uploader = TenderUploader(s3_client, "1032737", "j0w", "tenders-bucket")
    uploader.upload(archive_path)

    s3_client.put_object.assert_called_once_with(
        Bucket="tenders-bucket",
        Key="1032737_j0w.zip",
        Body=b"PK\x03\x04fake-zip-bytes",
    )
