/**
 * Application constants and default configuration values.
 */

/** Base URL for API calls — proxied through Next.js rewrites in dev */
export const API_BASE = '/api';

/** Default model name (matches .env OLLAMA_MODEL) */
export const DEFAULT_MODEL = 'qwen3:8b';

/** Default sampling temperature */
export const DEFAULT_TEMPERATURE = 0.7;

/** Health polling interval in ms */
export const HEALTH_POLL_INTERVAL = 30_000;

/** Max file size for uploads (MB) */
export const MAX_FILE_SIZE_MB = 50;

/** Accepted file types for RAG upload */
export const RAG_FILE_TYPES = '.pdf,.docx,.doc,.pptx,.ppt,.txt,.csv';

/** Accepted file types for Agent upload */
export const AGENT_FILE_TYPES = '.csv,.json,.xlsx,.xls,.png,.jpg,.jpeg,.txt,.pdf';

/** Max message length */
export const MAX_MESSAGE_LENGTH = 10_000;

/** Default number of top-k chunks for RAG retrieval */
export const DEFAULT_RAG_TOP_K = 5;
