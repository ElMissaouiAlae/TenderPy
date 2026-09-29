"""Tests for core.session module."""

import builtins
from unittest.mock import Mock

import pytest

from core.exceptions import HtmlParsingError, PradoStateError, SessionInitializationError
from core.session import SearchSession, SessionState


def test_session_state_to_payload_returns_expected_dict():
    state = SessionState(prado_page_state="page-state-value")

    payload = state.to_payload()

    assert payload == {
        "PRADO_PAGESTATE": "page-state-value",
        "PRADO_POSTBACK_PARAMETER": "undefined",
    }


def test_session_state_to_payload_raises_when_state_is_none():
    state = SessionState()

    with pytest.raises(PradoStateError, match="PRADO_PAGESTATE is not set"):
        state.to_payload()


def test_search_session_initialize_fetches_page_and_sets_state():
    http_client = Mock()
    http_client.get.return_value = Mock(text="<html><body><input type='hidden' name='PRADO_PAGESTATE' value='abc123'/></body></html>")
    http_client.cookies = {"SERVERID": "server-1"}
    session = SearchSession(http_client=http_client)

    response = session.initialize("https://example.test")

    assert response == http_client.get.return_value
    assert session.state.prado_page_state == "abc123"


def test_search_session_initialize_raises_when_serverid_missing():
    http_client = Mock()
    http_client.get.return_value = Mock(text="<html><body><input type='hidden' name='PRADO_PAGESTATE' value='abc123'/></body></html>")
    http_client.cookies = {}
    session = SearchSession(http_client=http_client)

    with pytest.raises(SessionInitializationError, match="SERVERID cookie not found"):
        session.initialize("https://example.test")


def test_search_session_initialize_wraps_prado_errors():
    http_client = Mock()
    http_client.get.return_value = Mock(text="<html><body></body></html>")
    http_client.cookies = {"SERVERID": "server-1"}
    session = SearchSession(http_client=http_client)

    with pytest.raises(SessionInitializationError, match="Failed to initialize PRADO state"):
        session.initialize("https://example.test")


def test_update_state_from_html_parses_prado_pagestate():
    html = "<html><body><input type='hidden' name='PRADO_PAGESTATE' value='abc123'/></body></html>"
    session = SearchSession(http_client=object())

    session._update_state_from_html(html)

    assert session.state.prado_page_state == "abc123"


def test_update_state_from_html_raises_prado_state_error_when_missing_input():
    html = "<html><body></body></html>"
    session = SearchSession(http_client=object())

    with pytest.raises(PradoStateError, match="Required PRADO field 'PRADO_PAGESTATE' not found"):
        session._update_state_from_html(html)


def test_update_state_from_html_raises_html_parsing_error_on_empty_html():
    session = SearchSession(http_client=object())

    with pytest.raises(HtmlParsingError, match="Received empty HTML response"):
        session._update_state_from_html("")


def test_update_state_from_html_raises_html_parsing_error_when_bs4_missing(monkeypatch):
    html = "<html><body><input type='hidden' name='PRADO_PAGESTATE' value='abc123'/></body></html>"
    session = SearchSession(http_client=object())

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "bs4":
            raise ImportError("No module named bs4")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(HtmlParsingError, match="BeautifulSoup is required to parse PRADO state"):
        session._update_state_from_html(html)


def test_update_state_from_html_with_realistic_html():
    """Test _update_state_from_html with more realistic HTML structure."""
    html = """
    <html>
        <body>
            <form>
                <input type='hidden' name='PRADO_PAGESTATE' value='/wEPDwULLTEwMDk5MjIwMTNkZGRW'/>
                <input type='hidden' name='other_field' value='ignored'/>
            </form>
        </body>
    </html>
    """
    session = SearchSession(http_client=object())

    session._update_state_from_html(html)

    assert session.state.prado_page_state == "/wEPDwULLTEwMDk5MjIwMTNkZGRW"


def test_update_state_from_html_updates_existing_state():
    """Test that _update_state_from_html properly updates existing state."""
    html = "<html><body><input type='hidden' name='PRADO_PAGESTATE' value='new-state-value'/></body></html>"
    session = SearchSession(http_client=object())
    session.state.prado_page_state = "old-state-value"

    session._update_state_from_html(html)

    assert session.state.prado_page_state == "new-state-value"


def test_search_session_get_refreshes_state_from_response():
    http_client = Mock()
    http_client.get.return_value = Mock(
        text="<html><body><input type='hidden' name='PRADO_PAGESTATE' value='fresh-state'/></body></html>"
    )
    session = SearchSession(http_client=http_client)

    response = session.get("https://example.test")

    assert response == http_client.get.return_value
    assert session.state.prado_page_state == "fresh-state"


def test_search_session_post_refreshes_state_from_response():
    http_client = Mock()
    http_client.post.return_value = Mock(
        text="<html><body><input type='hidden' name='PRADO_PAGESTATE' value='posted-state'/></body></html>"
    )
    session = SearchSession(http_client=http_client)

    response = session.post("https://example.test", data={"a": "b"})

    assert response == http_client.post.return_value
    assert session.state.prado_page_state == "posted-state"
