"""
API Routes – all HTTP endpoints for the Local LLM Assistant.

Endpoints:
    POST /api/chat              – Generate a complete response
    POST /api/chat/stream       – Stream response via SSE
    GET  /api/health            – Health check (API + Ollama + Qdrant)
    GET  /api/models            – List available Ollama models

    POST   /api/rag/upload      – Upload & index a document
    POST   /api/rag/query       – RAG query (non-streaming)
    POST   /api/rag/query/stream – RAG query (SSE streaming)
    GET    /api/rag/documents   – List indexed documents
    DELETE /api/rag/documents/{doc_id} – Delete a document
    GET    /api/rag/stats       – Vector store statistics
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File
from sse_starlette.sse import EventSourceResponse

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ModelInfo,
    ModelsResponse,
    DocumentUploadResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    SourceChunk,
    DocumentInfo,
    DocumentListResponse,
    RAGStatsResponse,
    # Step 3 – Agent schemas
    AgentRequest,
    AgentResponse,
    AgentStep,
    AgentStatusResponse,
    AgentFileUploadResponse,
)
from app.config import get_settings
from app.services.llm_service import ollama_service

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# LLM Router (Step 1)
# ──────────────────────────────────────────────

router = APIRouter(prefix="/api", tags=["LLM"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the local LLM and receive a complete response.
    
    Supports optional conversation history for multi-turn dialogue
    and temperature control for response creativity.
    """
    try:
        # Convert Pydantic models to dicts for the service
        history = [msg.model_dump() for msg in request.conversation_history]

        result = await ollama_service.generate(
            prompt=request.message,
            model=request.model,
            conversation_history=history,
            temperature=request.temperature,
        )

        return ChatResponse(
            response=result["response"],
            model=result["model"],
            created_at=datetime.now(),
            total_duration_ms=result.get("total_duration_ms"),
            tokens_per_second=result.get("tokens_per_second"),
        )

    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream a response from the local LLM using Server-Sent Events (SSE).
    
    Each event contains a JSON chunk with partial content.
    The final event has 'done: true' and optional performance stats.
    """
    history = [msg.model_dump() for msg in request.conversation_history]

    async def event_generator():
        async for chunk in ollama_service.generate_stream(
            prompt=request.message,
            model=request.model,
            conversation_history=history,
            temperature=request.temperature,
        ):
            yield {"data": chunk}

    return EventSourceResponse(event_generator())


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check the health of the API server, Ollama, and Qdrant.
    
    Returns status of all services and configuration details.
    """
    settings = get_settings()
    ollama_healthy = await ollama_service.check_health()

    # Check Qdrant health
    qdrant_status = "unknown"
    try:
        from app.services.vector_service import vector_service
        qdrant_healthy = await vector_service.check_health()
        qdrant_status = "healthy" if qdrant_healthy else "unreachable"
    except Exception:
        qdrant_status = "unreachable"

    all_healthy = ollama_healthy and qdrant_status == "healthy"

    langgraph_status = "unavailable"
    try:
        from app.agents.graph import agent_graph
        langgraph_status = "healthy" if agent_graph is not None else "unavailable"
    except Exception:
        langgraph_status = "unavailable"

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        api="healthy",
        ollama="healthy" if ollama_healthy else "unreachable",
        ollama_url=settings.OLLAMA_BASE_URL,
        default_model=settings.OLLAMA_MODEL,
        qdrant=qdrant_status,
        langgraph=langgraph_status,
        timestamp=datetime.now(),
    )


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """
    List all models available in the local Ollama instance.
    
    Returns model names, sizes, and the currently configured default.
    """
    settings = get_settings()

    try:
        models_data = await ollama_service.list_models()
        models = [ModelInfo(**m) for m in models_data]
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        models = []

    return ModelsResponse(
        models=models,
        default_model=settings.OLLAMA_MODEL,
    )


# ──────────────────────────────────────────────
# RAG Router (Step 2)
# ──────────────────────────────────────────────

rag_router = APIRouter(prefix="/api/rag", tags=["RAG"])


@rag_router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document and index it in the RAG pipeline.
    
    Supports: PDF, DOCX, PPTX, TXT, CSV.
    The document is parsed, chunked, embedded, and stored in Qdrant.
    """
    from app.services.rag_service import rag_service

    try:
        result = await rag_service.ingest_document(file)
        return DocumentUploadResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@rag_router.post("/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest):
    """
    Ask a question and get a RAG-augmented answer.
    
    Retrieves relevant document chunks from the vector store,
    then generates an answer using the LLM with context.
    """
    from app.services.rag_service import rag_service

    try:
        result = await rag_service.query(
            question=request.question,
            top_k=request.top_k,
            model=request.model,
            temperature=request.temperature,
        )

        sources = [SourceChunk(**s) for s in result.get("sources", [])]

        return RAGQueryResponse(
            answer=result["answer"],
            sources=sources,
            model=result["model"],
            total_duration_ms=result["total_duration_ms"],
            tokens_per_second=result.get("tokens_per_second"),
        )

    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"RAG query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.post("/query/stream")
async def rag_query_stream(request: RAGQueryRequest):
    """
    Stream a RAG-augmented answer via Server-Sent Events.
    
    First event contains the sources, followed by streamed answer chunks.
    """
    from app.services.rag_service import rag_service

    async def event_generator():
        async for chunk in rag_service.query_stream(
            question=request.question,
            top_k=request.top_k,
            model=request.model,
            temperature=request.temperature,
        ):
            yield {"data": chunk}

    return EventSourceResponse(event_generator())


@rag_router.get("/documents", response_model=DocumentListResponse)
async def list_documents():
    """List all documents indexed in the RAG pipeline."""
    from app.services.rag_service import rag_service

    try:
        docs = await rag_service.list_documents()
        doc_infos = [DocumentInfo(**d) for d in docs]
        return DocumentListResponse(
            documents=doc_infos,
            total_count=len(doc_infos),
        )
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        return DocumentListResponse(documents=[], total_count=0)


@rag_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """
    Delete a document and all its chunks from the vector store.
    
    Also removes the uploaded file from disk.
    """
    from app.services.rag_service import rag_service

    try:
        deleted = await rag_service.delete_document(doc_id)
        if deleted:
            return {"status": "deleted", "doc_id": doc_id}
        else:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@rag_router.get("/stats", response_model=RAGStatsResponse)
async def rag_stats():
    """Get RAG pipeline statistics including vector store info."""
    from app.services.rag_service import rag_service

    try:
        stats = await rag_service.get_stats()
        return RAGStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get RAG stats: {e}")
        return RAGStatsResponse()


# ──────────────────────────────────────────────
# Agent Router (Step 3 – LangGraph)
# ──────────────────────────────────────────────

agent_router = APIRouter(prefix="/api/agent", tags=["Agent"])


@agent_router.post("/upload", response_model=AgentFileUploadResponse)
async def upload_agent_file(file: UploadFile = File(...)):
    """
    Save a file for the Data / File / Vision agents.

    Stored under workspace/agent_files/ so specialized agents can read it
    via the returned path.
    """
    import uuid
    from pathlib import Path

    from app.config import get_settings as _get_settings

    settings = _get_settings()
    dest_dir = Path(settings.WORKSPACE_DIR) / "agent_files"
    dest_dir.mkdir(parents=True, exist_ok=True)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    safe_name = Path(file.filename).name
    dest = dest_dir / f"{uuid.uuid4().hex[:8]}_{safe_name}"
    content = await file.read()
    dest.write_bytes(content)

    logger.info("[Agent Upload] Saved %s (%s bytes)", dest, len(content))
    return AgentFileUploadResponse(
        filename=safe_name,
        path=str(dest),
        size_bytes=len(content),
        status="saved",
    )


@agent_router.post("/run", response_model=AgentResponse)
async def run_agent(request: AgentRequest):
    """
    Run the multi-agent LangGraph workflow for a user query.

    The supervisor classifies the intent and routes to the appropriate
    specialized agent (RAG, Data, File, Code, or Vision).
    Returns the final answer along with the agent execution trace.
    """
    from app.agents.graph import run_agent_workflow

    try:
        result = await run_agent_workflow(
            query=request.query,
            file_paths=request.file_paths,
        )

        steps = [AgentStep(**s) for s in result.get("agent_steps", [])]

        return AgentResponse(
            answer=result["answer"],
            intent=result["intent"],
            active_agent=result["active_agent"],
            agent_steps=steps,
            error=result.get("error"),
            metadata=result.get("metadata", {}),
        )
    except Exception as e:
        logger.error(f"Agent workflow failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@agent_router.post("/run/stream")
async def run_agent_stream(request: AgentRequest):
    """
    Stream the multi-agent workflow response via Server-Sent Events.

    Streams agent step events first, then the final answer.
    """
    from app.agents.graph import stream_agent_workflow

    async def event_generator():
        import json as _json
        async for event in stream_agent_workflow(
            query=request.query,
            file_paths=request.file_paths,
        ):
            yield {"data": _json.dumps(event)}

    return EventSourceResponse(event_generator())


@agent_router.get("/status", response_model=AgentStatusResponse)
async def agent_status():
    """
    Check the health and configuration of the multi-agent system.

    Returns whether the LangGraph is compiled and lists available agents.
    """
    from app.agents.graph import agent_graph

    is_compiled = agent_graph is not None

    return AgentStatusResponse(
        status="ready" if is_compiled else "unavailable",
        graph_compiled=is_compiled,
        available_agents=[
            "rag_agent",
            "data_agent",
            "file_agent",
            "code_agent",
            "vision_agent",
            "general_agent",
        ],
        intent_classes=["rag", "data", "file", "code", "vision", "general"],
    )
