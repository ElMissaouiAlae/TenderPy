"""Print the chunks most similar to a query.

Run with: python -m retrieval "date limite de remise des offres" --top-k 5
Scope to one tender with: --tender <tender_id> --org <organization_acronym>
"""

from __future__ import annotations

import argparse
import logging
import sys

from core.models import Tender
from indexing.embedder import SentenceTransformerEmbedder
from indexing.models import SearchHit
from indexing.vector_store import PgVectorStore
from persistence import Database, RecordNotFoundError, Settings
from retrieval.retriever import Retriever


def _non_blank_text(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("query must not be blank")
    return value


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print the chunks most similar to a query.")
    parser.add_argument("query", type=_non_blank_text, help="Free-text query.")
    parser.add_argument(
        "--top-k", type=_positive_int, default=5, help="Number of search hits (default: 5)."
    )
    parser.add_argument("--tender", help="Only search this tender's chunks (requires --org).")
    parser.add_argument("--org", help="Organization acronym of --tender.")
    args = parser.parse_args()
    if (args.tender is None) != (args.org is None):
        parser.error("--tender and --org must be passed together")
    return args


def _format_hit(rank: int, hit: SearchHit) -> str:
    pages = ", ".join(str(page) for page in hit.page_numbers) or "-"
    headings = " > ".join(hit.headings) or "-"
    return (
        f"#{rank}  similarity {1 - hit.distance:.3f}\n"
        f"Tender:   {hit.tender_id} ({hit.organization_acronym})\n"
        f"File:     {hit.dce_file_path}\n"
        f"Pages:    {pages}\n"
        f"Headings: {headings}\n"
        f"\n{hit.text}\n"
    )


def main() -> None:
    args = _parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    tender = (
        None
        if args.tender is None
        else Tender(tender_id=args.tender, organization_acronym=args.org)
    )
    settings = Settings.from_env()
    database = Database(settings)
    try:
        retriever = Retriever(
            embedder=SentenceTransformerEmbedder(
                settings.embedding_model, settings.embedding_dim
            ),
            vector_store=PgVectorStore(database),
        )
        hits = retriever.retrieve(args.query, top_k=args.top_k, tender=tender)
    except RecordNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        database.close()

    if not hits:
        print("No search hits")
        return
    print("\n".join(_format_hit(rank, hit) for rank, hit in enumerate(hits, start=1)))


if __name__ == "__main__":
    main()
