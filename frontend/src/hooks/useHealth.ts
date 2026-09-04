/**
 * useHealth — polls service health every 30 seconds.
 *
 * Checks API health, RAG stats (for Qdrant), and Agent status (for LangGraph).
 * Updates the Zustand store with current health statuses.
 */

'use client';

import { useEffect, useCallback } from 'react';
import { useAppStore } from '@/stores/appStore';
import { getHealth, getRAGStats, getAgentStatus } from '@/lib/api';
import { HEALTH_POLL_INTERVAL } from '@/lib/constants';

export function useHealth() {
  const setHealth = useAppStore((s) => s.setHealth);
  const health = useAppStore((s) => s.health);

  const checkHealth = useCallback(async () => {
    // API + Ollama
    try {
      const data = await getHealth();
      const ollamaOk = data.ollama === 'healthy';
      const qdrantOk = !data.qdrant || data.qdrant === 'healthy';
      const graphOk = !data.langgraph || data.langgraph === 'healthy';
      setHealth({
        api: 'healthy',
        ollama: ollamaOk ? 'healthy' : 'unhealthy',
        qdrant: qdrantOk ? 'healthy' : 'unhealthy',
        langgraph: graphOk ? 'healthy' : 'unhealthy',
      });
    } catch {
      setHealth({ api: 'unhealthy', ollama: 'unhealthy' });
    }

    // Qdrant via RAG stats
    try {
      const stats = await getRAGStats();
      const ok = stats.collection && (stats.collection as Record<string, unknown>).status !== 'error';
      setHealth({ qdrant: ok ? 'healthy' : 'unhealthy' });
    } catch {
      setHealth({ qdrant: 'unhealthy' });
    }

    // LangGraph agent status
    try {
      const agent = await getAgentStatus();
      setHealth({ langgraph: agent.graph_compiled ? 'healthy' : 'unhealthy' });
    } catch {
      setHealth({ langgraph: 'unhealthy' });
    }
  }, [setHealth]);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, HEALTH_POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [checkHealth]);

  return { health, refresh: checkHealth };
}
