"""
Workspace API Router — notebooks, cell execution, version history.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.notebook_service import notebook_service

logger = logging.getLogger(__name__)
workspace_router = APIRouter(prefix="/api/workspace", tags=["Workspace"])


class CreateNotebookRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

class UpdateNotebookRequest(BaseModel):
    name: Optional[str] = None
    cells: Optional[list] = None

class AddCellRequest(BaseModel):
    cell_type: str = Field(default="python", pattern="^(markdown|python|sql|mongodb)$")
    after_cell_id: Optional[str] = None


# ── Helpers ──

def _require_nb_access(nb: dict, user: User):
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")
    if user.role != "admin" and nb.get("created_by") != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this notebook")


# ── Notebooks ──

@workspace_router.get("/notebooks")
async def list_notebooks(user: User = Depends(get_current_user)):
    all_nb = notebook_service.list_all()
    if user.role != "admin":
        return [nb for nb in all_nb if nb.get("created_by") == user.id]
    return all_nb

@workspace_router.post("/notebooks", status_code=201)
async def create_notebook(body: CreateNotebookRequest, user: User = Depends(get_current_user)):
    return notebook_service.create(name=body.name, created_by=user.id)

@workspace_router.get("/notebooks/{notebook_id}")
async def get_notebook(notebook_id: str, user: User = Depends(get_current_user)):
    nb = notebook_service.get(notebook_id)
    _require_nb_access(nb, user)
    return nb

@workspace_router.put("/notebooks/{notebook_id}")
async def update_notebook(notebook_id: str, body: UpdateNotebookRequest, user: User = Depends(get_current_user)):
    nb = notebook_service.get(notebook_id)
    _require_nb_access(nb, user)
    
    data = body.model_dump(exclude_none=True)
    updated_nb = notebook_service.update(notebook_id, data)
    return updated_nb

@workspace_router.delete("/notebooks/{notebook_id}")
async def delete_notebook(notebook_id: str, user: User = Depends(get_current_user)):
    nb = notebook_service.get(notebook_id)
    _require_nb_access(nb, user)
    
    deleted = notebook_service.delete(notebook_id)
    return {"status": "deleted"}


# ── Cells ──

@workspace_router.post("/notebooks/{notebook_id}/cells")
async def add_cell(notebook_id: str, body: AddCellRequest, user: User = Depends(get_current_user)):
    nb = notebook_service.get(notebook_id)
    _require_nb_access(nb, user)
    
    cell = notebook_service.add_cell(notebook_id, cell_type=body.cell_type, after_cell_id=body.after_cell_id)
    return cell

@workspace_router.post("/notebooks/{notebook_id}/cells/{cell_id}/run")
async def run_cell(notebook_id: str, cell_id: str, user: User = Depends(get_current_user)):
    nb = notebook_service.get(notebook_id)
    _require_nb_access(nb, user)
    
    result = await notebook_service.run_cell(notebook_id, cell_id)
    if not result:
        raise HTTPException(status_code=404, detail="Notebook or cell not found")
    return result


# ── Versions ──

@workspace_router.get("/notebooks/{notebook_id}/versions")
async def get_versions(notebook_id: str, user: User = Depends(get_current_user)):
    nb = notebook_service.get(notebook_id)
    _require_nb_access(nb, user)
    
    return notebook_service.get_versions(notebook_id)
