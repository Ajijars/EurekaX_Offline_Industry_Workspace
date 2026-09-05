"""
Catalog Service — data source management and metadata catalog.

Manages connections to data sources (SQL, MongoDB, CSV, Databricks) and
maintains a searchable catalog of tables/collections with schema info and lineage.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import Base

logger = logging.getLogger(__name__)


# ── Additional DB Models for Catalog ──

class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(255), nullable=False, unique=True)
    source_type = Column(String(50), nullable=False)  # sql, mongodb, csv, databricks
    connection_config = Column(Text, nullable=True)    # JSON (encrypted in prod)
    description = Column(Text, nullable=True)
    created_by = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CatalogEntry(Base):
    __tablename__ = "catalog_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_source_id = Column(String(32), nullable=False)
    table_name = Column(String(255), nullable=False)
    schema_json = Column(Text, nullable=True)   # JSON: [{name, type, nullable}]
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)           # comma-separated
    lineage_json = Column(Text, nullable=True)   # JSON: {upstream: [], downstream: []}
    row_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_by = Column(String(32), nullable=True)


class CatalogService:
    """CRUD for data sources and catalog entries."""

    # ── Data Sources ──

    async def create_source(
        self, db: AsyncSession, *, name: str, source_type: str,
        connection_config: Optional[dict] = None, description: str = "",
        created_by: Optional[str] = None,
    ) -> dict:
        src = DataSource(
            name=name,
            source_type=source_type,
            connection_config=json.dumps(connection_config) if connection_config else None,
            description=description,
            created_by=created_by,
        )
        db.add(src)
        await db.commit()
        await db.refresh(src)
        return self._source_to_dict(src)

    async def list_sources(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(select(DataSource).order_by(DataSource.name))
        return [self._source_to_dict(s) for s in result.scalars().all()]

    async def get_source(self, db: AsyncSession, source_id: str) -> Optional[dict]:
        result = await db.execute(select(DataSource).where(DataSource.id == source_id))
        src = result.scalar_one_or_none()
        return self._source_to_dict(src) if src else None

    async def delete_source(self, db: AsyncSession, source_id: str) -> bool:
        result = await db.execute(select(DataSource).where(DataSource.id == source_id))
        src = result.scalar_one_or_none()
        if not src:
            return False
        await db.delete(src)
        await db.commit()
        return True

    # ── Catalog Entries ──

    async def add_entry(
        self, db: AsyncSession, *, data_source_id: str, table_name: str,
        schema_json: Optional[list] = None, description: str = "",
        tags: str = "", updated_by: Optional[str] = None,
    ) -> dict:
        entry = CatalogEntry(
            data_source_id=data_source_id,
            table_name=table_name,
            schema_json=json.dumps(schema_json) if schema_json else None,
            description=description,
            tags=tags,
            updated_by=updated_by,
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return self._entry_to_dict(entry)

    async def list_entries(
        self, db: AsyncSession, *, source_id: Optional[str] = None,
        search: Optional[str] = None, tag: Optional[str] = None,
    ) -> list[dict]:
        query = select(CatalogEntry).order_by(desc(CatalogEntry.created_at))
        if source_id:
            query = query.where(CatalogEntry.data_source_id == source_id)
        if search:
            query = query.where(CatalogEntry.table_name.ilike(f"%{search}%"))
        if tag:
            query = query.where(CatalogEntry.tags.ilike(f"%{tag}%"))
        result = await db.execute(query)
        return [self._entry_to_dict(e) for e in result.scalars().all()]

    async def get_entry(self, db: AsyncSession, entry_id: int) -> Optional[dict]:
        result = await db.execute(select(CatalogEntry).where(CatalogEntry.id == entry_id))
        entry = result.scalar_one_or_none()
        return self._entry_to_dict(entry) if entry else None

    async def update_lineage(
        self, db: AsyncSession, entry_id: int, lineage: dict,
    ) -> Optional[dict]:
        result = await db.execute(select(CatalogEntry).where(CatalogEntry.id == entry_id))
        entry = result.scalar_one_or_none()
        if not entry:
            return None
        entry.lineage_json = json.dumps(lineage)
        await db.commit()
        await db.refresh(entry)
        return self._entry_to_dict(entry)

    # ── Serializers ──

    @staticmethod
    def _source_to_dict(src: DataSource) -> dict:
        return {
            "id": src.id,
            "name": src.name,
            "source_type": src.source_type,
            "description": src.description or "",
            "created_by": src.created_by,
            "created_at": src.created_at.isoformat() if src.created_at else "",
        }

    @staticmethod
    def _entry_to_dict(entry: CatalogEntry) -> dict:
        return {
            "id": entry.id,
            "data_source_id": entry.data_source_id,
            "table_name": entry.table_name,
            "schema": json.loads(entry.schema_json) if entry.schema_json else [],
            "description": entry.description or "",
            "tags": entry.tags.split(",") if entry.tags else [],
            "lineage": json.loads(entry.lineage_json) if entry.lineage_json else {},
            "row_count": entry.row_count,
            "created_at": entry.created_at.isoformat() if entry.created_at else "",
        }


catalog_service = CatalogService()
