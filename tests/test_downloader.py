"""Tests for the HTTP-backed downloader."""

from unittest.mock import Mock

from downloader import TenderDownloader


def test_tender_downloader_initialization():
    http_client = Mock()
    document_storage = Mock()
    downloader = TenderDownloader(http_client, "1032737", "j0w", document_storage)

    assert downloader._http_client is http_client
    assert downloader._document_storage is document_storage
    assert downloader._tender_id == "1032737"
    assert downloader._organization_acronym == "j0w"


def test_download_url_builds_expected_query_string():
    http_client = Mock()
    downloader = TenderDownloader(http_client, "1032737", "j0w", Mock())
    downloader = TenderDownloader(Mock(), "1032737", "j0w")

    assert downloader.download_url == (
        "?page=entreprise.EntrepriseDownloadCompleteDce"
        "&reference=1032737&orgAcronym=j0w"
    )


def test_download_url_encodes_reserved_characters():
    http_client = Mock()
    downloader = TenderDownloader(http_client, "A&B", "x=y z", Mock())
    downloader = TenderDownloader(Mock(), "A&B", "x=y z")

    assert downloader.download_url == (
        "?page=entreprise.EntrepriseDownloadCompleteDce"
        "&reference=A%26B&orgAcronym=x%3Dy+z"
    )


def test_download_saves_archive_through_document_storage():
    http_client = Mock()
    mock_response = Mock(content=b"PK\x03\x04fake-zip-bytes")
    http_client.get = Mock(return_value=mock_response)
    document_storage = Mock()
    response = Mock(content=b"PK\x03\x04fake-zip-bytes")
    http_client.get.return_value = response
    s3_client = Mock()

    downloader = TenderDownloader(
        http_client, "1032737", "j0w", document_storage
    )
    downloader.download()

    http_client.get.assert_called_once_with(downloader.download_url)
    mock_response.raise_for_status.assert_called_once_with()
    document_storage.save_document.assert_called_once_with(
        downloader.filename, b"PK\x03\x04fake-zip-bytes"
    )

    )

    response.raise_for_status.assert_called_once_with()
    s3_client.upload_fileobj.assert_called_once_with(
        Fileobj=ANY,
        Bucket="test-bucket",
        Key=downloader.filename,
    )
    assert s3_client.upload_fileobj.call_args.kwargs["Fileobj"].read() == (
        b"PK\x03\x04fake-zip-bytes"
    )
