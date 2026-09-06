"""
SQL Service — generic SQL executor with query history and result caching.

Supports SQLite (local), and Databricks (via existing service).
Extensible for PostgreSQL/MySQL via SQLAlchemy connection strings.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, select, desc, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.database import Base

logger = logging.getLogger(__name__)


# ── Query History Model ──

class QueryHistory(Base):
    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), nullable=True)
    source_name = Column(String(255), nullable=False)
    query_text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False)  # success, error
    row_count = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SavedQuery(Base):
    __tablename__ = "saved_queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), nullable=True)
    name = Column(String(255), nullable=False)
    query_text = Column(Text, nullable=False)
    source_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SQLService:
    """Execute SQL queries against various data sources."""

    async def execute(
        self, db: AsyncSession, *, sql: str, source_name: str = "local",
        connection_string: Optional[str] = None,
        user_id: Optional[str] = None, max_rows: int = 500,
    ) -> dict:
        """Execute a SQL query and return results."""
        start = time.monotonic()

        try:
            if source_name == "databricks":
                return await self._execute_databricks(sql, max_rows)

            if connection_string:
                # Dynamic external SQL connection (e.g., MySQL, Postgres)
                engine = create_async_engine(connection_string, echo=False)
                async with engine.begin() as conn:
                    result = await conn.execute(text(sql))
                    if result.returns_rows:
                        columns = list(result.keys())
                        rows = [dict(zip(columns, row)) for row in result.fetchmany(max_rows)]
                        row_count = len(rows)
                    else:
                        columns = []
                        rows = []
                        row_count = result.rowcount or 0
                await engine.dispose()
            else:
                # Default: local SQLite execution
                result = await db.execute(text(sql))

                if result.returns_rows:
                    columns = list(result.keys())
                    rows = [dict(zip(columns, row)) for row in result.fetchmany(max_rows)]
                    row_count = len(rows)
                else:
                    columns = []
                    rows = []
                    row_count = result.rowcount or 0
                await db.commit()

            elapsed_ms = int((time.monotonic() - start) * 1000)

            # Save to history
            await self._save_history(
                db, user_id=user_id, source_name=source_name,
                query_text=sql, status="success",
                row_count=row_count, duration_ms=elapsed_ms,
            )

            return {
                "success": True,
                "columns": columns,
                "rows": rows,
                "row_count": row_count,
                "duration_ms": elapsed_ms,
                "truncated": row_count >= max_rows,
            }

        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            await self._save_history(
                db, user_id=user_id, source_name=source_name,
                query_text=sql, status="error",
                duration_ms=elapsed_ms, error_message=str(e),
            )
            logger.error("[SQL] Query failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "columns": [],
                "rows": [],
                "duration_ms": elapsed_ms,
            }

    async def _execute_databricks(self, sql: str, max_rows: int) -> dict:
        """Delegate to the Databricks service."""
        from app.services.databricks_service import databricks_service
        import asyncio
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: databricks_service.execute_query(sql, max_rows=max_rows)
        )
        return result

    async def _save_history(self, db: AsyncSession, **kwargs) -> None:
        try:
            db.add(QueryHistory(**kwargs))
            await db.commit()
        except Exception:
            pass  # Don't fail queries because of history logging

    async def get_history(
        self, db: AsyncSession, *, user_id: Optional[str] = None, limit: int = 50,
    ) -> list[dict]:
        query = select(QueryHistory).order_by(desc(QueryHistory.created_at)).limit(limit)
        if user_id:
            query = query.where(QueryHistory.user_id == user_id)
        result = await db.execute(query)
        return [
            {
                "id": h.id, "source_name": h.source_name,
                "query_text": h.query_text, "status": h.status,
                "row_count": h.row_count, "duration_ms": h.duration_ms,
                "error_message": h.error_message,
                "created_at": h.created_at.isoformat() if h.created_at else "",
            }
            for h in result.scalars().all()
        ]

    async def save_query(
        self, db: AsyncSession, *, user_id: str, name: str,
        query_text: str, source_name: str = "", description: str = "",
    ) -> dict:
        sq = SavedQuery(
            user_id=user_id, name=name, query_text=query_text,
            source_name=source_name, description=description,
        )
        db.add(sq)
        await db.commit()
        await db.refresh(sq)
        return {"id": sq.id, "name": sq.name, "query_text": sq.query_text}

    async def get_saved_queries(
        self, db: AsyncSession, *, user_id: str,
    ) -> list[dict]:
        result = await db.execute(
            select(SavedQuery).where(SavedQuery.user_id == user_id).order_by(desc(SavedQuery.created_at))
        )
        return [
            {"id": s.id, "name": s.name, "query_text": s.query_text,
             "source_name": s.source_name, "description": s.description or ""}
            for s in result.scalars().all()
        ]


sql_service = SQLService()
