"""
Pydantic schemas for API request/response validation.
Ensures type safety and auto-generates OpenAPI documentation.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ──────────────────────────────────────────────
# Chat Schemas
# ──────────────────────────────────────────────

class Message(BaseModel):
    """A single message in a conversation."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content text")


class ChatRequest(BaseModel):
    """Request body for the /api/chat endpoint."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The user's question or prompt"
    )
    conversation_history: list[Message] = Field(
        default_factory=list,
        description="Optional conversation history for context"
    )
    model: Optional[str] = Field(
        default=None,
        description="Override the default model (optional)"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 = deterministic, 2.0 = creative)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "What is machine learning?",
                    "conversation_history": [],
                    "temperature": 0.7
                }
            ]
        }
    }


class ChatResponse(BaseModel):
    """Response body from the /api/chat endpoint."""
    response: str = Field(..., description="The assistant's generated response")
    model: str = Field(..., description="The model used for generation")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp of the response"
    )
    total_duration_ms: Optional[float] = Field(
        default=None,
        description="Total generation time in milliseconds"
    )
    tokens_per_second: Optional[float] = Field(
        default=None,
        description="Generation speed in tokens per second"
    )


# ──────────────────────────────────────────────
# Health Check Schemas
# ──────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Response body for the /api/health endpoint."""
    status: str = Field(..., description="Overall health status")
    api: str = Field(default="healthy", description="API server status")
    ollama: str = Field(..., description="Ollama server status")
    ollama_url: str = Field(..., description="Ollama server URL")
    default_model: str = Field(..., description="Configured default model")
    qdrant: str = Field(default="unknown", description="Qdrant vector DB status")
    langgraph: str = Field(default="unknown", description="LangGraph agent status")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Health check timestamp"
    )


# ──────────────────────────────────────────────
# Model Schemas
# ──────────────────────────────────────────────

class ModelInfo(BaseModel):
    """Information about an available Ollama model."""
    name: str = Field(..., description="Model name/tag")
    size: Optional[float] = Field(
        default=None,
        description="Model size in GB"
    )
    modified_at: Optional[str] = Field(
        default=None,
        description="Last modified timestamp"
    )


class ModelsResponse(BaseModel):
    """Response body for the /api/models endpoint."""
    models: list[ModelInfo] = Field(
        default_factory=list,
        description="List of available models"
    )
    default_model: str = Field(..., description="Currently configured default model")


# ──────────────────────────────────────────────
# RAG – Document Upload Schemas
# ──────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    """Response after uploading and indexing a document."""
    doc_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    chunk_count: int = Field(..., description="Number of chunks created")
    page_count: int = Field(default=1, description="Number of pages in document")
    file_type: str = Field(..., description="File extension")
    processing_time_ms: float = Field(..., description="Total processing time in ms")
    status: str = Field(default="indexed", description="Indexing status")


# ──────────────────────────────────────────────
# RAG – Query Schemas
# ──────────────────────────────────────────────

class SourceChunk(BaseModel):
    """A single retrieved source chunk from vector search."""
    chunk_text: str = Field(..., description="The text content of the chunk")
    score: float = Field(..., description="Similarity score (0-1)")
    filename: str = Field(..., description="Source document filename")
    chunk_index: int = Field(default=0, description="Chunk position in document")
    doc_id: str = Field(default="", description="Source document ID")


class RAGQueryRequest(BaseModel):
    """Request body for RAG query endpoints."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The question to answer using document context"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of similar chunks to retrieve"
    )
    model: Optional[str] = Field(
        default=None,
        description="Override the default LLM model"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "What does the document say about machine learning?",
                    "top_k": 5,
                    "temperature": 0.7
                }
            ]
        }
    }


class RAGQueryResponse(BaseModel):
    """Response from a RAG query."""
    answer: str = Field(..., description="The generated answer")
    sources: list[SourceChunk] = Field(
        default_factory=list,
        description="Retrieved source chunks used for the answer"
    )
    model: str = Field(..., description="LLM model used")
    total_duration_ms: float = Field(..., description="Total query time in ms")
    tokens_per_second: Optional[float] = Field(
        default=None,
        description="Generation speed"
    )


# ──────────────────────────────────────────────
# RAG – Document Management Schemas
# ──────────────────────────────────────────────

class DocumentInfo(BaseModel):
    """Information about an indexed document."""
    doc_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(default="", description="File extension")
    chunk_count: int = Field(default=0, description="Number of indexed chunks")


class DocumentListResponse(BaseModel):
    """Response listing all indexed documents."""
    documents: list[DocumentInfo] = Field(
        default_factory=list,
        description="List of indexed documents"
    )
    total_count: int = Field(default=0, description="Total number of documents")


class RAGStatsResponse(BaseModel):
    """RAG pipeline statistics."""
    collection: dict = Field(default_factory=dict, description="Vector collection info")
    document_count: int = Field(default=0, description="Number of indexed documents")
    embedding_model: str = Field(default="", description="Embedding model name")
    embedding_loaded: bool = Field(default=False, description="Whether embedding model is loaded")


# ──────────────────────────────────────────────
# Step 3 – Agent Workflow Schemas
# ──────────────────────────────────────────────

class AgentStep(BaseModel):
    """A single step in the agent execution trace."""
    agent: str = Field(..., description="Agent name that executed this step")
    action: str = Field(..., description="Action performed by the agent")
    result: str = Field(default="", description="Summary of the step result")
    timestamp: str = Field(default="", description="ISO timestamp of the step")


class AgentRequest(BaseModel):
    """Request body for the multi-agent workflow endpoint."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The user's natural language query"
    )
    file_paths: list[str] = Field(
        default_factory=list,
        description="Paths to files uploaded for agent use"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "What is the main topic of the uploaded document?",
                    "file_paths": []
                }
            ]
        }
    }


class AgentResponse(BaseModel):
    """Response from the multi-agent workflow."""
    answer: str = Field(..., description="Final answer generated by the agent")
    intent: str = Field(..., description="Detected intent class")
    active_agent: str = Field(..., description="Agent that generated the answer")
    agent_steps: list[AgentStep] = Field(
        default_factory=list,
        description="Ordered execution trace of agent steps"
    )
    error: Optional[str] = Field(default=None, description="Error message if workflow failed")
    metadata: dict = Field(default_factory=dict, description="Additional agent metadata")


class AgentStatusResponse(BaseModel):
    """Status of the agent system."""
    status: str = Field(..., description="Agent system status")
    graph_compiled: bool = Field(..., description="Whether the LangGraph is compiled")
    available_agents: list[str] = Field(
        default_factory=list,
        description="List of available specialized agents"
    )
    intent_classes: list[str] = Field(
        default_factory=list,
        description="Supported intent classes for routing"
    )


class AgentFileUploadResponse(BaseModel):
    """Response after uploading a file for agent use."""
    filename: str = Field(..., description="Original filename")
    path: str = Field(..., description="Server path agents can read")
    size_bytes: int = Field(..., description="File size in bytes")
    status: str = Field(default="saved", description="Upload status")


