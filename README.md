# SIH Local LLM Assistant

Offline assistant with three layers: local chat, document RAG, and a LangGraph multi-agent workflow.

**Flow:** User → Next.js UI → FastAPI → Ollama (`qwen3:8b`) → Response

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com/download)
- Docker (optional, for Qdrant and the code-agent sandbox)

---

## Quick Start

### 1. Ollama

```powershell
ollama pull qwen3:8b
ollama serve
```

Ollama listens on `http://localhost:11434`.

### 2. Qdrant (RAG)

```powershell
docker compose up -d
```

If Docker is not running, the backend falls back to local file storage in `qdrant_data/`.

### 3. Python API

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Next.js UI

```powershell
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**. API calls are proxied to FastAPI on port 8000.

Swagger: http://localhost:8000/docs

---

## Modes

| Mode | What it does |
|------|----------------|
| **Chat** | Direct local LLM (Step 1) |
| **RAG** | Upload PDF/DOCX/PPTX/TXT/CSV, retrieve from Qdrant, answer with context (Step 2) |
| **Agent** | Supervisor routes to RAG, Data, File, Code, Vision, or General agents (Step 3) |

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Full chat response |
| POST | `/api/chat/stream` | SSE chat stream |
| GET | `/api/health` | API + Ollama + Qdrant + LangGraph |
| GET | `/api/models` | Local Ollama models |
| POST | `/api/rag/upload` | Index a document |
| POST | `/api/rag/query` | RAG answer |
| POST | `/api/rag/query/stream` | RAG SSE stream |
| GET | `/api/rag/documents` | List indexed docs |
| DELETE | `/api/rag/documents/{doc_id}` | Delete a document |
| GET | `/api/rag/stats` | Vector store stats |
| POST | `/api/agent/upload` | Save a file for agents |
| POST | `/api/agent/run` | Run the LangGraph workflow |
| POST | `/api/agent/run/stream` | Stream agent steps + answer |
| GET | `/api/agent/status` | Graph compiled + agent list |

---

## Project structure

```
SIH_Project/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── api/                 # FastAPI routes + Pydantic schemas
│   ├── services/            # Ollama, RAG, Qdrant, embeddings, Databricks
│   └── agents/              # LangGraph supervisor + specialized agents
├── frontend/                # Next.js chat / RAG / agent UI
├── docker-compose.yml       # Qdrant
├── requirements.txt
└── .env
```

---

## Configuration

Copy values into `.env` (see `.env.example`).

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
QDRANT_HOST=localhost
QDRANT_PORT=6333
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

Optional Databricks (Data Agent SQL / Delta Lake):

```env
DATABRICKS_HOST=https://adb-xxx.azuredatabricks.net
DATABRICKS_TOKEN=
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/...
DATABRICKS_CATALOG=
DATABRICKS_SCHEMA=
```

OCR: PaddleOCR if installed, otherwise Tesseract (`TESSERACT_CMD`). Code agent prefers Docker sandbox, then local subprocess.

---

## Roadmap

- [x] **Step 1** – Local LLM (FastAPI + Ollama)
- [x] **Step 2** – RAG pipeline (LangChain, BGE, Qdrant)
- [x] **Step 3** – LangGraph agents (RAG, Data, File, Code, Vision, General)
