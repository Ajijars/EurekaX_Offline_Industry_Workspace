"""
MongoDB Service — connection management and query execution.

Provides collection browsing, find/aggregate execution, and schema inference.
Gracefully handles missing pymongo dependency.
"""

import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_MONGO_AVAILABLE = False
try:
    from pymongo import MongoClient
    _MONGO_AVAILABLE = True
except ImportError:
    pass


class MongoDBService:
    """Execute queries against MongoDB."""

    def __init__(self):
        self._client = None

    @property
    def available(self) -> bool:
        return _MONGO_AVAILABLE

    def connect(self, connection_string: str) -> bool:
        """Establish a MongoDB connection."""
        if not _MONGO_AVAILABLE:
            return False
        try:
            self._client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            self._client.admin.command("ping")
            logger.info("[MongoDB] Connected successfully")
            return True
        except Exception as e:
            logger.error("[MongoDB] Connection failed: %s", e)
            self._client = None
            return False

    def list_databases(self) -> list[str]:
        if not self._client:
            return []
        try:
            return self._client.list_database_names()
        except Exception:
            return []

    def list_collections(self, database: str) -> list[str]:
        if not self._client:
            return []
        try:
            return self._client[database].list_collection_names()
        except Exception:
            return []

    def infer_schema(self, database: str, collection: str, sample_size: int = 100) -> list[dict]:
        """Infer schema by sampling documents."""
        if not self._client:
            return []
        try:
            coll = self._client[database][collection]
            docs = list(coll.find().limit(sample_size))
            field_types: dict[str, set] = {}
            for doc in docs:
                for key, value in doc.items():
                    if key not in field_types:
                        field_types[key] = set()
                    field_types[key].add(type(value).__name__)
            return [
                {"name": k, "types": sorted(v)} for k, v in field_types.items()
            ]
        except Exception as e:
            logger.error("[MongoDB] Schema inference failed: %s", e)
            return []

    def execute_find(
        self, database: str, collection: str,
        filter_doc: Optional[dict] = None,
        projection: Optional[dict] = None,
        sort: Optional[list] = None,
        limit: int = 100,
    ) -> dict:
        """Execute a find query."""
        if not self._client:
            return {"success": False, "error": "MongoDB not connected", "documents": []}

        start = time.monotonic()
        try:
            coll = self._client[database][collection]
            cursor = coll.find(filter_doc or {}, projection)
            if sort:
                cursor = cursor.sort(sort)
            cursor = cursor.limit(limit)

            docs = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                docs.append(doc)

            elapsed_ms = int((time.monotonic() - start) * 1000)
            return {
                "success": True,
                "documents": docs,
                "count": len(docs),
                "duration_ms": elapsed_ms,
            }
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return {"success": False, "error": str(e), "documents": [], "duration_ms": elapsed_ms}

    def execute_aggregate(
        self, database: str, collection: str, pipeline: list[dict],
    ) -> dict:
        """Execute an aggregation pipeline."""
        if not self._client:
            return {"success": False, "error": "MongoDB not connected", "documents": []}

        start = time.monotonic()
        try:
            coll = self._client[database][collection]
            cursor = coll.aggregate(pipeline)
            docs = []
            for doc in cursor:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                docs.append(doc)

            elapsed_ms = int((time.monotonic() - start) * 1000)
            return {
                "success": True,
                "documents": docs,
                "count": len(docs),
                "duration_ms": elapsed_ms,
            }
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return {"success": False, "error": str(e), "documents": [], "duration_ms": elapsed_ms}


mongodb_service = MongoDBService()
