"""Core domain layer: tender model, HTTP client, and PRADO session handling."""

from core.exceptions import (
    CrawlerException,
    HtmlParsingError,
    HttpRequestError,
    MissingTenderFieldError,
    PaginationError,
    PradoStateError,
    SearchExecutionError,
    SearchParsingError,
    SessionInitializationError,
)
from core.http import HttpClient
from core.models import Tender
from core.session import SearchSession, SessionState

__all__ = [
    "CrawlerException",
    "HtmlParsingError",
    "HttpClient",
    "HttpRequestError",
    "MissingTenderFieldError",
    "PaginationError",
    "PradoStateError",
    "SearchExecutionError",
    "SearchParsingError",
    "SearchSession",
    "SessionInitializationError",
    "SessionState",
    "Tender",
]
