"""Embed a query and return the nearest chunks as search hits."""

from __future__ import annotations

from core.models import Tender
from indexing.embedder import Embedder
from indexing.models import SearchHit
from indexing.vector_store import VectorStore


class Retriever:
    """Finds the chunks most similar to a query.

    The query is embedded with the same embedder used for indexing, and only
    chunks embedded with that model are compared.
    """

    def __init__(self, embedder: Embedder, vector_store: VectorStore) -> None:
        """Initialize the retriever.

        Args:
            embedder: Embeds the query; must be the model the chunks were
                embedded with.
            vector_store: Store searched for the nearest chunks.
        """
        self._embedder = embedder
        self._vector_store = vector_store

    def retrieve(
        self, query: str, top_k: int = 5, tender: Tender | None = None
    ) -> list[SearchHit]:
        """Return the top_k search hits for a query, nearest first.

        Args:
            query: Free-text query.
            top_k: Maximum number of search hits.
            tender: When given, only this tender's chunks are searched;
                otherwise every tender's chunks are.

        Returns:
            Search hits ordered nearest first.

        Raises:
            RecordNotFoundError: if tender is given and does not exist.
            RepositoryError: if the search fails.
        """
        [query_embedding] = self._embedder.embed([query])
        return self._vector_store.search(
            query_embedding, self._embedder.model_name, limit=top_k, tender=tender
        )
