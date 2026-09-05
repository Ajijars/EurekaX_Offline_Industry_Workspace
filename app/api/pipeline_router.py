"""
Pipeline API Router — ETL pipelines, execution, scheduling.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user, require_admin
from app.db.database import get_db
from app.db.models import User
from app.services.pipeline_service import pipeline_service
from app.services.scheduler_service import scheduler_service

logger = logging.getLogger(__name__)
pipeline_router = APIRouter(prefix="/api/pipelines", tags=["Pipelines"])


class CreatePipelineRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    steps: list[dict] = Field(..., min_length=1)

class CreateScheduleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    job_type: str = Field(..., pattern="^(pipeline|query|notebook)$")
    target_id: str
    cron_expression: str = Field(..., min_length=9)


# ── Helpers ──

async def _require_pipe_access(p: dict, user: User):
    if not p:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if user.role != "admin" and p.get("created_by") != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this pipeline")


# ── Pipelines ──

@pipeline_router.get("/")
async def list_pipelines(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    all_p = await pipeline_service.list_all(db)
    if user.role != "admin":
        return [p for p in all_p if p.get("created_by") == user.id]
    return all_p

@pipeline_router.post("/", status_code=201)
async def create_pipeline(body: CreatePipelineRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await pipeline_service.create(db, name=body.name, steps=body.steps, description=body.description, created_by=user.id)

@pipeline_router.get("/{pipeline_id}")
async def get_pipeline(pipeline_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    p = await pipeline_service.get(db, pipeline_id)
    await _require_pipe_access(p, user)
    return p

@pipeline_router.delete("/{pipeline_id}")
async def delete_pipeline(pipeline_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    p = await pipeline_service.get(db, pipeline_id)
    await _require_pipe_access(p, user)
    
    deleted = await pipeline_service.delete(db, pipeline_id)
    return {"status": "deleted"}

@pipeline_router.post("/{pipeline_id}/run")
async def run_pipeline(pipeline_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    p = await pipeline_service.get(db, pipeline_id)
    await _require_pipe_access(p, user)
    
    result = await pipeline_service.run(db, pipeline_id, triggered_by=user.id)
    if not result.get("success", True) and "not found" in result.get("error", "").lower():
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return result

@pipeline_router.get("/{pipeline_id}/runs")
async def get_runs(pipeline_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    p = await pipeline_service.get(db, pipeline_id)
    await _require_pipe_access(p, user)
    
    return await pipeline_service.get_runs(db, pipeline_id)


# ── Schedules ──

@pipeline_router.get("/schedules/all")
async def list_schedules(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    all_s = await scheduler_service.list_jobs(db)
    if user.role != "admin":
        return [s for s in all_s if s.get("created_by") == user.id]
    return all_s

@pipeline_router.post("/schedules", status_code=201)
async def create_schedule(body: CreateScheduleRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Verify they have access to the target pipeline/notebook before scheduling it
    if body.job_type == "pipeline":
        p = await pipeline_service.get(db, body.target_id)
        await _require_pipe_access(p, user)
    
    return await scheduler_service.create_job(db, name=body.name, job_type=body.job_type, target_id=body.target_id, cron_expression=body.cron_expression, created_by=user.id)

@pipeline_router.delete("/schedules/{job_id}")
async def delete_schedule(job_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # For simplicity, if they aren't admin, they can only delete their own schedules
    all_s = await scheduler_service.list_jobs(db)
    job = next((s for s in all_s if s["id"] == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if user.role != "admin" and job.get("created_by") != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    await scheduler_service.delete_job(db, job_id)
    return {"status": "deleted"}

@pipeline_router.put("/schedules/{job_id}/toggle")
async def toggle_schedule(job_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    all_s = await scheduler_service.list_jobs(db)
    job = next((s for s in all_s if s["id"] == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if user.role != "admin" and job.get("created_by") != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    return await scheduler_service.toggle_job(db, job_id)
