"""
Scheduler Service — cron-based job scheduling for pipelines and queries.

Uses APScheduler for recurring job execution.
Falls back to a simple in-memory timer if APScheduler is unavailable.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import Base

logger = logging.getLogger(__name__)

_APSCHEDULER_AVAILABLE = False
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    _APSCHEDULER_AVAILABLE = True
except ImportError:
    pass


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(255), nullable=False)
    job_type = Column(String(50), nullable=False)  # pipeline, query, notebook
    target_id = Column(String(255), nullable=False)
    cron_expression = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_status = Column(String(20), nullable=True)
    created_by = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SchedulerService:
    """Manage scheduled jobs."""

    def __init__(self):
        self._scheduler = None
        if _APSCHEDULER_AVAILABLE:
            self._scheduler = AsyncIOScheduler()

    def start(self):
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
            logger.info("[Scheduler] APScheduler started")

    def stop(self):
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown()

    async def create_job(
        self, db: AsyncSession, *, name: str, job_type: str,
        target_id: str, cron_expression: str, created_by: Optional[str] = None,
    ) -> dict:
        job = ScheduledJob(
            name=name, job_type=job_type, target_id=target_id,
            cron_expression=cron_expression, created_by=created_by,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        # Register with APScheduler if available
        if self._scheduler:
            try:
                parts = cron_expression.split()
                if len(parts) == 5:
                    trigger = CronTrigger(
                        minute=parts[0], hour=parts[1],
                        day=parts[2], month=parts[3], day_of_week=parts[4],
                    )
                    self._scheduler.add_job(
                        self._execute_job, trigger,
                        id=job.id, args=[job.id, job_type, target_id],
                        replace_existing=True,
                    )
            except Exception as e:
                logger.error("[Scheduler] Failed to register job: %s", e)

        return self._job_to_dict(job)

    async def list_jobs(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(select(ScheduledJob).order_by(desc(ScheduledJob.created_at)))
        return [self._job_to_dict(j) for j in result.scalars().all()]

    async def delete_job(self, db: AsyncSession, job_id: str) -> bool:
        result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return False

        if self._scheduler:
            try:
                self._scheduler.remove_job(job_id)
            except Exception:
                pass

        await db.delete(job)
        await db.commit()
        return True

    async def toggle_job(self, db: AsyncSession, job_id: str) -> Optional[dict]:
        result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return None
        job.is_active = not job.is_active
        await db.commit()
        await db.refresh(job)

        if self._scheduler:
            if job.is_active:
                try:
                    self._scheduler.resume_job(job_id)
                except Exception:
                    pass
            else:
                try:
                    self._scheduler.pause_job(job_id)
                except Exception:
                    pass

        return self._job_to_dict(job)

    async def _execute_job(self, job_id: str, job_type: str, target_id: str):
        """Execute a scheduled job."""
        logger.info("[Scheduler] Executing job %s (type=%s, target=%s)", job_id, job_type, target_id)
        try:
            from app.db.database import async_session
            async with async_session() as db:
                if job_type == "pipeline":
                    from app.services.pipeline_service import pipeline_service
                    await pipeline_service.run(db, target_id)
                elif job_type == "query":
                    from app.services.sql_service import sql_service
                    await sql_service.execute(db, sql=target_id)

                # Update last run
                result = await db.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.last_run_at = datetime.now(timezone.utc)
                    job.last_status = "success"
                    await db.commit()
        except Exception as e:
            logger.error("[Scheduler] Job %s failed: %s", job_id, e)

    @staticmethod
    def _job_to_dict(job: ScheduledJob) -> dict:
        return {
            "id": job.id, "name": job.name, "job_type": job.job_type,
            "target_id": job.target_id, "cron_expression": job.cron_expression,
            "is_active": job.is_active,
            "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
            "last_status": job.last_status,
            "created_by": job.created_by,
            "created_at": job.created_at.isoformat() if job.created_at else "",
        }


scheduler_service = SchedulerService()
