'use client';

/**
 * Employee Home — focused landing page for employees.
 * Shows personalized greeting, quick access tiles, and permitted datasets.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  MessageSquare, FileText, Database, Layers, ArrowRight,
  Sparkles, Zap, Brain, BookOpen, FolderOpen, Search,
  CheckCircle2, Lock, Table2, HardDrive,
} from 'lucide-react';
import AmbientBackground from '@/components/layout/AmbientBackground';
import Sidebar from '@/components/layout/Sidebar';
import AuthGuard from '@/components/auth/AuthGuard';
import { useAuthStore } from '@/stores/authStore';
import { authFetch } from '@/lib/auth';

interface CatalogEntry {
  id: number;
  table_name: string;
  description: string;
  tags: string[];
  data_source_id: string;
}

interface DbStatus {
  mongodb: { available: boolean; connected: boolean };
  sql: { available: boolean; connected: boolean; engine: string };
}

export default function EmployeeHomePage() {
  const user = useAuthStore((s) => s.user);
  const [permittedDatasets, setPermittedDatasets] = useState<CatalogEntry[]>([]);
  const [dbStatus, setDbStatus] = useState<DbStatus | null>(null);
  const [greeting, setGreeting] = useState('');

  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting('Good morning');
    else if (hour < 17) setGreeting('Good afternoon');
    else setGreeting('Good evening');

    loadData();
  }, []);

  const loadData = async () => {
    // Load permitted datasets
    try {
      const res = await authFetch('/api/governance/catalog');
      const data = await res.json();
      if (Array.isArray(data)) setPermittedDatasets(data);
    } catch {}

    // Load DB status
    try {
      const res = await authFetch('/api/db/status');
      const data = await res.json();
      setDbStatus(data);
    } catch {}
  };

  const quickAccess = [
    { href: '/', icon: MessageSquare, label: 'AI Chat', desc: 'Ask questions to the AI assistant', color: '#a78bfa', gradient: 'linear-gradient(135deg, rgba(124,58,237,0.12), rgba(167,139,250,0.08))' },
    { href: '/', icon: Brain, label: 'RAG Documents', desc: 'Upload & query documents', color: '#f472b6', gradient: 'linear-gradient(135deg, rgba(236,72,153,0.12), rgba(244,114,182,0.08))' },
    { href: '/sql-editor', icon: Database, label: 'SQL Editor', desc: 'Query permitted datasets', color: '#38bdf8', gradient: 'linear-gradient(135deg, rgba(14,165,233,0.12), rgba(56,189,248,0.08))' },
    { href: '/workspace', icon: BookOpen, label: 'Notebooks', desc: 'Code notebooks & analysis', color: '#34d399', gradient: 'linear-gradient(135deg, rgba(16,185,129,0.12), rgba(52,211,153,0.08))' },
    { href: '/governance', icon: Layers, label: 'Data Catalog', desc: 'Browse available datasets', color: '#fbbf24', gradient: 'linear-gradient(135deg, rgba(245,158,11,0.12), rgba(251,191,36,0.08))' },
    { href: '/databases', icon: HardDrive, label: 'Databases', desc: 'MongoDB & SQL connectivity', color: '#67e8f9', gradient: 'linear-gradient(135deg, rgba(34,211,238,0.12), rgba(103,232,249,0.08))' },
  ];

  const TAG_COLORS: Record<string, string> = {
    PII: '#ef4444', sensitive: '#ef4444', Confidential: '#f59e0b',
    Finance: '#10b981', HR: '#06b6d4', Public: '#8b5cf6',
  };

  return (
    <AuthGuard>
      <AmbientBackground />
      <div className="app-layout">
        <Sidebar />
        <main className="chat-main">
          <div className="landing-page">

            {/* Hero Section */}
            <div className="landing-hero employee-hero">
              <div className="landing-hero-content">
                <div className="landing-hero-badge employee-badge">
                  <Sparkles size={14} />
                  <span>Workspace</span>
                </div>
                <h1 className="landing-hero-title">
                  {greeting}, <span className="landing-gradient-text employee-gradient">{user?.username}</span>
                </h1>
                <p className="landing-hero-subtitle">
                  Access your data, run queries, and leverage AI to get insights from your workspace.
                </p>
              </div>
              <div className="landing-hero-glow employee-glow" />
            </div>

            {/* Quick Access Tiles */}
            <div className="landing-section">
              <h2 className="landing-section-title">
                <Zap size={18} />
                Quick Access
              </h2>
              <div className="landing-tiles-grid">
                {quickAccess.map((tile) => (
                  <Link key={tile.label} href={tile.href} className="landing-tile">
                    <div className="landing-tile-bg" style={{ background: tile.gradient }} />
                    <div className="landing-tile-icon" style={{ color: tile.color }}>
                      <tile.icon size={28} />
                    </div>
                    <span className="landing-tile-label">{tile.label}</span>
                    <span className="landing-tile-desc">{tile.desc}</span>
                    <div className="landing-tile-arrow" style={{ color: tile.color }}>
                      <ArrowRight size={16} />
                    </div>
                  </Link>
                ))}
              </div>
            </div>

            {/* Two Column: Permitted Datasets + DB Connectivity */}
            <div className="landing-two-col">
              {/* Permitted Datasets */}
              <div className="landing-section">
                <h2 className="landing-section-title">
                  <FolderOpen size={18} />
                  Available Datasets
                </h2>
                <div className="landing-datasets-list">
                  {permittedDatasets.length === 0 ? (
                    <div className="landing-empty-state">
                      <Lock size={24} />
                      <p>No datasets available</p>
                      <span>Contact your admin for access</span>
                    </div>
                  ) : (
                    permittedDatasets.slice(0, 6).map((ds) => (
                      <div key={ds.id} className="landing-dataset-item">
                        <div className="landing-dataset-icon">
                          <Table2 size={14} />
                        </div>
                        <div className="landing-dataset-info">
                          <span className="landing-dataset-name">{ds.table_name}</span>
                          <span className="landing-dataset-desc">
                            {ds.description || 'No description'}
                          </span>
                          {ds.tags.length > 0 && (
                            <div className="landing-dataset-tags">
                              {ds.tags.slice(0, 3).map((t, i) => (
                                <span
                                  key={i}
                                  className="landing-dataset-tag"
                                  style={{
                                    background: TAG_COLORS[t] ? `${TAG_COLORS[t]}18` : 'rgba(139,92,246,0.1)',
                                    color: TAG_COLORS[t] || '#8b5cf6',
                                  }}
                                >
                                  {t}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <CheckCircle2 size={14} className="landing-dataset-check" />
                      </div>
                    ))
                  )}
                  {permittedDatasets.length > 6 && (
                    <Link href="/governance" className="landing-view-all">
                      View all {permittedDatasets.length} datasets <ArrowRight size={14} />
                    </Link>
                  )}
                </div>
              </div>

              {/* Database Connectivity */}
              <div className="landing-section">
                <h2 className="landing-section-title">
                  <HardDrive size={18} />
                  Database Status
                </h2>
                <div className="landing-db-cards">
                  <div className="landing-db-card">
                    <div className="landing-db-header">
                      <div className="landing-db-icon mongo">
                        <Database size={18} />
                      </div>
                      <div className="landing-db-name">
                        <span>MongoDB</span>
                        <span className="landing-db-type">NoSQL Document Store</span>
                      </div>
                      <span className={`landing-db-badge ${dbStatus?.mongodb?.connected ? 'connected' : 'disconnected'}`}>
                        {dbStatus?.mongodb?.connected ? (
                          <><CheckCircle2 size={12} /> Connected</>
                        ) : (
                          <><Lock size={12} /> Not Connected</>
                        )}
                      </span>
                    </div>
                  </div>

                  <div className="landing-db-card">
                    <div className="landing-db-header">
                      <div className="landing-db-icon sql">
                        <Search size={18} />
                      </div>
                      <div className="landing-db-name">
                        <span>SQL Database</span>
                        <span className="landing-db-type">{dbStatus?.sql?.engine || 'SQLite (local)'}</span>
                      </div>
                      <span className={`landing-db-badge ${dbStatus?.sql?.connected ? 'connected' : 'disconnected'}`}>
                        {dbStatus?.sql?.connected ? (
                          <><CheckCircle2 size={12} /> Ready</>
                        ) : (
                          <><Lock size={12} /> Offline</>
                        )}
                      </span>
                    </div>
                    <Link href="/sql-editor" className="landing-db-action">
                      Open SQL Editor <ArrowRight size={14} />
                    </Link>
                  </div>
                </div>

                {/* Quick Tip */}
                <div className="landing-tip">
                  <Sparkles size={14} />
                  <span>
                    <strong>Tip:</strong> Use the AI Chat with RAG mode to ask questions about your uploaded documents.
                  </span>
                </div>
              </div>
            </div>

          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
