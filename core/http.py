"""Reusable HTTP client for crawler requests."""

from __future__ import annotations

from typing import Any
from types import TracebackType
import time

import requests
from requests.adapters import HTTPAdapter
from requests.cookies import RequestsCookieJar
from urllib3.util import Retry

from .exceptions import HttpRequestError


class HttpClient:
    """Thin wrapper around requests.Session with sensible defaults and auto-retries."""

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,ar;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    # Expose session cookies for external access
    @property
    def cookies(self) -> RequestsCookieJar:
        return self._session.cookies

    def __init__(self, base_url: str = "", timeout: int = 10, retries: int = 3, request_delay: float = 0.0) -> None:
        self._session = requests.Session()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retries = retries
        self._request_delay = request_delay

        # Set default headers
        self._session.headers.update(self.DEFAULT_HEADERS)

        # Configure automatic retry logic
        self._setup_retries()

    def _setup_retries(self) -> None:
        """Mount an HTTPAdapter with automatic retry policies to the session."""
        if self._retries <= 0:
            return

        # Retry on common network drops or standard server-side rate-limits/errors
        retry_strategy = Retry(
            total=self._retries,
            backoff_factor=1,  # Waits: 1s, 2s, 4s between attempts
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,  # Allows raise_for_status() to handle exceptions cleanly
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """Perform a GET request and return the response."""
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        """Perform a POST request and return the response."""
        return self._request("POST", url, **kwargs)

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """Send a request with timeout, redirects, and retry handling."""
        full_url = self._build_url(url)

        # Extract timeout and allow_redirects before use for potential retry
        timeout = kwargs.pop("timeout", self._timeout)
        allow_redirects = kwargs.pop("allow_redirects", True)

        # Add delay before request if specified
        if self._request_delay > 0:
            time.sleep(self._request_delay)

        try:
            response = self._session.request(
                method=method,
                url=full_url,
                timeout=timeout,
                allow_redirects=allow_redirects,
                **kwargs,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            # Capture set-cookie headers even on failed requests
            set_cookies = dict(exc.response.cookies) if exc.response is not None else {}
            raise HttpRequestError(
                f"{method} request failed for {full_url}: {exc}",
                set_cookies=set_cookies
            ) from exc

    def _build_url(self, url: str) -> str:
        """Build the full request URL from the base URL and path."""
        if not url:
            raise HttpRequestError("URL must not be empty")
        if url.startswith(("http://", "https://")):
            return url
        return f"{self._base_url}/{url.lstrip('/')}" if self._base_url else url

    def close(self) -> None:
        """Close the underlying session and release mounted adapters."""
        self._session.close()
        self._session.adapters.clear()

    # Context Manager support for 'with HttpClient() as client:' syntax
    def __enter__(self) -> HttpClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
