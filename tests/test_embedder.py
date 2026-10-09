"""Tests for indexing.embedder."""

import pytest

from indexing.embedder import SentenceTransformerEmbedder
from persistence.config import Settings
from persistence.exceptions import ConfigurationError


@pytest.mark.slow
def test_bge_m3_embeds_french_and_arabic_into_1024_dim_vectors():
    settings = Settings(database_url="postgresql://unused")
    embedder = SentenceTransformerEmbedder(settings.embedding_model, settings.embedding_dim)

    vectors = embedder.embed(["Objet du marché", "موضوع الصفقة"])

    assert embedder.model_name == "BAAI/bge-m3"
    assert len(vectors) == 2
    assert all(len(vector) == settings.embedding_dim == 1024 for vector in vectors)



@pytest.mark.slow
def test_dimension_mismatch_with_configured_model_is_rejected():
    with pytest.raises(ConfigurationError, match="EMBEDDING_DIM=768"):
        SentenceTransformerEmbedder("BAAI/bge-m3", dimension=768)
