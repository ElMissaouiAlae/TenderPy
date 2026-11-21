"""Tests for core.http module."""

from unittest.mock import Mock, patch

import pytest
from requests.exceptions import RequestException

from core.exceptions import HttpRequestError
from core.http import HttpClient


def test_http_client_initialization_with_defaults():
    client = HttpClient()
    assert client._base_url == ""
    assert client._timeout == 10
    assert client._retries == 3
    assert "User-Agent" in client._session.headers


def test_http_client_initialization_with_custom_params():
    client = HttpClient(base_url="https://example.com", timeout=30, retries=5)
    assert client._base_url == "https://example.com"
    assert client._timeout == 30
    assert client._retries == 5


def test_http_client_base_url_strips_trailing_slash():
    client = HttpClient(base_url="https://example.com/")
    assert client._base_url == "https://example.com"


def test_build_url_with_absolute_url():
    client = HttpClient(base_url="https://example.com")
    url = client._build_url("https://other.com/path")
    assert url == "https://other.com/path"


def test_build_url_with_relative_url_and_base():
    client = HttpClient(base_url="https://example.com")
    url = client._build_url("api/search")
    assert url == "https://example.com/api/search"


def test_build_url_with_relative_url_without_base():
    client = HttpClient()
    url = client._build_url("api/search")
    assert url == "api/search"


def test_build_url_with_leading_slash():
    client = HttpClient(base_url="https://example.com")
    url = client._build_url("/api/search")
    assert url == "https://example.com/api/search"


def test_build_url_raises_on_empty_url():
    client = HttpClient()
    with pytest.raises(HttpRequestError, match="URL must not be empty"):
        client._build_url("")


@patch("core.http.requests.Session.request")
def test_get_request_success(mock_request):
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_request.return_value = mock_response

    client = HttpClient()
    response = client.get("https://example.com/api")

    mock_request.assert_called_once()
    assert response == mock_response


@patch("core.http.requests.Session.request")
def test_post_request_success(mock_request):
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_request.return_value = mock_response

    client = HttpClient()
    response = client.post("https://example.com/api", data={"key": "value"})

    mock_request.assert_called_once()
    assert response == mock_response


@patch("core.http.requests.Session.request")
def test_request_raises_on_http_error(mock_request):
    mock_request.side_effect = RequestException("Connection failed")

    client = HttpClient()
    with pytest.raises(HttpRequestError, match="GET request failed"):
        client.get("https://example.com/api")


def test_context_manager():
    client = HttpClient()
    with client as c:
        assert c is client
    # Session should be closed after context exit
    assert client._session.adapters == {}


def test_close():
    client = HttpClient()
    client.close()
    # Session should be closed
    assert client._session.adapters == {}


def test_setup_retries_with_zero_retries():
    client = HttpClient(retries=0)
    # Should not raise any errors
    client._setup_retries()


def test_setup_retries_with_negative_retries():
    client = HttpClient(retries=-1)
    # Should not raise any errors
    client._setup_retries()
