"""
Embedding Service – Local BGE embeddings generation.

Uses sentence-transformers with BAAI/bge-small-en-v1.5 model.
Generates 384-dimensional embeddings entirely offline.
"""

import logging
from typing import Optional

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Singleton service for generating text embeddings using BGE-small.
    
    The model is loaded lazily on first use to avoid slow startup.
    BGE models use a special query prefix for retrieval tasks.
    """

    _instance: Optional["EmbeddingService"] = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            settings = get_settings()
            self.model_name = settings.EMBEDDING_MODEL
            self.dimension = settings.EMBEDDING_DIMENSION
            # BGE models need a query prefix for better retrieval
            self.query_prefix = "Represent this sentence for searching relevant passages: "
            self._initialized = True

    def _load_model(self):
        """Lazy-load the sentence-transformers model."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}...")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"Embedding model loaded (dim={self.dimension})")
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of document texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (each is a list of floats).
        """
        if not texts:
            return []

        model = self._load_model()

        logger.info(f"Embedding {len(texts)} text chunks...")
        embeddings = model.encode(
            texts,
            show_progress_bar=False,
            normalize_embeddings=True,  # L2 normalize for cosine similarity
            batch_size=32
        )

        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """
        Generate an embedding for a search query.

        BGE models perform better when queries are prefixed with a
        special instruction string for retrieval tasks.

        Args:
            query: The search query string.

        Returns:
            Single embedding vector as a list of floats.
        """
        model = self._load_model()

        # Add BGE query prefix for better retrieval
        prefixed_query = f"{self.query_prefix}{query}"

        embedding = model.encode(
            [prefixed_query],
            show_progress_bar=False,
            normalize_embeddings=True
        )

        return embedding[0].tolist()

    @property
    def is_loaded(self) -> bool:
        """Check if the model has been loaded."""
        return self._model is not None


# Singleton instance
embedding_service = EmbeddingService()
