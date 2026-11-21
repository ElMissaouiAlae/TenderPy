"""Serve the dashboard API against the configured database and document storage.

Run with: python -m api [--port 8000]
"""

from __future__ import annotations

import argparse

import uvicorn

from api.app import create_app
from persistence import Database, Settings
from persistence.file_storage import S3DocumentStorage
from persistence.tender_lookup import PostgresTenderLookup


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the dashboard API.")
    parser.add_argument("--host", default="127.0.0.1", help="Interface to bind to.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on.")
    args = parser.parse_args()

    settings = Settings.from_env()
    database = Database(settings)
    try:
        app = create_app(
            tender_lookup=PostgresTenderLookup(database),
            document_storage=S3DocumentStorage(settings),
        )
        uvicorn.run(app, host=args.host, port=args.port)
    finally:
        database.close()


if __name__ == "__main__":
    main()
