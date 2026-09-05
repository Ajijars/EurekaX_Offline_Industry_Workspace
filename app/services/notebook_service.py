"""
Notebook Service — cell-based notebook management.

Notebooks are stored as JSON files in workspace/notebooks/.
Each notebook contains ordered cells (markdown, python, sql, mongodb).
Supports version history via snapshot files.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


def _notebooks_dir() -> Path:
    settings = get_settings()
    d = Path(settings.WORKSPACE_DIR) / "notebooks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _versions_dir(notebook_id: str) -> Path:
    d = _notebooks_dir() / f".versions_{notebook_id}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _new_cell(cell_type: str = "markdown", source: str = "") -> dict:
    return {
        "id": uuid.uuid4().hex[:8],
        "type": cell_type,
        "source": source,
        "output": "",
        "status": "idle",
    }


class NotebookService:
    """CRUD for cell-based notebooks."""

    def create(self, *, name: str, created_by: Optional[str] = None) -> dict:
        nb_id = uuid.uuid4().hex[:12]
        notebook = {
            "id": nb_id,
            "name": name,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "cells": [_new_cell("markdown", f"# {name}\n\nStart writing here...")],
        }
        path = _notebooks_dir() / f"{nb_id}.json"
        path.write_text(json.dumps(notebook, indent=2), encoding="utf-8")
        logger.info("[Notebook] Created %s: %s", nb_id, name)
        return notebook

    def list_all(self) -> list[dict]:
        notebooks = []
        for path in sorted(_notebooks_dir().glob("*.json")):
            try:
                nb = json.loads(path.read_text(encoding="utf-8"))
                notebooks.append({
                    "id": nb["id"],
                    "name": nb["name"],
                    "created_by": nb.get("created_by"),
                    "created_at": nb.get("created_at", ""),
                    "updated_at": nb.get("updated_at", ""),
                    "cell_count": len(nb.get("cells", [])),
                })
            except Exception:
                continue
        return notebooks

    def get(self, notebook_id: str) -> Optional[dict]:
        path = _notebooks_dir() / f"{notebook_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def update(self, notebook_id: str, data: dict) -> Optional[dict]:
        path = _notebooks_dir() / f"{notebook_id}.json"
        if not path.exists():
            return None

        nb = json.loads(path.read_text(encoding="utf-8"))

        # Save version snapshot before update
        self._save_version(notebook_id, nb)

        if "name" in data:
            nb["name"] = data["name"]
        if "cells" in data:
            nb["cells"] = data["cells"]
        nb["updated_at"] = datetime.now(timezone.utc).isoformat()

        path.write_text(json.dumps(nb, indent=2), encoding="utf-8")
        return nb

    def delete(self, notebook_id: str) -> bool:
        path = _notebooks_dir() / f"{notebook_id}.json"
        if not path.exists():
            return False
        path.unlink()
        return True

    def add_cell(self, notebook_id: str, cell_type: str = "python", after_cell_id: Optional[str] = None) -> Optional[dict]:
        nb = self.get(notebook_id)
        if not nb:
            return None

        cell = _new_cell(cell_type)
        cells = nb.get("cells", [])

        if after_cell_id:
            idx = next((i for i, c in enumerate(cells) if c["id"] == after_cell_id), len(cells))
            cells.insert(idx + 1, cell)
        else:
            cells.append(cell)

        nb["cells"] = cells
        self.update(notebook_id, nb)
        return cell

    async def run_cell(self, notebook_id: str, cell_id: str) -> Optional[dict]:
        """Execute a cell and return the updated cell with output."""
        nb = self.get(notebook_id)
        if not nb:
            return None

        cell = next((c for c in nb["cells"] if c["id"] == cell_id), None)
        if not cell:
            return None

        cell["status"] = "running"
        start = time.monotonic()

        try:
            if cell["type"] == "python":
                from app.agents.tools import execute_python
                result = await execute_python(cell["source"])
                cell["output"] = result.get("stdout", "") + result.get("stderr", "")
                cell["status"] = "success" if result.get("success") else "error"

            elif cell["type"] == "sql":
                from app.db.database import async_session
                from app.services.sql_service import sql_service
                async with async_session() as db:
                    result = await sql_service.execute(db, sql=cell["source"])
                    if result["success"]:
                        cell["output"] = json.dumps(result["rows"][:20], indent=2, default=str)
                        cell["status"] = "success"
                    else:
                        cell["output"] = result.get("error", "Query failed")
                        cell["status"] = "error"

            elif cell["type"] == "markdown":
                cell["output"] = cell["source"]
                cell["status"] = "success"

            else:
                cell["output"] = f"Unsupported cell type: {cell['type']}"
                cell["status"] = "error"

        except Exception as e:
            cell["output"] = f"Error: {e}"
            cell["status"] = "error"

        elapsed_ms = int((time.monotonic() - start) * 1000)
        cell["duration_ms"] = elapsed_ms

        # Save updated notebook
        self.update(notebook_id, nb)
        return cell

    def get_versions(self, notebook_id: str) -> list[dict]:
        vdir = _versions_dir(notebook_id)
        versions = []
        for path in sorted(vdir.glob("*.json"), reverse=True):
            try:
                v = json.loads(path.read_text(encoding="utf-8"))
                versions.append({
                    "version_id": path.stem,
                    "saved_at": v.get("_version_saved_at", ""),
                    "cell_count": len(v.get("cells", [])),
                })
            except Exception:
                continue
        return versions[:20]

    def _save_version(self, notebook_id: str, nb: dict) -> None:
        vdir = _versions_dir(notebook_id)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        snapshot = {**nb, "_version_saved_at": datetime.now(timezone.utc).isoformat()}
        path = vdir / f"{ts}.json"
        path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


notebook_service = NotebookService()
