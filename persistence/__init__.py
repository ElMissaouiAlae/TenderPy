"""Persistence layer for tender data management.

This package provides a Repository Pattern-based persistence layer that
isolates database implementation details from the rest of the application.
"""

from persistence.config import Settings
from persistence.database import Database
from persistence.exceptions import (
    ConfigurationError,
    DatabaseConnectionError,
    DuplicateTenderError,
    PersistenceError,
    RecordNotFoundError,
    RepositoryError,
    TransactionError,
)
from persistence.migrations import verify_schema
from persistence.models import TenderRecord, TenderStatus
from persistence.repository import TenderRepository

__all__ = [
    "Settings",
    "Database",
    "TenderRepository",
    "TenderRecord",
    "TenderStatus",
    "verify_schema",
    "PersistenceError",
    "ConfigurationError",
    "DatabaseConnectionError",
    "RepositoryError",
    "DuplicateTenderError",
    "RecordNotFoundError",
    "TransactionError",
]
