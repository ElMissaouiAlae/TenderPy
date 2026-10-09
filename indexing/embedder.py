"""Turn chunk text into embedding vectors."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from persistence.exceptions import ConfigurationError


class Embedder(Protocol):
    """Embeds texts into fixed-size vectors.

    Attributes:
        model_name: Name of the model producing the vectors, recorded on
            every chunk so vectors from different models are never mixed.
    """

    model_name: str

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per text, in the same order."""
        ...


class SentenceTransformerEmbedder:
    """Embedder backed by a sentence-transformers model, encoding in batches."""

    def __init__(self, model_name: str, dimension: int, batch_size: int = 16) -> None:
        """Load the model and check it produces vectors of the configured size.

        Args:
            model_name: Hugging Face model name (e.g. "BAAI/bge-m3").
            dimension: Expected vector size (EMBEDDING_DIM), which must match
                the vector column created by the migrations.
            batch_size: Texts encoded per forward pass; bounds memory use.

        Raises:
            ConfigurationError: if the model's dimension differs from `dimension`.
        """
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._batch_size = batch_size
        self._model = SentenceTransformer(model_name)
        model_dimension = self._model.get_embedding_dimension()
        if model_dimension != dimension:
            raise ConfigurationError(
                f"EMBEDDING_DIM={dimension} but {model_name} produces "
                f"{model_dimension}-dim vectors"
            )

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Encode texts in batches into L2-normalised vectors.

        Args:
            texts: Texts to embed.

        Returns:
            One vector per text, in the same order.
        """
        if not texts:
            return []
        vectors = self._model.encode(
            list(texts),
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vectors.tolist()
