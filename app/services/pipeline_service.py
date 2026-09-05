"""
Pipeline Service — ETL pipeline definition and execution.

Pipelines are ordered sequences of steps:
    - query: Execute SQL/MongoDB queries
    - transform: Run Python transformation code
    - notify: Log completion

Pipelines and run history are stored in SQLite.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import Base

logger = logging.getLogger(__name__)


class Pipeline(Base):
    __tablename__ = "pipelines"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    steps_json = Column(Text, nullable=False)  # JSON array of step definitions
    created_by = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_id = Column(String(32), nullable=False)
    status = Column(String(20), nullable=False)  # running, success, failed
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    step_results_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    triggered_by = Column(String(32), nullable=True)


class PipelineService:
    """CRUD and execution for ETL pipelines."""

    async def create(
        self, db: AsyncSession, *, name: str, steps: list[dict],
        description: str = "", created_by: Optional[str] = None,
    ) -> dict:
        pipeline = Pipeline(
            name=name,
            description=description,
            steps_json=json.dumps(steps),
            created_by=created_by,
        )
        db.add(pipeline)
        await db.commit()
        await db.refresh(pipeline)
        return self._pipeline_to_dict(pipeline)

    async def list_all(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(select(Pipeline).order_by(desc(Pipeline.created_at)))
        return [self._pipeline_to_dict(p) for p in result.scalars().all()]

    async def get(self, db: AsyncSession, pipeline_id: str) -> Optional[dict]:
        result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
        p = result.scalar_one_or_none()
        return self._pipeline_to_dict(p) if p else None

    async def delete(self, db: AsyncSession, pipeline_id: str) -> bool:
        result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
        p = result.scalar_one_or_none()
        if not p:
            return False
        await db.delete(p)
        await db.commit()
        return True

    async def run(
        self, db: AsyncSession, pipeline_id: str, triggered_by: Optional[str] = None,
    ) -> dict:
        """Execute a pipeline's steps sequentially."""
        pipeline = await self.get(db, pipeline_id)
        if not pipeline:
            return {"success": False, "error": "Pipeline not found"}

        run = PipelineRun(
            pipeline_id=pipeline_id,
            status="running",
            triggered_by=triggered_by,
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        steps = pipeline.get("steps", [])
        step_results = []
        start = time.monotonic()

        try:
            for i, step in enumerate(steps):
                step_start = time.monotonic()
                step_result = await self._execute_step(db, step)
                step_result["step_index"] = i
                step_result["duration_ms"] = int((time.monotonic() - step_start) * 1000)
                step_results.append(step_result)

                if not step_result.get("success", False):
                    raise RuntimeError(
                        f"Step {i} ({step.get('type', 'unknown')}) failed: {step_result.get('error', '')}"
                    )

            run.status = "success"
        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            logger.error("[Pipeline] Run failed: %s", e)

        run.finished_at = datetime.now(timezone.utc)
        run.duration_ms = int((time.monotonic() - start) * 1000)
        run.step_results_json = json.dumps(step_results, default=str)
        await db.commit()

        return {
            "run_id": run.id,
            "pipeline_id": pipeline_id,
            "status": run.status,
            "duration_ms": run.duration_ms,
            "step_results": step_results,
            "error": run.error_message,
        }

    async def _execute_step(self, db: AsyncSession, step: dict) -> dict:
        """Execute a single pipeline step."""
        step_type = step.get("type", "unknown")

        if step_type == "query":
            from app.services.sql_service import sql_service
            result = await sql_service.execute(
                db, sql=step.get("sql", ""), source_name=step.get("source", "local"),
            )
            return {"success": result.get("success", False), "type": "query", "row_count": result.get("row_count", 0), "error": result.get("error")}

        elif step_type == "python":
            from app.agents.tools import execute_python
            result = await execute_python(step.get("code", ""))
            return {"success": result.get("success", False), "type": "python", "output": result.get("stdout", "")[:1000], "error": result.get("stderr")}

        elif step_type == "notify":
            logger.info("[Pipeline] Notify: %s", step.get("message", "Step complete"))
            return {"success": True, "type": "notify", "message": step.get("message", "")}

        return {"success": False, "type": step_type, "error": f"Unknown step type: {step_type}"}

    async def get_runs(self, db: AsyncSession, pipeline_id: str, limit: int = 20) -> list[dict]:
        result = await db.execute(
            select(PipelineRun)
            .where(PipelineRun.pipeline_id == pipeline_id)
            .order_by(desc(PipelineRun.started_at))
            .limit(limit)
        )
        return [
            {
                "id": r.id, "pipeline_id": r.pipeline_id, "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else "",
                "finished_at": r.finished_at.isoformat() if r.finished_at else "",
                "duration_ms": r.duration_ms, "error": r.error_message,
                "step_results": json.loads(r.step_results_json) if r.step_results_json else [],
            }
            for r in result.scalars().all()
        ]

    @staticmethod
    def _pipeline_to_dict(p: Pipeline) -> dict:
        return {
            "id": p.id, "name": p.name, "description": p.description or "",
            "steps": json.loads(p.steps_json) if p.steps_json else [],
            "created_by": p.created_by,
            "created_at": p.created_at.isoformat() if p.created_at else "",
        }


pipeline_service = PipelineService()
