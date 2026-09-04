"""
Application configuration loaded from environment variables.
Uses pydantic-settings to validate and provide typed access to all config values.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:8b"

    # Application Settings
    APP_TITLE: str = "SIH Local LLM Assistant"
    APP_VERSION: str = "3.0.0"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Qdrant Vector Database
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "sih_documents"

    # Embedding Model
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384

    # Chunking Settings
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # RAG Settings
    RAG_TOP_K: int = 5

    # Upload Settings
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 50

    # Tesseract OCR (Windows default path)
    TESSERACT_CMD: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    # Step 3: Agentic Workflow
    SANDBOX_DIR: str = "sandbox"       # Python code execution sandbox
    WORKSPACE_DIR: str = "workspace"   # File agent working directory

    # LangGraph Settings
    MAX_AGENT_ITERATIONS: int = 10
    AGENT_TIMEOUT_SECONDS: int = 120

    # Databricks / Delta Lake (optional — Data Agent)
    DATABRICKS_HOST: str = ""
    DATABRICKS_TOKEN: str = ""
    DATABRICKS_HTTP_PATH: str = ""
    DATABRICKS_CATALOG: str = ""
    DATABRICKS_SCHEMA: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance (singleton pattern)."""
    return Settings()
