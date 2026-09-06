"""
FastAPI Application Entry Point.

Configures the app, mounts static files, includes API routes (LLM + RAG),
and sets up CORS middleware for cross-origin access.
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.api.routes import router as api_router
from app.api.routes import rag_router
from app.api.routes import agent_router
from app.auth.router import auth_router
from app.api.governance_router import governance_router
from app.api.security_router import security_router
from app.api.query_router import query_router
from app.api.workspace_router import workspace_router
from app.api.pipeline_router import pipeline_router
from app.api.jobs_router import jobs_router
from app.api.database_router import database_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Load settings
settings = get_settings()

# ──────────────────────────────────────────────
# Create FastAPI App
# ──────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description=(
        "Local LLM Assistant powered by Ollama. "
        "Step 1: Foundation | Step 2: RAG Pipeline | Step 3: LangGraph Multi-Agent Orchestration."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ──────────────────────────────────────────────
# Middleware
# ──────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Routes & Static Files
# ──────────────────────────────────────────────

# Include all API routers
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(rag_router)
app.include_router(agent_router)
app.include_router(governance_router)
app.include_router(security_router)
app.include_router(query_router)
app.include_router(workspace_router)
app.include_router(pipeline_router)
app.include_router(jobs_router)
app.include_router(database_router)

# Mount static files (frontend)
app.mount(
    "/static",
    StaticFiles(directory="app/static", html=True),
    name="static",
)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to the chat UI."""
    return RedirectResponse(url="/static/index.html")


# ──────────────────────────────────────────────
# Startup Event
# ──────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Log startup info, check Ollama & Qdrant connectivity, init collections."""
    # Initialize SQLite database (creates tables if not exist)
    from app.db.database import init_db
    await init_db()

    logger.info("=" * 55)
    logger.info(f"  {settings.APP_TITLE} v{settings.APP_VERSION}")
    logger.info(f"  Ollama URL   : {settings.OLLAMA_BASE_URL}")
    logger.info(f"  Model        : {settings.OLLAMA_MODEL}")
    logger.info(f"  Qdrant       : {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    logger.info(f"  Embedding    : {settings.EMBEDDING_MODEL}")
    logger.info(f"  Chunk Size   : {settings.CHUNK_SIZE} (overlap: {settings.CHUNK_OVERLAP})")
    logger.info("=" * 55)

    # Ensure uploads directory exists
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Upload dir: {upload_path.absolute()}")

    # Check Ollama
    from app.services.llm_service import ollama_service
    is_healthy = await ollama_service.check_health()

    if is_healthy:
        logger.info("✓ Ollama is reachable and ready")
    else:
        logger.warning(
            "✗ Ollama is NOT reachable at %s. "
            "Start it with: ollama serve",
            settings.OLLAMA_BASE_URL,
        )

    # Check Qdrant & initialize collection
    try:
        from app.services.vector_service import vector_service
        qdrant_healthy = await vector_service.check_health()

        if qdrant_healthy:
            logger.info("✓ Qdrant is reachable and ready")
            # Initialize collection
            await vector_service.init_collection()
        else:
            logger.warning(
                "✗ Qdrant is NOT reachable at %s:%s. "
                "Start it with: docker-compose up -d",
                settings.QDRANT_HOST,
                settings.QDRANT_PORT,
            )
    except Exception as e:
        logger.warning(f"✗ Qdrant check failed: {e}")

    logger.info("─" * 55)
    logger.info("  RAG Pipeline : Ready (upload documents to get started)")
    logger.info("  Agent System : Ready (LangGraph multi-agent workflow)")
    logger.info("─" * 55)

    # Pre-compile LangGraph
    try:
        from app.agents.graph import agent_graph
        if agent_graph is not None:
            logger.info("✓ LangGraph agent workflow compiled and ready")
        else:
            logger.warning("✗ LangGraph agent workflow failed to compile")
    except Exception as ag_err:
        logger.warning(f"✗ LangGraph init error: {ag_err}")

# Trigger reload 2
