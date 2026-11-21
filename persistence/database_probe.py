"""Reports whether the database answers, without exposing how to reach it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import text

from persistence.database import Database


@dataclass(frozen=True)
class DatabaseHealth:
    """Whether the database answered, and why not if it didn't.

    Attributes:
        reachable: True if the database answered a trivial query.
        reason: Short, credential-free explanation when unreachable.
    """

    reachable: bool
    reason: str | None = None


class DatabaseProbe(Protocol):
    """Checks whether the database can be reached."""

    def check(self) -> DatabaseHealth:
        """Return the database's current health. Never raises."""


class PostgresDatabaseProbe:
    """DatabaseProbe that runs ``SELECT 1`` through the shared engine.

    How long a check can take is bounded by the engine's connect timeout
    (``Settings.connect_timeout``). Failure reasons are picked from a fixed
    set rather than copied from the driver, so they never carry the
    connection URL, user or password.
    """

    def __init__(self, database: Database) -> None:
        """Initialize the probe with a database instance.

        Args:
            database: Database whose engine is probed.
        """
        self._database = database

    def check(self) -> DatabaseHealth:
        """Return whether the database answers ``SELECT 1``. Never raises."""
        engine = self._database.engine
        if engine is None:
            return DatabaseHealth(reachable=False, reason="database connection is closed")
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001 - any failure means unreachable
            return DatabaseHealth(reachable=False, reason=_describe_failure(exc))
        return DatabaseHealth(reachable=True)


_FAILURE_REASONS = (
    (
        ("could not translate host name", "name or service not known", "nodename nor servname"),
        "host does not resolve",
    ),
    (("connection refused",), "connection refused"),
    (("timeout expired", "timed out"), "connection timed out"),
    (("password authentication failed",), "authentication failed"),
)


def _describe_failure(exc: Exception) -> str:
    """Turn a connection failure into a short reason without connection details."""
    cause = getattr(exc, "orig", None) or exc
    message = str(cause).lower()
    for markers, reason in _FAILURE_REASONS:
        if any(marker in message for marker in markers):
            return reason
    return f"connection failed ({type(cause).__name__})"
