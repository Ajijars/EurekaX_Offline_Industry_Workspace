"""
Agent Tools – callable functions available to all specialized agents.

Available tools:
    search_documents   – RAG vector search via Qdrant
    read_file          – Read text content of a local file
    write_file         – Write text content to a local file
    list_files         – List files in a directory
    analyze_data       – Load CSV/JSON/Excel and return summary statistics
    execute_python     – Run Python code in Docker sandbox (falls back to subprocess)
    extract_image_text – OCR text extraction using PaddleOCR (falls back to pytesseract)
    query_databricks   – Run SQL against Databricks Delta Lake tables
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import textwrap
from pathlib import Path

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# RAG Tool
# ──────────────────────────────────────────────

async def search_documents(query: str, top_k: int = 5) -> dict:
    """
    Search indexed documents in Qdrant and return the top-k relevant chunks.

    Args:
        query:  The search query string.
        top_k:  Number of results to return.

    Returns:
        Dict with 'results' list of chunks and 'count'.
    """
    try:
        from app.services.embedding_service import embedding_service
        from app.services.vector_service import vector_service

        query_vector = embedding_service.embed_query(query)
        results = await vector_service.search(query_vector=query_vector, top_k=top_k)

        return {
            "success": True,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error(f"[search_documents] Error: {e}")
        return {"success": False, "error": str(e), "results": []}


# ──────────────────────────────────────────────
# File Tools
# ──────────────────────────────────────────────

def _safe_path(base_dir: str, relative_path: str) -> Path:
    """Resolve and validate that path stays within base_dir (path traversal guard)."""
    base = Path(base_dir).resolve()
    target = (base / relative_path).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError(f"Path traversal detected: {relative_path!r}")
    return target


async def read_file(file_path: str, workspace_dir: str = "workspace") -> dict:
    """
    Read a file from the workspace or an absolute path.

    Args:
        file_path:     Relative (to workspace) or absolute path.
        workspace_dir: Base workspace directory.

    Returns:
        Dict with 'content' string.
    """
    try:
        # Accept absolute paths for uploaded files too
        path = Path(file_path)
        if not path.is_absolute():
            path = _safe_path(workspace_dir, file_path)

        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        content = path.read_text(encoding="utf-8", errors="replace")
        return {
            "success": True,
            "path": str(path),
            "content": content[:10_000],  # cap at 10k chars
            "size_bytes": path.stat().st_size,
        }
    except Exception as e:
        logger.error(f"[read_file] Error: {e}")
        return {"success": False, "error": str(e)}


async def write_file(file_path: str, content: str, workspace_dir: str = "workspace") -> dict:
    """
    Write text content to a file in the workspace.

    Args:
        file_path:     Relative path within workspace.
        content:       Text content to write.
        workspace_dir: Base workspace directory.

    Returns:
        Dict with 'path' of written file.
    """
    try:
        path = _safe_path(workspace_dir, file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"success": True, "path": str(path), "size_bytes": len(content.encode())}
    except Exception as e:
        logger.error(f"[write_file] Error: {e}")
        return {"success": False, "error": str(e)}


async def list_files(directory: str = ".", workspace_dir: str = "workspace") -> dict:
    """
    List files and directories within a workspace directory.

    Args:
        directory:     Relative path to list (default: workspace root).
        workspace_dir: Base workspace directory.

    Returns:
        Dict with 'entries' list of {name, type, size_bytes}.
    """
    try:
        # Allow listing uploads too
        if directory in ("uploads", "./uploads"):
            path = Path("uploads").resolve()
        else:
            path = _safe_path(workspace_dir, directory)

        if not path.exists():
            return {"success": False, "error": f"Directory not found: {directory}"}

        entries = []
        for item in sorted(path.iterdir()):
            entry = {
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
            }
            if item.is_file():
                entry["size_bytes"] = item.stat().st_size
            entries.append(entry)

        return {"success": True, "path": str(path), "entries": entries, "count": len(entries)}
    except Exception as e:
        logger.error(f"[list_files] Error: {e}")
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────
# Data Analysis Tool
# ──────────────────────────────────────────────

async def analyze_data(file_path: str) -> dict:
    """
    Load a CSV, JSON, or Excel file and return descriptive statistics.

    Args:
        file_path: Absolute or relative path to the data file.

    Returns:
        Dict with shape, columns, dtypes, descriptive stats, and sample rows.
    """
    try:
        import pandas as pd

        path = Path(file_path)
        if not path.exists():
            # Try uploads dir
            alt = Path("uploads") / path.name
            if alt.exists():
                path = alt
            else:
                return {"success": False, "error": f"File not found: {file_path}"}

        suffix = path.suffix.lower()

        if suffix == ".csv":
            df = pd.read_csv(path)
        elif suffix in (".xls", ".xlsx"):
            df = pd.read_excel(path)
        elif suffix == ".json":
            df = pd.read_json(path)
        else:
            return {"success": False, "error": f"Unsupported format: {suffix}"}

        stats = df.describe(include="all").to_dict()
        # Convert numpy types to Python natives for JSON serialisation
        def _clean(v):
            try:
                import numpy as np
                if isinstance(v, (np.integer,)): return int(v)
                if isinstance(v, (np.floating,)): return float(v)
                if isinstance(v, float) and (v != v): return None  # NaN
            except ImportError:
                pass
            return v

        stats_clean = {
            col: {k: _clean(val) for k, val in col_stats.items()}
            for col, col_stats in stats.items()
        }

        return {
            "success": True,
            "filename": path.name,
            "rows": len(df),
            "columns": list(df.columns),
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "stats": stats_clean,
            "sample": df.head(5).to_dict(orient="records"),
            "missing_values": df.isnull().sum().to_dict(),
        }
    except Exception as e:
        logger.error(f"[analyze_data] Error: {e}")
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────
# Python Sandbox Tool
# ──────────────────────────────────────────────

async def execute_python(code: str, timeout: int = 30, sandbox_dir: str = "sandbox") -> dict:
    """
    Execute Python code in a Docker container sandbox (truly isolated).

    Security measures (Docker path):
    - Runs inside a throwaway python:3.11-slim container
    - --network none  : no internet access
    - --read-only     : read-only root filesystem
    - --memory 256m   : memory cap
    - --cpus 0.5      : CPU cap
    - Container removed immediately after execution (--rm)

    Falls back to local subprocess if Docker daemon is unavailable.
    """
    import time

    sandbox = Path(sandbox_dir)
    sandbox.mkdir(parents=True, exist_ok=True)

    script_file = sandbox / "_agent_exec.py"
    script_file.write_text(textwrap.dedent(code), encoding="utf-8")
    abs_sandbox = str(sandbox.resolve())

    start = time.monotonic()

    # ── Try Docker first ──────────────────────────────────────────────────
    docker_available = False
    try:
        check = await asyncio.create_subprocess_exec(
            "docker", "info",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(check.wait(), timeout=3)
        docker_available = (check.returncode == 0)
    except Exception:
        pass

    if docker_available:
        logger.info("[execute_python] Using Docker sandbox")
        try:
            docker_cmd = [
                "docker", "run", "--rm",
                "--network", "none",          # No internet
                "--memory", "256m",           # Memory limit
                "--cpus", "0.5",              # CPU limit
                "--read-only",                # Read-only root fs
                "--tmpfs", "/tmp:size=64m",  # Writable /tmp only
                "-v", f"{abs_sandbox}:/sandbox:ro",  # Mount sandbox read-only
                "--workdir", "/tmp",
                "python:3.11-slim",
                "python", f"/sandbox/_agent_exec.py",
            ]
            proc = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            return {
                "success": proc.returncode == 0,
                "stdout": stdout_b.decode("utf-8", errors="replace")[:5000],
                "stderr": stderr_b.decode("utf-8", errors="replace")[:2000],
                "exit_code": proc.returncode,
                "execution_time_ms": elapsed_ms,
                "sandbox": "docker",
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Docker execution timed out after {timeout}s",
                "stdout": "", "stderr": "", "exit_code": -1,
                "execution_time_ms": timeout * 1000,
                "sandbox": "docker",
            }
        except Exception as e:
            logger.warning(f"[execute_python] Docker run failed: {e}, falling back to subprocess")

    # ── Fallback: local subprocess ─────────────────────────────────────────
    logger.info("[execute_python] Using local subprocess sandbox (Docker unavailable)")
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(script_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(sandbox),
        )
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        return {
            "success": proc.returncode == 0,
            "stdout": stdout_b.decode("utf-8", errors="replace")[:5000],
            "stderr": stderr_b.decode("utf-8", errors="replace")[:2000],
            "exit_code": proc.returncode,
            "execution_time_ms": elapsed_ms,
            "sandbox": "subprocess",
        }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"Execution timed out after {timeout}s",
            "stdout": "", "stderr": "", "exit_code": -1,
            "execution_time_ms": timeout * 1000,
            "sandbox": "subprocess",
        }
    except Exception as e:
        logger.error(f"[execute_python] Error: {e}")
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────
# Vision / OCR Tool
# ──────────────────────────────────────────────

async def extract_image_text(image_path: str) -> dict:
    """
    Extract text from an image using PaddleOCR (primary) or pytesseract (fallback).

    Priority order:
      1. PaddleOCR  – deep learning OCR, no external binary needed
      2. pytesseract – traditional OCR with Tesseract binary
      3. PIL metadata only – if both OCR engines are unavailable
    """
    try:
        from PIL import Image

        path = Path(image_path)
        if not path.exists():
            alt = Path("uploads") / path.name
            if alt.exists():
                path = alt
            else:
                return {"success": False, "error": f"Image not found: {image_path}"}

        img = Image.open(path)
        width, height = img.size
        ocr_engine = "none"
        text = ""

        # ── 1. Try PaddleOCR ──────────────────────────────────────────────
        try:
            from paddleocr import PaddleOCR
            import numpy as np

            # Use English model, suppress verbose paddle logs
            paddle_ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            img_array = np.array(img.convert("RGB"))
            result = paddle_ocr.ocr(img_array, cls=True)

            if result and result[0]:
                lines = []
                for line in result[0]:
                    if line and len(line) >= 2 and line[1]:
                        word_info = line[1]
                        if isinstance(word_info, (list, tuple)) and len(word_info) > 0:
                            lines.append(str(word_info[0]))
                text = "\n".join(lines)
                ocr_engine = "paddleocr"
                logger.info(f"[extract_image_text] PaddleOCR extracted {len(text)} chars")
            else:
                text = ""
                ocr_engine = "paddleocr_empty"

        except ImportError:
            logger.info("[extract_image_text] PaddleOCR not installed, trying pytesseract")
        except Exception as paddle_err:
            logger.warning(f"[extract_image_text] PaddleOCR failed: {paddle_err}")

        # ── 2. Fallback: pytesseract ──────────────────────────────────────
        if ocr_engine == "none":
            try:
                import pytesseract
                from app.config import get_settings
                settings = get_settings()
                pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
                text = pytesseract.image_to_string(img)
                ocr_engine = "tesseract"
                logger.info(f"[extract_image_text] Tesseract extracted {len(text)} chars")
            except Exception as tess_err:
                logger.warning(f"[extract_image_text] Tesseract failed: {tess_err}")
                text = "(OCR unavailable — install PaddleOCR or Tesseract)"
                ocr_engine = "none"

        return {
            "success": True,
            "path": str(path),
            "width": width,
            "height": height,
            "mode": img.mode,
            "text": text.strip(),
            "ocr_used": ocr_engine not in ("none",),
            "ocr_engine": ocr_engine,
        }
    except Exception as e:
        logger.error(f"[extract_image_text] Error: {e}")
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────
# Databricks / Delta Lake Tool
# ──────────────────────────────────────────────

async def query_databricks(sql: str, catalog: str = None, schema: str = None) -> dict:
    """
    Run a SQL query against a Databricks Delta Lake warehouse.

    Requires environment variables:
        DATABRICKS_HOST        – e.g. https://adb-xxx.azuredatabricks.net
        DATABRICKS_TOKEN       – personal access token
        DATABRICKS_HTTP_PATH   – SQL warehouse HTTP path

    Args:
        sql:     SQL query to execute.
        catalog: Optional Unity Catalog catalog name.
        schema:  Optional schema/database name.

    Returns:
        Dict with 'rows' list, 'columns', 'row_count'.
    """
    try:
        from app.services.databricks_service import databricks_service
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: databricks_service.execute_query(sql, catalog=catalog, schema=schema)
        )
        return result
    except Exception as e:
        logger.error(f"[query_databricks] Error: {e}")
        return {"success": False, "configured": False, "error": str(e), "rows": [], "columns": []}
