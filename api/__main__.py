"""Serve the dashboard API against the configured database and document storage.

Run with: python -m api [--port 8000]
"""

from __future__ import annotations

import argparse
import logging

import uvicorn

from api.app import create_app
from persistence import Database, Settings
from persistence.database_probe import PostgresDatabaseProbe
from persistence.file_storage import S3DocumentStorage
from persistence.insights import PostgresInsights
from persistence.tender_lookup import PostgresTenderLookup

logger = logging.getLogger("api")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the dashboard API.")
    parser.add_argument("--host", default="127.0.0.1", help="Interface to bind to.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on.")
    args = parser.parse_args()
    logging.basicConfig(format="%(levelname)s:     %(message)s")

    settings = Settings.from_env()
    database = Database(settings)
    try:
        database_probe = PostgresDatabaseProbe(database)
        database_health = database_probe.check()
        if not database_health.reachable:
            logger.warning(
                "Database unreachable (%s); starting anyway - check GET /health",
                database_health.reason,
            )
        app = create_app(
            tender_lookup=PostgresTenderLookup(database),
            insights=PostgresInsights(database),
            document_storage=S3DocumentStorage(settings),
            database_probe=database_probe,
        )
        uvicorn.run(app, host=args.host, port=args.port)
    finally:
        database.close()


if __name__ == "__main__":
    main()
