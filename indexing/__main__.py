"""Index UPLOADED tenders into pgvector.

Run with: python -m indexing --limit 5
"""

from __future__ import annotations

import argparse
import logging

from indexing.chunker import DoclingChunker
from indexing.embedder import SentenceTransformerEmbedder
from indexing.pipeline import IndexingPipeline
from indexing.vector_store import PgVectorStore
from persistence import Database, Settings, TenderRepository
from persistence.file_storage import S3DocumentStorage


def main() -> None:
    parser = argparse.ArgumentParser(description="Index UPLOADED tenders into pgvector.")
    parser.add_argument(
        "--limit", type=int, required=True, help="Maximum number of tenders to index."
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    settings = Settings.from_env()
    database = Database(settings)
    try:
        pipeline = IndexingPipeline(
            repository=TenderRepository(database),
            document_storage=S3DocumentStorage(settings),
            chunker=DoclingChunker(tokenizer_model=settings.embedding_model),
            embedder=SentenceTransformerEmbedder(
                settings.embedding_model, settings.embedding_dim
            ),
            vector_store=PgVectorStore(database),
        )
        pipeline.run(limit=args.limit)
    finally:
        database.close()


if __name__ == "__main__":
    main()
