"""
Jobs API Router — unified dashboard for Notebooks and Pipelines.
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.security import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.notebook_service import notebook_service
from app.services.pipeline_service import pipeline_service

logger = logging.getLogger(__name__)
jobs_router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

@jobs_router.get("/")
async def list_all_jobs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # 1. Fetch Notebooks
    notebooks = notebook_service.list_all()
    
    # 2. Fetch Pipelines
    pipelines = await pipeline_service.list_all(db)
    
    # 3. Fetch Users mapping
    users_result = await db.execute(select(User.id, User.username))
    user_map = {row[0]: row[1] for row in users_result.all()}
    
    jobs = []
    
    # Filter and format Notebooks
    for nb in notebooks:
        creator_id = nb.get("created_by")
        # Isolation Check
        if user.role != "admin" and creator_id != user.id:
            continue
            
        jobs.append({
            "id": nb["id"],
            "type": "notebook",
            "name": nb["name"],
            "created_by": creator_id,
            "creator_name": user_map.get(creator_id, "Unknown"),
            "created_at": nb.get("created_at") or nb.get("updated_at") or "",
            "item_count": nb.get("cell_count", 0),
        })
        
    # Filter and format Pipelines
    for p in pipelines:
        creator_id = p.get("created_by")
        # Isolation Check
        if user.role != "admin" and creator_id != user.id:
            continue
            
        jobs.append({
            "id": p["id"],
            "type": "pipeline",
            "name": p["name"],
            "created_by": creator_id,
            "creator_name": user_map.get(creator_id, "Unknown"),
            "created_at": p.get("created_at") or "",
            "item_count": len(p.get("steps", [])),
        })
        
    # Sort by created_at descending
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    return jobs
