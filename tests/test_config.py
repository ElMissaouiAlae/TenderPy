"""Tests for the persistence configuration module."""

import pytest

from persistence.config import Settings
from persistence.exceptions import ConfigurationError, DatabaseConnectionError


def test_from_env_requires_database_url(monkeypatch):
    monkeypatch.delenv("DB_URL", raising=False)
    monkeypatch.setattr("persistence.config.load_dotenv", lambda: None)

    with pytest.raises(DatabaseConnectionError):
        Settings.from_env()


def test_from_env_does_not_require_s3_settings(monkeypatch):
    monkeypatch.setattr("persistence.config.load_dotenv", lambda: None)
    monkeypatch.setenv("DB_URL", "postgresql://user:pass@localhost/db")
    monkeypatch.delenv("S3_BUCKET_NAME", raising=False)
    monkeypatch.delenv("S3_REGION", raising=False)

    settings = Settings.from_env()

    assert settings.database_url == "postgresql://user:pass@localhost/db"
    assert settings.s3_bucket_name is None
    assert settings.s3_region is None


def test_from_env_reads_s3_settings_when_present(monkeypatch):
    monkeypatch.setenv("DB_URL", "postgresql://user:pass@localhost/db")
    monkeypatch.setenv("S3_BUCKET_NAME", "tenders-bucket")
    monkeypatch.setenv("S3_REGION", "eu-west-3")

    settings = Settings.from_env()

    assert settings.s3_bucket_name == "tenders-bucket"
    assert settings.s3_region == "eu-west-3"


def test_require_s3_raises_when_bucket_missing():
    settings = Settings(database_url="postgresql://x", s3_bucket_name=None, s3_region="eu-west-3")

    with pytest.raises(ConfigurationError):
        settings.require_s3()


def test_require_s3_raises_when_region_missing():
    settings = Settings(database_url="postgresql://x", s3_bucket_name="tenders-bucket", s3_region=None)

    with pytest.raises(ConfigurationError):
        settings.require_s3()


def test_require_s3_returns_bucket_and_region_when_present():
    settings = Settings(
        database_url="postgresql://x", s3_bucket_name="tenders-bucket", s3_region="eu-west-3"
    )

    assert settings.require_s3() == ("tenders-bucket", "eu-west-3")
