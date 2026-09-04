/**
 * TypeScript interfaces matching the FastAPI Pydantic schemas.
 * Ensures type-safe communication between frontend and backend.
 */

// ── Chat ──

export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  message: string;
  conversation_history: Message[];
  model?: string | null;
  temperature: number;
}

export interface ChatResponse {
  response: string;
  model: string;
  created_at: string;
  total_duration_ms?: number | null;
  tokens_per_second?: number | null;
}

// ── Health ──

export interface HealthResponse {
  status: string;
  api: string;
  ollama: string;
  ollama_url: string;
  default_model: string;
  qdrant?: string;
  langgraph?: string;
  timestamp: string;
}

// ── Models ──

export interface ModelInfo {
  name: string;
  size?: number | null;
  modified_at?: string | null;
}

export interface ModelsResponse {
  models: ModelInfo[];
  default_model: string;
}

// ── RAG: Document Upload ──

export interface DocumentUploadResponse {
  doc_id: string;
  filename: string;
  chunk_count: number;
  page_count: number;
  file_type: string;
  processing_time_ms: number;
  status: string;
}

// ── RAG: Query ──

export interface SourceChunk {
  chunk_text: string;
  score: number;
  filename: string;
  chunk_index: number;
  doc_id: string;
}

export interface RAGQueryRequest {
  question: string;
  top_k: number;
  model?: string | null;
  temperature: number;
}

export interface RAGQueryResponse {
  answer: string;
  sources: SourceChunk[];
  model: string;
  total_duration_ms: number;
  tokens_per_second?: number | null;
}

// ── RAG: Document Management ──

export interface DocumentInfo {
  doc_id: string;
  filename: string;
  file_type: string;
  chunk_count: number;
}

export interface DocumentListResponse {
  documents: DocumentInfo[];
  total_count: number;
}

export interface RAGStatsResponse {
  collection: Record<string, unknown>;
  document_count: number;
  embedding_model: string;
  embedding_loaded: boolean;
}

// ── Agent ──

export interface AgentStep {
  agent: string;
  action: string;
  result: string;
  timestamp: string;
}

export interface AgentFileInfo {
  filename: string;
  path: string;
  size_bytes: number;
}

export interface AgentRequest {
  query: string;
  file_paths: string[];
}

export interface AgentResponse {
  answer: string;
  intent: string;
  active_agent: string;
  agent_steps: AgentStep[];
  error?: string | null;
  metadata: Record<string, unknown>;
}

export interface AgentStatusResponse {
  status: string;
  graph_compiled: boolean;
  available_agents: string[];
  intent_classes: string[];
}

// ── SSE Stream Chunk Types ──

export interface SSEChatChunk {
  content?: string;
  done?: boolean;
  model?: string;
  tokens_per_second?: number;
  error?: string;
}

export interface SSERAGChunk {
  type?: 'sources' | 'content' | 'done' | 'error';
  content?: string;
  sources?: SourceChunk[];
  done?: boolean;
  model?: string;
  tokens_per_second?: number;
  error?: string;
}

export interface SSEAgentChunk {
  type: 'step' | 'answer' | 'error';
  step?: AgentStep;
  answer?: string;
  intent?: string;
  active_agent?: string;
  done?: boolean;
  error?: string;
}

// ── App State Types ──

export type AppMode = 'chat' | 'rag' | 'agent';

export interface ServiceHealth {
  api: 'healthy' | 'unhealthy' | 'checking';
  ollama: 'healthy' | 'unhealthy' | 'checking';
  qdrant: 'healthy' | 'unhealthy' | 'checking';
  langgraph: 'healthy' | 'unhealthy' | 'checking';
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  mode: AppMode;
  timestamp: Date;
  // Chat-specific
  stats?: {
    tokens_per_second?: number;
    model?: string;
  };
  // RAG-specific
  sources?: SourceChunk[];
  // Agent-specific
  intent?: string;
  activeAgent?: string;
  agentSteps?: AgentStep[];
  isStreaming?: boolean;
}
