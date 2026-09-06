"""
Governance API Router — data sources, catalog, audit trail, and permissions.

Permission model:
    Admin  → full access to all datasets, sources, and catalog entries.
    Employee → access only to catalog entries explicitly granted via the permissions table.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user, require_admin
from app.db.database import get_db
from app.db.models import User, Permission
from app.services.audit_service import audit_service
from app.services.catalog_service import catalog_service

logger = logging.getLogger(__name__)
governance_router = APIRouter(prefix="/api/governance", tags=["Governance"])


# ── Schemas ──

class DataSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    source_type: str = Field(..., pattern="^(sql|mongodb|csv|databricks|excel|image)$")
    description: str = ""
    connection_config: Optional[dict] = None

class CatalogEntryCreate(BaseModel):
    data_source_id: str
    table_name: str
    schema_json: Optional[list] = None
    description: str = ""
    tags: str = ""

class PermissionGrant(BaseModel):
    user_id: str
    catalog_entry_id: int
    access_level: str = Field(default="read", pattern="^(read|write|admin)$")


# ── Helpers ──

async def _get_permitted_entry_ids(db: AsyncSession, user: User) -> Optional[set[int]]:
    """Return the set of catalog_entry IDs this user can access.
    Returns None for admins (meaning all access)."""
    if user.role == "admin":
        return None  # Admin sees everything
    result = await db.execute(
        select(Permission.resource_id).where(
            Permission.user_id == user.id,
            Permission.resource_type == "catalog_entry",
        )
    )
    return {int(row[0]) for row in result.all()}


# ── Data Sources ──

@governance_router.get("/sources")
async def list_sources(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    all_sources = await catalog_service.list_sources(db)
    if user.role == "admin":
        return all_sources
    # For employees, only return sources that have at least one permitted entry
    permitted_ids = await _get_permitted_entry_ids(db, user)
    if not permitted_ids:
        return []
    all_entries = await catalog_service.list_entries(db)
    permitted_source_ids = {e["data_source_id"] for e in all_entries if e["id"] in permitted_ids}
    return [s for s in all_sources if s["id"] in permitted_source_ids]

@governance_router.post("/sources", status_code=201)
async def create_source(body: DataSourceCreate, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await catalog_service.create_source(
        db, name=body.name, source_type=body.source_type,
        connection_config=body.connection_config, description=body.description,
        created_by=user.id,
    )
    await audit_service.log(db, user_id=user.id, action="create_source", resource_type="datasource", resource_id=result["id"])
    return result

@governance_router.delete("/sources/{source_id}")
async def delete_source(source_id: str, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    deleted = await catalog_service.delete_source(db, source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Data source not found")
    await audit_service.log(db, user_id=user.id, action="delete_source", resource_type="datasource", resource_id=source_id)
    return {"status": "deleted"}


# ── Catalog ──

@governance_router.get("/catalog")
async def list_catalog(
    source_id: Optional[str] = None, search: Optional[str] = None, tag: Optional[str] = None,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    entries = await catalog_service.list_entries(db, source_id=source_id, search=search, tag=tag)
    if user.role == "admin":
        return entries
    # Filter to only permitted entries for employees
    permitted_ids = await _get_permitted_entry_ids(db, user)
    return [e for e in entries if e["id"] in (permitted_ids or set())]

@governance_router.post("/catalog", status_code=201)
async def add_catalog_entry(body: CatalogEntryCreate, user: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return await catalog_service.add_entry(
        db, data_source_id=body.data_source_id, table_name=body.table_name,
        schema_json=body.schema_json, description=body.description, tags=body.tags, updated_by=user.id,
    )

@governance_router.get("/catalog/{entry_id}")
async def get_catalog_entry(entry_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Check permission for employees
    if user.role != "admin":
        permitted_ids = await _get_permitted_entry_ids(db, user)
        if entry_id not in (permitted_ids or set()):
            raise HTTPException(status_code=403, detail="You don't have access to this dataset")
    entry = await catalog_service.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog entry not found")
    return entry

@governance_router.get("/catalog/{entry_id}/lineage")
async def get_lineage(entry_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    entry = await catalog_service.get_entry(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog entry not found")
    return entry.get("lineage", {})


# ═══════════════════════════════════════════════
# Permissions — Admin manages dataset access
# ═══════════════════════════════════════════════

@governance_router.get("/permissions/{user_id}")
async def get_user_permissions(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all catalog entry permissions for a specific user."""
    result = await db.execute(
        select(Permission).where(
            Permission.user_id == user_id,
            Permission.resource_type == "catalog_entry",
        )
    )
    perms = result.scalars().all()
    return [
        {
            "id": p.id,
            "user_id": p.user_id,
            "catalog_entry_id": int(p.resource_id),
            "access_level": p.access_level,
            "granted_at": p.granted_at.isoformat() if p.granted_at else "",
            "granted_by": p.granted_by,
        }
        for p in perms
    ]


@governance_router.post("/permissions", status_code=201)
async def grant_permission(
    body: PermissionGrant,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Grant a user access to a catalog entry."""
    # Check user exists
    user_res = await db.execute(select(User).where(User.id == body.user_id))
    target_user = user_res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check catalog entry exists
    entry = await catalog_service.get_entry(db, body.catalog_entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog entry not found")

    # Check if already granted
    existing = await db.execute(
        select(Permission).where(
            Permission.user_id == body.user_id,
            Permission.resource_type == "catalog_entry",
            Permission.resource_id == str(body.catalog_entry_id),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Permission already granted")

    perm = Permission(
        user_id=body.user_id,
        resource_type="catalog_entry",
        resource_id=str(body.catalog_entry_id),
        access_level=body.access_level,
        granted_by=admin.id,
    )
    db.add(perm)
    await db.commit()
    await db.refresh(perm)

    await audit_service.log(
        db, user_id=admin.id, action="grant_permission",
        resource_type="catalog_entry", resource_id=str(body.catalog_entry_id),
        details={"granted_to": target_user.username, "access_level": body.access_level},
    )

    # ── Native MySQL Provisioning ──
    try:
        if entry.get("data_source_id") == "sql" or "MySQL" in entry.get("description", ""):
            from app.services.sql_service import sql_service
            MYSQL_URL = "mysql+aiomysql://root:root@localhost:3307/mysql"
            table = entry["table_name"]
            uname = target_user.username
            # Create user if not exists and grant access
            await sql_service.execute(db, sql=f"CREATE USER IF NOT EXISTS '{uname}'@'%' IDENTIFIED BY 'password';", connection_string=MYSQL_URL)
            await sql_service.execute(db, sql=f"GRANT SELECT ON mysql.{table} TO '{uname}'@'%';", connection_string=MYSQL_URL)
            await sql_service.execute(db, sql="FLUSH PRIVILEGES;", connection_string=MYSQL_URL)
            logger.info(f"Granted native MySQL SELECT on {table} to {uname}")
    except Exception as e:
        logger.error(f"Failed to grant native MySQL permission: {e}")

    return {
        "id": perm.id,
        "user_id": perm.user_id,
        "catalog_entry_id": body.catalog_entry_id,
        "access_level": perm.access_level,
    }


@governance_router.delete("/permissions/{perm_id}")
async def revoke_permission(
    perm_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a user's access to a catalog entry."""
    result = await db.execute(select(Permission).where(Permission.id == perm_id))
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")

    user_res = await db.execute(select(User).where(User.id == perm.user_id))
    target_user = user_res.scalar_one_or_none()

    await audit_service.log(
        db, user_id=admin.id, action="revoke_permission",
        resource_type="catalog_entry", resource_id=perm.resource_id,
        details={"revoked_from": target_user.username if target_user else perm.user_id},
    )

    # ── Native MySQL Revocation ──
    try:
        entry = await catalog_service.get_entry(db, int(perm.resource_id))
        if entry and target_user and (entry.get("data_source_id") == "sql" or "MySQL" in entry.get("description", "")):
            from app.services.sql_service import sql_service
            MYSQL_URL = "mysql+aiomysql://root:root@localhost:3307/mysql"
            table = entry["table_name"]
            uname = target_user.username
            await sql_service.execute(db, sql=f"REVOKE SELECT ON mysql.{table} FROM '{uname}'@'%';", connection_string=MYSQL_URL)
            await sql_service.execute(db, sql="FLUSH PRIVILEGES;", connection_string=MYSQL_URL)
            logger.info(f"Revoked native MySQL SELECT on {table} from {uname}")
    except Exception as e:
        logger.error(f"Failed to revoke native MySQL permission: {e}")

    await db.delete(perm)
    await db.commit()
    return {"status": "revoked"}


# ── Audit ──

@governance_router.get("/audit")
async def get_audit_trail(
    user_id: Optional[str] = None, action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = Query(default=100, le=500), offset: int = Query(default=0, ge=0),
    admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db),
):
    return await audit_service.get_trail(db, user_id=user_id, action=action, resource_type=resource_type, limit=limit, offset=offset)

@governance_router.get("/audit/summary")
async def get_audit_summary(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    return await audit_service.get_actions_summary(db)
