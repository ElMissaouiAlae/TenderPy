"""Tests for retrieval.retriever, driven through Retriever.retrieve.

The embedder and the vector store are fakes.
"""

from collections.abc import Sequence

import pytest

from core.models import Tender
from indexing.models import SearchHit
from persistence.exceptions import RecordNotFoundError
from retrieval.retriever import Retriever


class FakeEmbedder:
    """Embedder mapping each known text to a fixed vector, recording what it embedded."""

    model_name = "fake-embedder"

    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._vectors = vectors
        self.embedded: list[str] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.embedded.extend(texts)
        return [self._vectors[text] for text in texts]


class FakeVectorStore:
    """Vector store returning canned hits and recording each search."""

    def __init__(self, hits: list[SearchHit] | None = None) -> None:
        self._hits = hits or []
        self.searches: list[dict] = []

    def replace_tender_files(self, tender, dce_files) -> None:
        raise AssertionError("retrieval must never write to the vector store")

    def search(self, query_embedding, embedding_model, limit=10, tender=None):
        self.searches.append(
            {
                "query_embedding": list(query_embedding),
                "embedding_model": embedding_model,
                "limit": limit,
                "tender": tender,
            }
        )
        return self._hits[:limit]


def _hit(chunk_index: int, distance: float) -> SearchHit:
    return SearchHit(
        tender_id="T-1",
        organization_acronym="ORG",
        dce_file_path="CPS.pdf",
        chunk_index=chunk_index,
        text=f"chunk {chunk_index}",
        page_numbers=(chunk_index + 1,),
        headings=("Article 1",),
        distance=distance,
    )


def test_retrieve_searches_with_the_query_embedding_and_keeps_the_store_order():
    query = "date limite de remise des offres"
    embedder = FakeEmbedder({query: [0.6, 0.8]})
    # Deliberately not sorted by distance: the store decides the order.
    hits = [_hit(2, 0.5), _hit(0, 0.1), _hit(1, 0.3)]
    store = FakeVectorStore(hits)

    result = Retriever(embedder, store).retrieve(query, top_k=3)

    assert result == hits
    assert embedder.embedded == [query]
    assert store.searches == [
        {
            "query_embedding": [0.6, 0.8],
            "embedding_model": "fake-embedder",
            "limit": 3,
            "tender": None,
        }
    ]


def test_retrieve_scopes_the_search_to_the_given_tender():
    query = "cautionnement provisoire"
    tender = Tender(tender_id="T-1", organization_acronym="ORG")
    store = FakeVectorStore([_hit(0, 0.2)])

    result = Retriever(FakeEmbedder({query: [1.0, 0.0]}), store).retrieve(
        query, top_k=2, tender=tender
    )

    assert result == [_hit(0, 0.2)]
    assert store.searches[0]["tender"] == tender
    assert store.searches[0]["limit"] == 2


def test_retrieve_returns_five_hits_by_default():
    query = "délai d'exécution"
    store = FakeVectorStore([_hit(index, index / 10) for index in range(8)])

    result = Retriever(FakeEmbedder({query: [1.0, 0.0]}), store).retrieve(query)

    assert [hit.chunk_index for hit in result] == [0, 1, 2, 3, 4]
    assert store.searches[0]["limit"] == 5


def test_retrieve_returns_no_hits_when_the_store_is_empty():
    query = "pénalités de retard"

    result = Retriever(FakeEmbedder({query: [1.0, 0.0]}), FakeVectorStore()).retrieve(query)

    assert result == []


def test_retrieve_raises_when_the_tender_does_not_exist():
    class StoreWithoutTender(FakeVectorStore):
        def search(self, query_embedding, embedding_model, limit=10, tender=None):
            raise RecordNotFoundError("No tender found for tender_id='MISSING'")

    query = "garantie"
    retriever = Retriever(FakeEmbedder({query: [1.0, 0.0]}), StoreWithoutTender())

    with pytest.raises(RecordNotFoundError):
        retriever.retrieve(query, tender=Tender(tender_id="MISSING", organization_acronym="ORG"))
