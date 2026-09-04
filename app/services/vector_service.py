"""
Vector Service – Qdrant vector database operations.

Handles collection management, document chunk storage,
similarity search, and document deletion.

Supports two modes:
  - Docker mode: connects to Qdrant at QDRANT_HOST:QDRANT_PORT
  - Local mode (fallback): uses file-based storage in ./qdrant_data/
"""

import logging
import uuid
from pathlib import Path
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.config import get_settings

logger = logging.getLogger(__name__)

# Local fallback storage path
QDRANT_LOCAL_PATH = Path("qdrant_data")


class VectorService:
    """Service class wrapping Qdrant vector database operations."""

    def __init__(self):
        settings = get_settings()
        self.host = settings.QDRANT_HOST
        self.port = settings.QDRANT_PORT
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self.dimension = settings.EMBEDDING_DIMENSION
        self._client: Optional[QdrantClient] = None
        self._mode: str = "unknown"

    @property
    def client(self) -> QdrantClient:
        """
        Lazy-initialize the Qdrant client.
        
        Tries Docker-based Qdrant first; falls back to local file mode.
        """
        if self._client is None:
            # Try Docker-based Qdrant first
            try:
                client = QdrantClient(host=self.host, port=self.port, timeout=5)
                client.get_collections()  # Test connectivity
                self._client = client
                self._mode = "docker"
                logger.info(f"Qdrant connected (Docker) at {self.host}:{self.port}")
            except Exception:
                # Fall back to local file storage
                QDRANT_LOCAL_PATH.mkdir(parents=True, exist_ok=True)
                self._client = QdrantClient(path=str(QDRANT_LOCAL_PATH))
                self._mode = "local"
                logger.info(f"Qdrant running (local mode) at {QDRANT_LOCAL_PATH.absolute()}")
        return self._client

    @property
    def mode(self) -> str:
        """Return the current Qdrant connection mode."""
        _ = self.client  # Ensure initialized
        return self._mode

    # ──────────────────────────────────────────────
    # Collection Management
    # ──────────────────────────────────────────────

    async def init_collection(self) -> bool:
        """
        Create the vector collection if it doesn't exist.
        
        Uses cosine similarity and the configured embedding dimension.
        """
        try:
            collections = self.client.get_collections().collections
            existing = [c.name for c in collections]

            if self.collection_name not in existing:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE
                    ),
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Qdrant collection exists: {self.collection_name}")

            return True
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {e}")
            return False

    async def check_health(self) -> bool:
        """Check if Qdrant is reachable."""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.warning(f"Qdrant health check failed: {e}")
            return False

    # ──────────────────────────────────────────────
    # CRUD Operations
    # ──────────────────────────────────────────────

    async def upsert_chunks(
        self,
        doc_id: str,
        chunks: list[str],
        vectors: list[list[float]],
        metadata: dict
    ) -> int:
        """
        Store document chunks with their embeddings in Qdrant.

        Args:
            doc_id: Document identifier
            chunks: List of text chunks
            vectors: Corresponding embedding vectors
            metadata: Document-level metadata (filename, etc.)

        Returns:
            Number of points inserted.
        """
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")

        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
            point_id = str(uuid.uuid4())
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "doc_id": doc_id,
                        "chunk_index": i,
                        "chunk_text": chunk,
                        "filename": metadata.get("filename", ""),
                        "file_type": metadata.get("file_type", ""),
                        "total_chunks": len(chunks),
                    }
                )
            )

        # Upsert in batches of 100
        batch_size = 100
        for start in range(0, len(points), batch_size):
            batch = points[start:start + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )

        logger.info(
            f"Stored {len(points)} chunks for doc '{doc_id}' "
            f"({metadata.get('filename', 'unknown')})"
        )
        return len(points)

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        doc_id: Optional[str] = None
    ) -> list[dict]:
        """
        Perform similarity search in the vector store.

        Args:
            query_vector: The query embedding vector
            top_k: Number of results to return
            doc_id: Optional filter to search within a specific document

        Returns:
            List of dicts with 'chunk_text', 'score', 'filename', 'chunk_index'
        """
        search_filter = None
        if doc_id:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id)
                    )
                ]
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=search_filter,
            with_payload=True,
        )

        return [
            {
                "chunk_text": hit.payload.get("chunk_text", ""),
                "score": round(hit.score, 4),
                "filename": hit.payload.get("filename", ""),
                "chunk_index": hit.payload.get("chunk_index", 0),
                "doc_id": hit.payload.get("doc_id", ""),
            }
            for hit in results
        ]

    async def delete_document(self, doc_id: str) -> bool:
        """Delete all chunks belonging to a specific document."""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="doc_id",
                            match=MatchValue(value=doc_id)
                        )
                    ]
                ),
            )
            logger.info(f"Deleted all chunks for doc_id: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

    async def list_documents(self) -> list[dict]:
        """
        List all unique documents in the collection.
        
        Scrolls through all points and groups by doc_id.
        """
        try:
            documents = {}
            offset = None
            batch_size = 100

            while True:
                result = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )

                points, next_offset = result

                for point in points:
                    doc_id = point.payload.get("doc_id", "")
                    if doc_id not in documents:
                        documents[doc_id] = {
                            "doc_id": doc_id,
                            "filename": point.payload.get("filename", ""),
                            "file_type": point.payload.get("file_type", ""),
                            "chunk_count": 0,
                        }
                    documents[doc_id]["chunk_count"] += 1

                if next_offset is None:
                    break
                offset = next_offset

            return list(documents.values())

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []

    async def get_collection_info(self) -> dict:
        """Get collection statistics."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status.value if info.status else "unknown",
                "mode": self._mode,
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {
                "name": self.collection_name,
                "points_count": 0,
                "status": "error",
                "error": str(e),
                "mode": self._mode,
            }


# Singleton instance
vector_service = VectorService()
