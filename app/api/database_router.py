"""
Database Connectivity Router — MongoDB + SQL unified API.

Endpoints:
    POST /api/db/mongodb/connect     – Connect to MongoDB (admin only)
    GET  /api/db/mongodb/status      – Check MongoDB connection status
    GET  /api/db/mongodb/databases   – List MongoDB databases
    GET  /api/db/mongodb/collections – List collections in a database
    GET  /api/db/mongodb/schema      – Infer schema of a collection
    POST /api/db/mongodb/query       – Execute find query
    POST /api/db/mongodb/aggregate   – Execute aggregation pipeline
    POST /api/db/sql/execute         – Execute SQL query
    GET  /api/db/sql/history         – Get query history
    GET  /api/db/status              – Overall DB connectivity status
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user, require_admin
from app.db.database import get_db
from app.db.models import User

logger = logging.getLogger(__name__)

database_router = APIRouter(prefix="/api/db", tags=["Database Connectivity"])


# ── Request / Response Schemas ──

class MongoConnectRequest(BaseModel):
    connection_string: str = Field(..., description="MongoDB connection URI")


class MongoQueryRequest(BaseModel):
    database: str
    collection: str
    filter: dict = Field(default_factory=dict)
    projection: Optional[dict] = None
    sort: Optional[list] = None
    limit: int = Field(default=100, le=1000)


class MongoAggregateRequest(BaseModel):
    database: str
    collection: str
    pipeline: list[dict]


class SQLExecuteRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    source_name: str = "local"
    connection_string: Optional[str] = None
    max_rows: int = Field(default=500, le=5000)

# ── MongoDB Endpoints ──

@database_router.post("/mongodb/connect")
async def mongodb_connect(
    body: MongoConnectRequest,
    admin: User = Depends(require_admin),
):
    """Connect to a MongoDB instance (admin only)."""
    from app.services.mongodb_service import mongodb_service

    if not mongodb_service.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="pymongo is not installed. Run: pip install pymongo",
        )

    success = mongodb_service.connect(body.connection_string)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to connect to MongoDB. Check your connection string.",
        )

    databases = mongodb_service.list_databases()
    logger.info("[DB Router] MongoDB connected by admin %s", admin.username)
    return {
        "status": "connected",
        "databases": databases,
    }


@database_router.get("/mongodb/status")
async def mongodb_status(user: User = Depends(get_current_user)):
    """Check if MongoDB is connected."""
    from app.services.mongodb_service import mongodb_service

    if not mongodb_service.available:
        return {"available": False, "connected": False, "reason": "pymongo not installed"}

    connected = mongodb_service._client is not None
    if connected:
        try:
            mongodb_service._client.admin.command("ping")
        except Exception:
            connected = False

    return {"available": True, "connected": connected}


@database_router.get("/mongodb/databases")
async def mongodb_databases(user: User = Depends(get_current_user)):
    """List all MongoDB databases."""
    from app.services.mongodb_service import mongodb_service
    databases = mongodb_service.list_databases()
    return {"databases": databases}


@database_router.get("/mongodb/collections")
async def mongodb_collections(
    database: str,
    user: User = Depends(get_current_user),
):
    """List collections in a MongoDB database."""
    from app.services.mongodb_service import mongodb_service
    collections = mongodb_service.list_collections(database)
    return {"database": database, "collections": collections}


@database_router.get("/mongodb/schema")
async def mongodb_schema(
    database: str,
    collection: str,
    user: User = Depends(get_current_user),
):
    """Infer the schema of a MongoDB collection."""
    from app.services.mongodb_service import mongodb_service
    schema = mongodb_service.infer_schema(database, collection)
    return {"database": database, "collection": collection, "fields": schema}


@database_router.post("/mongodb/query")
async def mongodb_query(
    body: MongoQueryRequest,
    user: User = Depends(get_current_user),
):
    """Execute a find query on a MongoDB collection."""
    from app.services.mongodb_service import mongodb_service
    result = mongodb_service.execute_find(
        database=body.database,
        collection=body.collection,
        filter_doc=body.filter,
        projection=body.projection,
        sort=body.sort,
        limit=body.limit,
    )
    return result


@database_router.post("/mongodb/aggregate")
async def mongodb_aggregate(
    body: MongoAggregateRequest,
    user: User = Depends(get_current_user),
):
    """Execute an aggregation pipeline on a MongoDB collection."""
    from app.services.mongodb_service import mongodb_service
    result = mongodb_service.execute_aggregate(
        database=body.database,
        collection=body.collection,
        pipeline=body.pipeline,
    )
    return result


# ── SQL Endpoints ──

@database_router.post("/sql/execute")
async def sql_execute(
    body: SQLExecuteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a SQL query."""
    from app.services.sql_service import sql_service
    result = await sql_service.execute(
        db,
        sql=body.sql,
        source_name=body.source_name,
        connection_string=body.connection_string,
        user_id=user.id,
        max_rows=body.max_rows,
    )
    return result


@database_router.get("/sql/history")
async def sql_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
):
    """Get SQL query history for the current user."""
    from app.services.sql_service import sql_service
    history = await sql_service.get_history(db, user_id=user.id, limit=limit)
    return {"history": history}


# ── Combined Status ──

@database_router.get("/status")
async def db_status(user: User = Depends(get_current_user)):
    """Get overall database connectivity status."""
    from app.services.mongodb_service import mongodb_service

    mongo_connected = False
    mongo_available = mongodb_service.available
    if mongo_available and mongodb_service._client is not None:
        try:
            mongodb_service._client.admin.command("ping")
            mongo_connected = True
        except Exception:
            pass

    return {
        "mongodb": {
            "available": mongo_available,
            "connected": mongo_connected,
        },
        "sql": {
            "available": True,
            "connected": True,  # SQLite is always available
            "engine": "SQLite (local)",
        },
    }
