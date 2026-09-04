'use client';

/**
 * Sidebar — mode selector, document/agent uploads, model/temp controls, status indicators.
 */

import { useEffect, useState } from 'react';
import {
  Layers,
  Plus,
  MessageSquare,
  FileText,
  Settings,
} from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import { getModels } from '@/lib/api';
import { useDocuments } from '@/hooks/useDocuments';
import type { ModelInfo } from '@/lib/types';
import DocumentUpload from '@/components/rag/DocumentUpload';
import DocumentList from '@/components/rag/DocumentList';
import AgentFileUpload from '@/components/agent/AgentFileUpload';

export default function Sidebar() {
  const mode = useAppStore((s) => s.mode);
  const setMode = useAppStore((s) => s.setMode);
  const currentModel = useAppStore((s) => s.currentModel);
  const setCurrentModel = useAppStore((s) => s.setCurrentModel);
  const temperature = useAppStore((s) => s.temperature);
  const setTemperature = useAppStore((s) => s.setTemperature);
  const sidebarOpen = useAppStore((s) => s.sidebarOpen);
  const clearMessages = useAppStore((s) => s.clearMessages);
  const health = useAppStore((s) => s.health);

  const { documents, uploading, uploadProgress, upload, remove } = useDocuments();
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [isMobile, setIsMobile] = useState(false);

  // Load models on mount
  useEffect(() => {
    getModels()
      .then((data) => {
        setModels(data.models || []);
        if (data.default_model) setCurrentModel(data.default_model);
      })
      .catch(() => {
        setModels([{ name: currentModel, size: null, modified_at: null }]);
      });
  }, [currentModel, setCurrentModel]);

  // Track mobile breakpoint
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth <= 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  const sidebarClass = [
    'sidebar',
    !sidebarOpen && !isMobile ? 'collapsed' : '',
    isMobile && sidebarOpen ? 'mobile-open' : '',
  ]
    .filter(Boolean)
    .join(' ');

  const StatusDot = ({ status }: { status: 'healthy' | 'unhealthy' | 'checking' }) => (
    <span
      className={`status-item-dot ${
        status === 'healthy' ? 'dot-green' : status === 'checking' ? 'dot-checking' : 'dot-red'
      }`}
    />
  );

  const StatusBadge = ({ status }: { status: 'healthy' | 'unhealthy' | 'checking' }) => (
    <span className={`status-item-badge ${status}`}>
      {status === 'healthy' ? 'Healthy' : status === 'checking' ? 'Checking...' : 'Unreachable'}
    </span>
  );

  return (
    <aside className={sidebarClass}>
      {/* ── Logo ── */}
      <div className="sidebar-header">
        <div className="logo">
          <div className="logo-icon">
            <Layers size={18} />
          </div>
          <div className="logo-text-group">
            <span className="logo-title">SIH Assistant</span>
            <span className="logo-sub">AI Platform v3.0</span>
          </div>
        </div>
        <button className="icon-btn icon-btn-sm" onClick={clearMessages} title="New Chat">
          <Plus size={15} />
        </button>
      </div>

      {/* ── Scrollable Content ── */}
      <div className="sidebar-content">
        {/* Mode Selector */}
        <div className="sidebar-section">
          <p className="section-label">Mode</p>
          <div className="mode-pills">
            <button
              className={`mode-pill ${mode === 'chat' ? 'active-chat' : ''}`}
              onClick={() => setMode('chat')}
            >
              <MessageSquare size={13} />
              <span>Chat</span>
            </button>
            <button
              className={`mode-pill ${mode === 'rag' ? 'active-rag' : ''}`}
              onClick={() => setMode('rag')}
            >
              <FileText size={13} />
              <span>RAG</span>
            </button>
            <button
              className={`mode-pill ${mode === 'agent' ? 'active-agent' : ''}`}
              onClick={() => setMode('agent')}
            >
              <Settings size={13} />
              <span>Agent</span>
            </button>
          </div>
        </div>

        {/* RAG: Document Upload (visible in RAG mode) */}
        {mode === 'rag' && (
          <div className="sidebar-section">
            <p className="section-label">Documents</p>
            <DocumentUpload
              onUpload={upload}
              uploading={uploading}
              uploadProgress={uploadProgress}
            />
            <DocumentList documents={documents} onDelete={remove} />
          </div>
        )}

        {/* Agent: File Upload (visible in Agent mode) */}
        {mode === 'agent' && (
          <div className="sidebar-section">
            <p className="section-label">Agent Files</p>
            <AgentFileUpload />
          </div>
        )}

        {/* Model Selector */}
        <div className="sidebar-section">
          <p className="section-label">Model</p>
          <select
            className="styled-select"
            value={currentModel}
            onChange={(e) => setCurrentModel(e.target.value)}
          >
            {models.length === 0 ? (
              <option value="">Loading models...</option>
            ) : (
              models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.size ? `${m.name} (${m.size} GB)` : m.name}
                </option>
              ))
            )}
          </select>
        </div>

        {/* Temperature */}
        <div className="sidebar-section">
          <p className="section-label">Temperature</p>
          <div className="temp-row">
            <input
              type="range"
              className="range-slider"
              min="0"
              max="2"
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
            />
            <span className="temp-val">{temperature.toFixed(1)}</span>
          </div>
          <div className="temp-labels-row">
            <span>Precise</span>
            <span>Creative</span>
          </div>
        </div>

        {/* Services Status */}
        <div className="sidebar-section">
          <p className="section-label">Services</p>
          <div className="status-list">
            {(['api', 'ollama', 'qdrant', 'langgraph'] as const).map((svc) => (
              <div key={svc} className="status-item">
                <StatusDot status={health[svc]} />
                <span className="status-item-label">
                  {svc === 'api' ? 'API' : svc === 'ollama' ? 'Ollama' : svc === 'qdrant' ? 'Qdrant' : 'LangGraph'}
                </span>
                <StatusBadge status={health[svc]} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Footer ── */}
      <div className="sidebar-footer">
        <div className="footer-badge">Step 3 · Multi-Agent</div>
        <span className="footer-ver">v3.0.0</span>
      </div>
    </aside>
  );
}
