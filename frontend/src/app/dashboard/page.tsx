'use client';

/**
 * Dashboard Page — system health, stats, and model information.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Server, Database, Brain, Cpu, FileText, Layers } from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import AuthGuard from '@/components/auth/AuthGuard';
import { useHealth } from '@/hooks/useHealth';
import { useAppStore } from '@/stores/appStore';
import { getModels, getRAGStats, getAgentStatus } from '@/lib/api';
import type { ModelInfo, RAGStatsResponse, AgentStatusResponse } from '@/lib/types';

export default function DashboardPage() {
  const { health } = useHealth();
  const currentModel = useAppStore((s) => s.currentModel);

  const [models, setModels] = useState<ModelInfo[]>([]);
  const [ragStats, setRagStats] = useState<RAGStatsResponse | null>(null);
  const [agentStatus, setAgentStatus] = useState<AgentStatusResponse | null>(null);

  useEffect(() => {
    getModels()
      .then((d) => setModels(d.models))
      .catch(() => {});
    getRAGStats()
      .then(setRagStats)
      .catch(() => {});
    getAgentStatus()
      .then(setAgentStatus)
      .catch(() => {});
  }, []);

  const StatusBadge = ({
    status,
  }: {
    status: 'healthy' | 'unhealthy' | 'checking';
  }) => (
    <span className={`dash-status-badge ${status}`}>
      <span className={`dash-status-dot ${status}`} />
      {status === 'healthy' ? 'Online' : status === 'checking' ? 'Checking...' : 'Offline'}
    </span>
  );

  return (
    <AuthGuard>
      <div className="app-layout">
        <Sidebar />
        <main className="chat-main">
          <div className="dashboard-page">
            <Link href="/" className="back-link">
              <ArrowLeft size={16} />
              Back to Chat
            </Link>

            <h1 className="dashboard-title">System Dashboard</h1>
            <p className="dashboard-subtitle">
              Monitor services, view statistics, and check system health
            </p>

            {/* Service Health Grid */}
            <div>
              <p className="section-label" style={{ marginBottom: '12px' }}>
                Service Health
              </p>
              <div className="dashboard-grid">
                <div className="dash-card">
                  <div className="dash-card-header">
                    <div className="dash-card-icon green-icon"><Server size={18} /></div>
                    <span className="dash-card-title">FastAPI Server</span>
                  </div>
                  <StatusBadge status={health.api} />
                </div>

                <div className="dash-card">
                  <div className="dash-card-header">
                    <div className="dash-card-icon chat-icon"><Brain size={18} /></div>
                    <span className="dash-card-title">Ollama LLM</span>
                  </div>
                  <StatusBadge status={health.ollama} />
                  <div className="dash-card-label" style={{ marginTop: '8px' }}>
                    Model: {currentModel}
                  </div>
                </div>

                <div className="dash-card">
                  <div className="dash-card-header">
                    <div className="dash-card-icon rag-icon"><Database size={18} /></div>
                    <span className="dash-card-title">Qdrant Vector DB</span>
                  </div>
                  <StatusBadge status={health.qdrant} />
                </div>

                <div className="dash-card">
                  <div className="dash-card-header">
                    <div className="dash-card-icon agent-icon"><Cpu size={18} /></div>
                    <span className="dash-card-title">LangGraph Agents</span>
                  </div>
                  <StatusBadge status={health.langgraph} />
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div>
              <p className="section-label" style={{ marginBottom: '12px' }}>
                Statistics
              </p>
              <div className="dashboard-grid">
                <div className="dash-card">
                  <div className="dash-card-header">
                    <div className="dash-card-icon chat-icon"><Layers size={18} /></div>
                    <span className="dash-card-title">Available Models</span>
                  </div>
                  <div className="dash-card-value">{models.length}</div>
                  <div className="dash-card-label">
                    {models.map((m) => m.name).join(', ') || 'None loaded'}
                  </div>
                </div>

                <div className="dash-card">
                  <div className="dash-card-header">
                    <div className="dash-card-icon rag-icon"><FileText size={18} /></div>
                    <span className="dash-card-title">Indexed Documents</span>
                  </div>
                  <div className="dash-card-value">
                    {ragStats?.document_count ?? '—'}
                  </div>
                  <div className="dash-card-label">
                    Embedding: {ragStats?.embedding_model || '—'}
                  </div>
                </div>

                <div className="dash-card">
                  <div className="dash-card-header">
                    <div className="dash-card-icon agent-icon"><Cpu size={18} /></div>
                    <span className="dash-card-title">Available Agents</span>
                  </div>
                  <div className="dash-card-value">
                    {agentStatus?.available_agents?.length ?? '—'}
                  </div>
                  <div className="dash-card-label">
                    {agentStatus?.available_agents?.join(', ') || '—'}
                  </div>
                </div>

                <div className="dash-card">
                  <div className="dash-card-header">
                    <div className="dash-card-icon green-icon"><Database size={18} /></div>
                    <span className="dash-card-title">Vector Collection</span>
                  </div>
                  <div className="dash-card-value">
                    {ragStats?.collection
                      ? (ragStats.collection as Record<string, unknown>).vectors_count?.toString() ?? '—'
                      : '—'}
                  </div>
                  <div className="dash-card-label">Total vectors stored</div>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
