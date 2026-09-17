"""Tests for the downloader module."""

from unittest.mock import ANY, Mock, patch

from downloader import TenderDownloader


def test_tender_downloader_initialization():
    http_client = Mock()
    downloader = TenderDownloader(http_client, "1032737", "j0w")

    assert downloader._http_client is http_client
    assert downloader._tender_id == "1032737"
    assert downloader._organization_acronym == "j0w"


def test_download_url_builds_expected_query_string():
    http_client = Mock()
    downloader = TenderDownloader(http_client, "1032737", "j0w")

    assert downloader.download_url == (
        "?page=entreprise.EntrepriseDownloadCompleteDce"
        "&reference=1032737&orgAcronym=j0w"
    )


def test_download_url_encodes_reserved_characters():
    http_client = Mock()
    downloader = TenderDownloader(http_client, "A&B", "x=y z")

    assert downloader.download_url == (
        "?page=entreprise.EntrepriseDownloadCompleteDce"
        "&reference=A%26B&orgAcronym=x%3Dy+z"
    )


def test_download_gets_archive_and_uploads_it_to_s3():
    http_client = Mock()
    mock_response = Mock(content=b"PK\x03\x04fake-zip-bytes")
    http_client.get = Mock(return_value=mock_response)
    s3_client = Mock()

    with patch("downloader.boto3.client", return_value=s3_client), patch.dict(
        "downloader.os.environ", {"S3_BUCKET_NAME": "test-bucket"}
    ):
        downloader = TenderDownloader(http_client, "1032737", "j0w")
        downloader.download()

    http_client.get.assert_called_once_with(downloader.download_url)
    mock_response.raise_for_status.assert_called_once_with()
    s3_client.upload_fileobj.assert_called_once_with(
        Fileobj=ANY,
        Bucket="test-bucket",
        Key=downloader.filename,
    )
    uploaded_file = s3_client.upload_fileobj.call_args.kwargs["Fileobj"]
    assert uploaded_file.read() == b"PK\x03\x04fake-zip-bytes"

