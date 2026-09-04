/**
 * API Client — typed fetch wrappers for all FastAPI endpoints.
 *
 * All paths use the `/api` prefix which Next.js rewrites to the
 * FastAPI backend at http://localhost:8000 during development.
 */

import { API_BASE } from './constants';
import type {
  ChatRequest,
  ChatResponse,
  HealthResponse,
  ModelsResponse,
  DocumentUploadResponse,
  RAGQueryRequest,
  RAGQueryResponse,
  DocumentListResponse,
  RAGStatsResponse,
  AgentRequest,
  AgentResponse,
  AgentStatusResponse,
  AgentFileInfo,
} from './types';

// ── Helpers ──

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

// ── Chat (Step 1) ──

export async function chatGenerate(req: ChatRequest): Promise<ChatResponse> {
  return json<ChatResponse>(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
}

export function chatStream(req: ChatRequest): ReadableStream<Uint8Array> | null {
  // Returns the raw response body stream for SSE consumption
  const controller = new AbortController();
  const promise = fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal: controller.signal,
  });
  // We return a wrapper; caller should use readSSEStream()
  return null; // see streamChat() below
}

/**
 * Initiate a streaming chat request and yield parsed SSE chunks.
 */
export async function* streamChat(
  req: ChatRequest,
  signal?: AbortSignal,
): AsyncGenerator<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  });
  yield* parseSSEStream(res);
}

// ── Health ──

export async function getHealth(): Promise<HealthResponse> {
  return json<HealthResponse>(`${API_BASE}/health`);
}

// ── Models ──

export async function getModels(): Promise<ModelsResponse> {
  return json<ModelsResponse>(`${API_BASE}/models`);
}

// ── RAG (Step 2) ──

export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/rag/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Upload failed: ${res.status}`);
  }
  return res.json();
}

export async function ragQuery(req: RAGQueryRequest): Promise<RAGQueryResponse> {
  return json<RAGQueryResponse>(`${API_BASE}/rag/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
}

export async function* streamRAGQuery(
  req: RAGQueryRequest,
  signal?: AbortSignal,
): AsyncGenerator<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/rag/query/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  });
  yield* parseSSEStream(res);
}

export async function listDocuments(): Promise<DocumentListResponse> {
  return json<DocumentListResponse>(`${API_BASE}/rag/documents`);
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/rag/documents/${docId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    throw new Error(`Failed to delete document: ${res.status}`);
  }
}

export async function getRAGStats(): Promise<RAGStatsResponse> {
  return json<RAGStatsResponse>(`${API_BASE}/rag/stats`);
}

// ── Agent (Step 3) ──

export async function uploadAgentFile(file: File): Promise<AgentFileInfo> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/agent/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Agent upload failed: ${res.status}`);
  }
  const data = await res.json();
  return {
    filename: data.filename,
    path: data.path,
    size_bytes: data.size_bytes,
  };
}

export async function runAgent(req: AgentRequest): Promise<AgentResponse> {
  return json<AgentResponse>(`${API_BASE}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
}

export async function* streamAgent(
  req: AgentRequest,
  signal?: AbortSignal,
): AsyncGenerator<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/agent/run/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  });
  yield* parseSSEStream(res);
}

export async function getAgentStatus(): Promise<AgentStatusResponse> {
  return json<AgentStatusResponse>(`${API_BASE}/agent/status`);
}

// ── SSE Stream Parser ──

/**
 * Parse a fetch Response as an SSE stream and yield each parsed JSON data chunk.
 * Handles the `data: {...}` format from FastAPI's sse-starlette.
 */
async function* parseSSEStream(
  response: Response,
): AsyncGenerator<Record<string, unknown>> {
  if (!response.body) return;

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim();
          if (!dataStr) continue;
          try {
            yield JSON.parse(dataStr);
          } catch {
            // Skip unparseable lines
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
