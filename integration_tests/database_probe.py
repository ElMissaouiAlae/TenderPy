"""Test PostgresDatabaseProbe against the real Postgres database and an unreachable one."""

from persistence import Database, Settings
from persistence.database_probe import PostgresDatabaseProbe

from .config import logger

UNRESOLVABLE_HOST = "pg-does-not-exist.tenderpy.invalid"


def test_database_probe():
    """Test which databases PostgresDatabaseProbe reports as reachable.

    The live database must be reachable. An unresolvable host and a refused
    connection must be unreachable, with a reason that leaks no connection
    details.

    Raises on any failure instead of swallowing it - callers must not treat
    a caught exception here as a passing run.
    """
    logger.info("\n" + "=" * 60)
    logger.info("TEST: Database Probe (connects to Postgres)")
    logger.info("=" * 60)

    settings = Settings.from_env()
    database = Database(settings)
    try:
        health = PostgresDatabaseProbe(database).check()
        logger.info(f"Live database: {health}")
        if not health.reachable:
            raise AssertionError(f"Expected the live database to be reachable, got {health}")
    finally:
        database.close()

    # (host:port, expected reason)
    unreachable_cases = [
        (f"{UNRESOLVABLE_HOST}:5432", "host does not resolve"),
        ("127.0.0.1:1", "connection refused"),
    ]
    for address, expected_reason in unreachable_cases:
        unreachable_url = f"postgresql://probe-user:probe-secret@{address}/db"
        database = Database(Settings(database_url=unreachable_url, connect_timeout=3))
        try:
            health = PostgresDatabaseProbe(database).check()
            logger.info(f"{address}: {health}")
            if health.reachable or health.reason != expected_reason:
                raise AssertionError(f"Expected {expected_reason!r} for {address}, got {health}")
            for secret in ("probe-user", "probe-secret", address):
                if secret in (health.reason or ""):
                    raise AssertionError(f"Probe reason leaks connection details: {health.reason}")
        finally:
            database.close()

    logger.info("Database probe verified successfully")
