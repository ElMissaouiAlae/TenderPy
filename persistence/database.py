"""Database connection management for the persistence layer."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .exceptions import DatabaseConnectionError


class Database:
    """Manages database connections and session lifecycle.

    This class provides a SQLAlchemy engine and session factory
    configured for PostgreSQL with connection pooling.

    Attributes:
        engine: SQLAlchemy engine instance.
        _session_factory: Callable that creates new Session instances.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize database connection with given settings.

        Args:
            settings: Configuration settings for database connection.

        Raises:
            DatabaseConnectionError: if engine creation fails.
        """
        self._settings = settings
        self.engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

        self._initialize_engine()

    def _initialize_engine(self) -> None:
        """Create SQLAlchemy engine with connection pooling.

        Raises:
            DatabaseConnectionError: if engine creation fails.
        """
        try:
            self.engine = create_engine(
                self._settings.database_url,
                pool_size=self._settings.pool_size,
                max_overflow=self._settings.max_overflow,
                pool_timeout=self._settings.pool_timeout,
                pool_recycle=self._settings.pool_recycle,
                connect_args={"connect_timeout": self._settings.connect_timeout},
                echo=False,
            )
            self._session_factory = sessionmaker(bind=self.engine)
        except Exception as exc:
            raise DatabaseConnectionError(f"Failed to create database engine: {exc}") from exc

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provide a transactional scope for database operations.

        Yields:
            Session: SQLAlchemy session instance.

        Example:
            with database.session() as session:
                # perform database operations
                session.commit()
        """
        if self._session_factory is None:
            raise DatabaseConnectionError("Session factory not initialized")

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self) -> None:
        """Close the database engine and dispose of connections."""
        if self.engine is not None:
            self.engine.dispose()
            self.engine = None
            self._session_factory = None
