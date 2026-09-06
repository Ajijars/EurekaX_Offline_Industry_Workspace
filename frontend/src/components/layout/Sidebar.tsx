'use client';

/**
 * Sidebar — mode selector, document/agent uploads, model/temp controls, status indicators.
 * Now includes user info and logout.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Layers,
  Plus,
  MessageSquare,
  FileText,
  Settings,
  LogOut,
  LayoutDashboard,
  User as UserIcon,
  Shield,
  Database,
  GitBranch,
  Clock,
  Activity,
} from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import { useAuthStore } from '@/stores/authStore';
import { getModels } from '@/lib/api';
import { logout } from '@/lib/auth';
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

  const user = useAuthStore((s) => s.user);

  const { documents, uploading, uploadProgress, upload, remove } = useDocuments();
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    let mounted = true;
    getModels()
      .then((data) => {
        if (mounted) {
          setModels(data.models || []);
          const storeModel = useAppStore.getState().currentModel;
          // Only set to default if we don't have a model selected yet
          // or if the currently selected model isn't in the fetched list
          const hasCurrentModel = data.models?.some((m: any) => m.name === storeModel);
          if (data.default_model && (!storeModel || !hasCurrentModel)) {
            useAppStore.getState().setCurrentModel(data.default_model);
          }
        }
      })
      .catch(() => {
        if (mounted) {
          setModels([{ name: useAppStore.getState().currentModel, size: null, modified_at: null }]);
        }
      });
    return () => { mounted = false; };
  }, []);

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
            <span className="logo-title">EurekaX</span>
            <span className="logo-sub">Data Platform v4.0</span>
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

        {/* Navigation Links */}
        <div className="sidebar-section">
          <p className="section-label">Navigate</p>
          <div className="sidebar-nav-links">
            <Link href={user?.role === 'admin' ? '/admin-home' : '/employee-home'} className="sidebar-nav-link">
              <Layers size={15} />
              <span>Home</span>
            </Link>
            <Link href="/dashboard" className="sidebar-nav-link">
              <LayoutDashboard size={15} />
              <span>Dashboard</span>
            </Link>
            <Link href="/databases" className="sidebar-nav-link">
              <Database size={15} />
              <span>Databases</span>
            </Link>
            <Link href="/sql-editor" className="sidebar-nav-link">
              <Database size={15} />
              <span>SQL Editor</span>
            </Link>
            <Link href="/workspace" className="sidebar-nav-link">
              <FileText size={15} />
              <span>Notebooks</span>
            </Link>
            <Link href="/governance" className="sidebar-nav-link">
              <Layers size={15} />
              <span>Data Catalog</span>
            </Link>
            <Link href="/pipelines" className="sidebar-nav-link">
              <GitBranch size={15} />
              <span>Pipelines</span>
            </Link>
            <Link href="/jobs" className="sidebar-nav-link">
              <Activity size={15} />
              <span>Jobs Monitor</span>
            </Link>
            {user?.role === 'admin' && (
              <>
                <Link href="/security" className="sidebar-nav-link admin-link">
                  <Shield size={15} />
                  <span>Security</span>
                </Link>
                <Link href="/audit" className="sidebar-nav-link admin-link">
                  <Clock size={15} />
                  <span>Audit Log</span>
                </Link>
                <Link href="/admin" className="sidebar-nav-link admin-link">
                  <Shield size={15} />
                  <span>Admin Panel</span>
                </Link>
              </>
            )}
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

      {/* ── Footer: User Profile ── */}
      <div className="sidebar-footer">
        {user ? (
          <div className="sidebar-user">
            <div className="sidebar-user-avatar">
              <UserIcon size={16} />
            </div>
            <div className="sidebar-user-info">
              <span className="sidebar-user-name">{user.username}</span>
              <span className={`sidebar-user-role ${user.role}`}>
                {user.role === 'admin' ? '🛡️ Admin' : '👤 Employee'}
              </span>
            </div>
            <button
              className="icon-btn icon-btn-sm sidebar-logout-btn"
              onClick={logout}
              title="Logout"
            >
              <LogOut size={15} />
            </button>
          </div>
        ) : (
          <div className="footer-badge">EurekaX v4.0</div>
        )}
      </div>
    </aside>
  );
}

