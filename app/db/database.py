"""
SQLAlchemy Async Database Engine & Session Factory.

Uses SQLite via aiosqlite for zero-config persistence.
Database file: data/eurekax.db
"""

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

# ── Database path ──
DB_DIR = Path("data")
DB_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite+aiosqlite:///{DB_DIR / 'eurekax.db'}"

# ── Engine ──
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

# ── Session factory ──
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base model ──
class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


# ── Lifecycle helpers ──

async def init_db() -> None:
    """Create all tables that don't exist yet."""
    # Import ALL models so Base.metadata knows about every table
    import app.db.models  # noqa: F401 — User, Permission, AuditLog
    import app.services.catalog_service  # noqa: F401 — DataSource, CatalogEntry
    import app.services.sql_service  # noqa: F401 — QueryHistory, SavedQuery
    import app.services.pipeline_service  # noqa: F401 — Pipeline, PipelineRun
    import app.services.scheduler_service  # noqa: F401 — ScheduledJob
    import app.security.anomaly_detector  # noqa: F401 — SecurityAlert

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[DB] Tables initialized (SQLite: %s)", DATABASE_URL)


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
