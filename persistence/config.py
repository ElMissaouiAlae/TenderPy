"""Configuration management for the persistence layer."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .exceptions import ConfigurationError, DatabaseConnectionError


@dataclass
class Settings:
    """Configuration settings for database connections and S3 uploads.

    Attributes:
        database_url: PostgreSQL connection string
        s3_bucket_name: Name of the S3 bucket DCE archives are uploaded to,
            or None if not configured. Not required unless S3 is actually
            used - call require_s3() at the point of use to validate.
        s3_region: AWS region the S3 bucket lives in, or None if not
            configured. Same lazy-validation caveat as s3_bucket_name.
        pool_size: Connection pool size
        max_overflow: Maximum overflow connections beyond pool_size
        pool_timeout: Timeout in seconds for getting a connection from pool
        pool_recycle: Recycle connections after this many seconds
    """

    database_url: str
    s3_bucket_name: str | None = None
    s3_region: str | None = None
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600

    @classmethod
    def from_env(cls) -> Settings:
        """Load settings from environment variables.

        Loads environment variables from .env file if present.
        Expects DB_DATABASE_URL to be set. S3_BUCKET_NAME and S3_REGION are
        read if present but not required here - they're only validated by
        require_s3(), called at the point S3 access is actually needed, so
        that callers who only need database settings aren't forced to
        configure S3.

        Returns:
            Settings instance configured from environment.

        Raises:
            DatabaseConnectionError: if DB_DATABASE_URL is missing.
        """
        load_dotenv()

        database_url = os.getenv("DB_DATABASE_URL")
        if not database_url:
            raise DatabaseConnectionError(
                "DB_DATABASE_URL environment variable is required"
            )

        return cls(
            database_url=database_url,
            s3_bucket_name=os.getenv("S3_BUCKET_NAME"),
            s3_region=os.getenv("S3_REGION"),
            pool_size=int(os.getenv("DB_POOL_SIZE", str(cls.pool_size))),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", str(cls.max_overflow))),
            pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", str(cls.pool_timeout))),
            pool_recycle=int(os.getenv("DB_POOL_RECYCLE", str(cls.pool_recycle))),
        )

    def require_s3(self) -> tuple[str, str]:
        """Validate that S3 settings are present, raising if not.

        Call this at the point S3 access is actually needed (e.g. when
        constructing an S3 client for TenderUploader) rather than in
        from_env(), so that flows which never touch S3 aren't forced to
        configure it.

        Returns:
            A (bucket_name, region) tuple.

        Raises:
            ConfigurationError: if s3_bucket_name or s3_region is missing.
        """
        if not self.s3_bucket_name:
            raise ConfigurationError(
                "S3_BUCKET_NAME environment variable is required"
            )
        if not self.s3_region:
            raise ConfigurationError(
                "S3_REGION environment variable is required"
            )
        return self.s3_bucket_name, self.s3_region
