"""Session management for PRADO-based search pages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import requests

from .exceptions import HtmlParsingError, PradoStateError, SessionInitializationError
from .http import HttpClient


@dataclass
class SessionState:
    """Represents the current hidden PRADO state for a server session."""

    prado_page_state: str | None = None

    def to_payload(self) -> dict[str, str]:
        """Convert the current PRADO session state into POST parameters.

        Raises:
            PradoStateError: if PRADO_PAGESTATE hasn't been captured yet —
                every postback requires it, so a missing value here means
                this was called before any page was fetched.
        """
        if self.prado_page_state is None:
            raise PradoStateError(
                "PRADO_PAGESTATE is not set — fetch a page before building a payload"
            )

        return {
            "PRADO_PAGESTATE": self.prado_page_state,
            "PRADO_POSTBACK_PARAMETER": "undefined",
        }


class SearchSession:
    """Manages an initialized crawling session and refreshes PRADO state."""

    def __init__(self, http_client: HttpClient | Any) -> None:
        self._http_client = http_client
        self.state = SessionState()

    def initialize(self, url: str) -> requests.Response:
        """Initialize the session with the initial GET request and extract PRADO fields."""
        # Let HttpRequestError bubble up naturally from the HttpClient
        response = self._http_client.get(url)

        # Confirm SERVERID is present before attempting PRADO postback
        if "SERVERID" not in self._http_client.cookies:
            raise SessionInitializationError(
                "SERVERID cookie not found in response - cannot proceed with PRADO postback"
            )

        try:
            self._update_state_from_html(response.text)
        except (HtmlParsingError, PradoStateError) as exc:
            raise SessionInitializationError(f"Failed to initialize PRADO state: {exc}") from exc

        return response

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """Perform a GET request and refresh the PRADO state from the returned HTML."""
        response = self._http_client.get(url, **kwargs)

        # Mid-session parsing failure shouldn't throw an "Initialization" error
        self._update_state_from_html(response.text)
        return response

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        """Perform a POST request and refresh the PRADO state from the returned HTML."""
        response = self._http_client.post(url, **kwargs)

        # Mid-session parsing failure shouldn't throw an "Initialization" error
        self._update_state_from_html(response.text)
        return response

    def _update_state_from_html(self, html: str) -> None:
        """Extract hidden PRADO input values from an HTML response.

        Raises:
            HtmlParsingError: if the HTML is empty or unparsable.
            PradoStateError: if a required field is missing/empty, or the
                state object doesn't expose the expected attribute.
        """
        if not html:
            raise HtmlParsingError("Received empty HTML response")

        try:
            from bs4 import BeautifulSoup
        except ImportError as exc:
            raise HtmlParsingError("BeautifulSoup is required to parse PRADO state") from exc

        soup = BeautifulSoup(html, "html.parser")

        # Map exact HTML input `name` -> dataclass attribute.
        # `required=True` fields must be present with a non-empty value;
        # everything else defaults to "" if missing (legitimate on first load).
        prado_mapping = {
            "PRADO_PAGESTATE": ("prado_page_state", True),
        }

        found_fields: set[str] = set()

        for html_name, (dataclass_attr, required) in prado_mapping.items():
            element = soup.find("input", {"name": html_name})

            if element is None:
                if required:
                    raise PradoStateError(f"Required PRADO field '{html_name}' not found in HTML")
                continue

            value = element.get("value", "") or ""

            if required and not value:
                raise PradoStateError(f"Required PRADO field '{html_name}' has an empty value")

            if not hasattr(self.state, dataclass_attr):
                raise PradoStateError(
                    f"State object has no attribute '{dataclass_attr}' "
                    f"(mapped from '{html_name}')"
                )

            setattr(self.state, dataclass_attr, value)
            found_fields.add(html_name)

        # Belt-and-suspenders: required fields must have actually been set.
        # This comprehension returns the names of any required PRADO fields that were
        # defined in `prado_mapping` but were not found and recorded during parsing.
        # If the set is non-empty, it means the HTML response was missing one or more
        # required hidden inputs, so we raise a PradoStateError.
        missing_required = {
            html_name for html_name, (_, required) in prado_mapping.items()
            if required and html_name not in found_fields
        }
        if missing_required:
            raise PradoStateError(f"Missing required PRADO fields: {sorted(missing_required)}")
