/**
 * useChat — manages conversation logic, message sending, and SSE streaming.
 *
 * Automatically routes to the correct API endpoint based on the current mode
 * (Chat → /api/chat/stream, RAG → /api/rag/query/stream, Agent → /api/agent/run/stream).
 */

'use client';

import { useCallback, useRef } from 'react';
import { useAppStore } from '@/stores/appStore';
import { streamChat, streamRAGQuery, streamAgent } from '@/lib/api';
import { DEFAULT_RAG_TOP_K } from '@/lib/constants';
import type { ChatMessage, AgentStep, SourceChunk } from '@/lib/types';

function generateId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function useChat() {
  const {
    mode,
    messages,
    addMessage,
    updateMessage,
    clearMessages,
    isStreaming,
    setIsStreaming,
    currentModel,
    temperature,
    agentFiles,
  } = useAppStore();

  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return;

      // ── Add user message ──
      const userMsg: ChatMessage = {
        id: generateId(),
        role: 'user',
        content: text,
        mode,
        timestamp: new Date(),
      };
      addMessage(userMsg);

      // ── Create placeholder assistant message ──
      const assistantId = generateId();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        content: '',
        mode,
        timestamp: new Date(),
        isStreaming: true,
      };
      addMessage(assistantMsg);

      setIsStreaming(true);
      abortRef.current = new AbortController();
      const signal = abortRef.current.signal;

      try {
        if (mode === 'chat') {
          await handleChatStream(text, assistantId, signal);
        } else if (mode === 'rag') {
          await handleRAGStream(text, assistantId, signal);
        } else if (mode === 'agent') {
          await handleAgentStream(text, assistantId, signal);
        }
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          const errorMsg = err instanceof Error ? err.message : 'Unknown error';
          updateMessage(assistantId, {
            content: `⚠️ Error: ${errorMsg}`,
            isStreaming: false,
          });
        }
      } finally {
        setIsStreaming(false);
        updateMessage(assistantId, { isStreaming: false });
        abortRef.current = null;
      }
    },
    [mode, isStreaming, currentModel, temperature, messages, agentFiles, addMessage, updateMessage, setIsStreaming],
  );

  // ── Chat mode streaming ──
  const handleChatStream = useCallback(
    async (text: string, msgId: string, signal: AbortSignal) => {
      // Build conversation history from previous messages (excluding current)
      const history = useAppStore
        .getState()
        .messages.filter((m) => m.mode === 'chat' && m.id !== msgId)
        .map((m) => ({ role: m.role, content: m.content }));

      // Remove the last user message (it's the prompt, not history)
      history.pop();

      let fullContent = '';
      for await (const chunk of streamChat(
        {
          message: text,
          conversation_history: history,
          model: currentModel,
          temperature,
        },
        signal,
      )) {
        if (chunk.error) {
          updateMessage(msgId, { content: `⚠️ ${chunk.error}` });
          return;
        }
        if (chunk.content) {
          fullContent += chunk.content as string;
          updateMessage(msgId, { content: fullContent });
        }
        if (chunk.done && chunk.tokens_per_second) {
          updateMessage(msgId, {
            stats: {
              tokens_per_second: chunk.tokens_per_second as number,
              model: chunk.model as string,
            },
          });
        }
      }
    },
    [currentModel, temperature, updateMessage],
  );

  // ── RAG mode streaming ──
  const handleRAGStream = useCallback(
    async (text: string, msgId: string, signal: AbortSignal) => {
      let fullContent = '';
      let sources: SourceChunk[] = [];

      for await (const chunk of streamRAGQuery(
        {
          question: text,
          top_k: DEFAULT_RAG_TOP_K,
          model: currentModel,
          temperature,
        },
        signal,
      )) {
        if (chunk.type === 'sources') {
          sources = (chunk.sources as SourceChunk[]) || [];
          updateMessage(msgId, { sources });
        }
        if (chunk.error) {
          updateMessage(msgId, { content: `⚠️ ${chunk.error}` });
          return;
        }
        if (chunk.content) {
          fullContent += chunk.content as string;
          updateMessage(msgId, { content: fullContent });
        }
        if (chunk.done && chunk.tokens_per_second) {
          updateMessage(msgId, {
            stats: {
              tokens_per_second: chunk.tokens_per_second as number,
              model: chunk.model as string,
            },
          });
        }
      }
    },
    [currentModel, temperature, updateMessage],
  );

  // ── Agent mode streaming ──
  const handleAgentStream = useCallback(
    async (text: string, msgId: string, signal: AbortSignal) => {
      const filePaths = agentFiles.map((f) => f.path);
      const steps: AgentStep[] = [];

      for await (const chunk of streamAgent(
        { query: text, file_paths: filePaths },
        signal,
      )) {
        if (chunk.type === 'step') {
          steps.push(chunk.step as AgentStep);
          updateMessage(msgId, { agentSteps: [...steps] });
        } else if (chunk.type === 'answer') {
          updateMessage(msgId, {
            content: (chunk.answer as string) || '',
            intent: chunk.intent as string,
            activeAgent: chunk.active_agent as string,
          });
        } else if (chunk.type === 'error') {
          updateMessage(msgId, {
            content: `⚠️ ${chunk.error}`,
          });
        }
      }
    },
    [agentFiles, updateMessage],
  );

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return {
    messages,
    isStreaming,
    sendMessage,
    stopStreaming,
    clearMessages,
  };
}
