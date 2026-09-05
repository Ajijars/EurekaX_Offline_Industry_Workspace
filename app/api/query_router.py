"""
Query API Router — SQL and MongoDB query execution, history, saved queries.
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.db.database import get_db
from app.db.models import User, Permission
from app.security.query_sanitizer import query_sanitizer
from app.security.anomaly_detector import anomaly_detector
from app.services.audit_service import audit_service
from app.services.catalog_service import catalog_service
from sqlalchemy import select

logger = logging.getLogger(__name__)
query_router = APIRouter(prefix="/api/query", tags=["Query"])


class SQLQueryRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    source_name: str = "local"
    max_rows: int = Field(default=500, le=5000)

class MongoQueryRequest(BaseModel):
    database: str
    collection: str
    operation: str = "find"  # find, aggregate
    filter: Optional[dict] = None
    pipeline: Optional[list] = None
    limit: int = Field(default=100, le=1000)

class SaveQueryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    query_text: str = Field(..., min_length=1)
    source_name: str = ""
    description: str = ""


# ── SQL ──

@query_router.post("/sql")
async def execute_sql(
    body: SQLQueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a SQL query with role-based sanitization."""
    # Rate limit check
    allowed, reason = anomaly_detector.check_rate_limit(user.id)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)

    # Sanitize query based on role
    sanitize = query_sanitizer.sanitize_sql(body.sql, role=user.role)
    if not sanitize.is_safe:
        await audit_service.log(db, user_id=user.id, action="blocked_query", resource_type="sql", details={"reason": sanitize.blocked_reason, "sql": body.sql[:500]})
        raise HTTPException(status_code=403, detail=sanitize.blocked_reason)

    # Dataset Permission Check
    if user.role != "admin":
        import re
        all_entries = await catalog_service.list_entries(db)
        # Get permitted IDs
        perm_res = await db.execute(
            select(Permission.resource_id).where(
                Permission.user_id == user.id,
                Permission.resource_type == "catalog_entry"
            )
        )
        permitted_ids = {int(r[0]) for r in perm_res.all()}
        
        # Check against restricted tables
        for entry in all_entries:
            if entry["id"] not in permitted_ids:
                # If restricted table name appears in query as a whole word (case-insensitive)
                pattern = rf"\b{re.escape(entry['table_name'])}\b"
                if re.search(pattern, body.sql, re.IGNORECASE):
                    msg = f"Access denied: You do not have permission to query dataset '{entry['table_name']}'"
                    await audit_service.log(db, user_id=user.id, action="blocked_query", resource_type="sql", details={"reason": "unauthorized_dataset", "table": entry['table_name']})
                    raise HTTPException(status_code=403, detail=msg)

    from app.services.sql_service import sql_service
    result = await sql_service.execute(db, sql=body.sql, source_name=body.source_name, user_id=user.id, max_rows=body.max_rows)

    await audit_service.log(db, user_id=user.id, action="sql_query", resource_type="sql", details={"source": body.source_name, "rows": result.get("row_count", 0)})

    # PII Scanning on Output
    if result.get("rows"):
        from app.security.guardrails import guardrails
        rows_str = json.dumps(result["rows"])
        scan_res = guardrails.scan_output(rows_str, role=user.role)
        if not scan_res.is_safe:
            # Re-parse the sanitized JSON string if it was modified
            try:
                result["rows"] = json.loads(scan_res.sanitized_text or rows_str)
            except json.JSONDecodeError:
                result["rows"] = [{"error": "Output redacted due to PII violations."}]
                
            await audit_service.log(db, user_id=user.id, action="pii_redacted", resource_type="sql", details={"violations": [v["category"] for v in scan_res.violations]})
            
            # Log as a security alert
            await anomaly_detector.create_alert(
                db, user_id=user.id, alert_type="pii_leak_attempt", severity="high",
                message=f"PII detected and redacted in query output. Violations: {len(scan_res.violations)}"
            )

    # Check for bulk extraction
    bulk_msg = anomaly_detector.check_bulk_extraction(result.get("row_count", 0), user.id)
    if bulk_msg:
        await anomaly_detector.create_alert(db, user_id=user.id, alert_type="bulk_extract", severity="medium", message=bulk_msg)

    return result


# ── MongoDB ──

@query_router.post("/mongodb")
async def execute_mongodb(
    body: MongoQueryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a MongoDB query."""
    allowed, reason = anomaly_detector.check_rate_limit(user.id)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)

    from app.services.mongodb_service import mongodb_service
    if not mongodb_service.available:
        raise HTTPException(status_code=501, detail="MongoDB not available (pymongo not installed)")

    if body.operation == "find":
        result = mongodb_service.execute_find(
            body.database, body.collection,
            filter_doc=body.filter, limit=body.limit,
        )
    elif body.operation == "aggregate":
        if not body.pipeline:
            raise HTTPException(status_code=400, detail="Pipeline required for aggregate")
        result = mongodb_service.execute_aggregate(body.database, body.collection, body.pipeline)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown operation: {body.operation}")

    await audit_service.log(db, user_id=user.id, action="mongodb_query", resource_type="mongodb", details={"db": body.database, "collection": body.collection})
    return result


# ── MongoDB Browser ──

@query_router.get("/mongodb/databases")
async def list_mongo_databases(user: User = Depends(get_current_user)):
    from app.services.mongodb_service import mongodb_service
    if not mongodb_service.available:
        return {"databases": [], "available": False}
    return {"databases": mongodb_service.list_databases(), "available": True}

@query_router.get("/mongodb/collections/{database}")
async def list_mongo_collections(database: str, user: User = Depends(get_current_user)):
    from app.services.mongodb_service import mongodb_service
    return {"collections": mongodb_service.list_collections(database)}

@query_router.get("/mongodb/schema/{database}/{collection}")
async def get_mongo_schema(database: str, collection: str, user: User = Depends(get_current_user)):
    from app.services.mongodb_service import mongodb_service
    return {"schema": mongodb_service.infer_schema(database, collection)}


# ── History & Saved ──

@query_router.get("/history")
async def get_history(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.sql_service import sql_service
    return await sql_service.get_history(db, user_id=user.id)

@query_router.post("/save")
async def save_query(body: SaveQueryRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.sql_service import sql_service
    return await sql_service.save_query(db, user_id=user.id, name=body.name, query_text=body.query_text, source_name=body.source_name, description=body.description)

@query_router.get("/saved")
async def get_saved(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.services.sql_service import sql_service
    return await sql_service.get_saved_queries(db, user_id=user.id)
