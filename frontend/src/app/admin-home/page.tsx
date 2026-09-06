'use client';

/**
 * Admin Home — premium landing page for administrators.
 * Shows system overview, quick actions, recent activity, and database connectivity.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Shield, Users, Database, Layers, Activity, Clock,
  ArrowRight, Zap, Server, Brain, Cpu, FileText,
  GitBranch, Lock, Eye, BarChart3, Sparkles,
  MonitorCheck, AlertTriangle, CheckCircle2, XCircle,
  HardDrive,
} from 'lucide-react';
import AmbientBackground from '@/components/layout/AmbientBackground';
import Sidebar from '@/components/layout/Sidebar';
import AuthGuard from '@/components/auth/AuthGuard';
import { useAuthStore } from '@/stores/authStore';
import { authFetch, listUsers, type AuthUser } from '@/lib/auth';

interface AuditEntry {
  id: number;
  action: string;
  username: string;
  details: string;
  timestamp: string;
}

interface DbStatus {
  mongodb: { available: boolean; connected: boolean };
  sql: { available: boolean; connected: boolean; engine: string };
}

export default function AdminHomePage() {
  const user = useAuthStore((s) => s.user);
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([]);
  const [dbStatus, setDbStatus] = useState<DbStatus | null>(null);
  const [health, setHealth] = useState<Record<string, string>>({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    // Load users
    try { setUsers(await listUsers()); } catch {}

    // Load audit logs
    try {
      const res = await authFetch('/api/governance/audit?limit=5');
      const data = await res.json();
      if (Array.isArray(data)) setAuditLogs(data);
    } catch {}

    // Load DB status
    try {
      const res = await authFetch('/api/db/status');
      const data = await res.json();
      setDbStatus(data);
    } catch {}

    // Load health
    try {
      const res = await fetch('/api/health');
      const data = await res.json();
      setHealth(data);
    } catch {}
  };

  const adminCount = users.filter(u => u.role === 'admin').length;
  const employeeCount = users.filter(u => u.role === 'employee').length;
  const activeCount = users.filter(u => u.is_active).length;

  const quickActions = [
    { href: '/admin', icon: Shield, label: 'Admin Panel', desc: 'Manage users & permissions', color: '#a78bfa' },
    { href: '/security', icon: Lock, label: 'Security', desc: 'AI guardrails & alerts', color: '#f472b6' },
    { href: '/audit', icon: Clock, label: 'Audit Log', desc: 'Activity tracking', color: '#fbbf24' },
    { href: '/sql-editor', icon: Database, label: 'SQL Editor', desc: 'Query & analyze data', color: '#38bdf8' },
    { href: '/governance', icon: Layers, label: 'Data Catalog', desc: 'Datasets & lineage', color: '#34d399' },
    { href: '/pipelines', icon: GitBranch, label: 'Pipelines', desc: 'ETL workflows', color: '#fb923c' },
    { href: '/jobs', icon: Activity, label: 'Jobs Monitor', desc: 'Scheduled tasks', color: '#a78bfa' },
    { href: '/databases', icon: HardDrive, label: 'Databases', desc: 'MongoDB & SQL', color: '#67e8f9' },
  ];

  const getTimeAgo = (ts: string) => {
    if (!ts) return '';
    const diff = Date.now() - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  const actionIcons: Record<string, typeof Shield> = {
    login: Eye, register: Users, change_role: Shield,
    deactivate_user: XCircle, query: Database, upload: FileText,
  };

  return (
    <AuthGuard requireAdmin>
      <AmbientBackground />
      <div className="app-layout">
        <Sidebar />
        <main className="chat-main">
          <div className="landing-page">

            {/* Hero Section */}
            <div className="landing-hero">
              <div className="landing-hero-content">
                <div className="landing-hero-badge">
                  <Shield size={14} />
                  <span>Administrator</span>
                </div>
                <h1 className="landing-hero-title">
                  Welcome back, <span className="landing-gradient-text">{user?.username}</span>
                </h1>
                <p className="landing-hero-subtitle">
                  Monitor your platform, manage users, and govern your data — all from one place.
                </p>
              </div>
              <div className="landing-hero-glow" />
            </div>

            {/* Stats Cards */}
            <div className="landing-stats-grid">
              <div className="landing-stat-card">
                <div className="landing-stat-icon" style={{ background: 'rgba(124,58,237,0.15)' }}>
                  <Users size={20} style={{ color: '#a78bfa' }} />
                </div>
                <div className="landing-stat-info">
                  <span className="landing-stat-value">{users.length}</span>
                  <span className="landing-stat-label">Total Users</span>
                </div>
              </div>
              <div className="landing-stat-card">
                <div className="landing-stat-icon" style={{ background: 'rgba(245,158,11,0.15)' }}>
                  <Shield size={20} style={{ color: '#fbbf24' }} />
                </div>
                <div className="landing-stat-info">
                  <span className="landing-stat-value">{adminCount}</span>
                  <span className="landing-stat-label">Admins</span>
                </div>
              </div>
              <div className="landing-stat-card">
                <div className="landing-stat-icon" style={{ background: 'rgba(56,189,248,0.15)' }}>
                  <Users size={20} style={{ color: '#38bdf8' }} />
                </div>
                <div className="landing-stat-info">
                  <span className="landing-stat-value">{employeeCount}</span>
                  <span className="landing-stat-label">Employees</span>
                </div>
              </div>
              <div className="landing-stat-card">
                <div className="landing-stat-icon" style={{ background: 'rgba(52,211,153,0.15)' }}>
                  <CheckCircle2 size={20} style={{ color: '#34d399' }} />
                </div>
                <div className="landing-stat-info">
                  <span className="landing-stat-value">{activeCount}</span>
                  <span className="landing-stat-label">Active</span>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="landing-section">
              <h2 className="landing-section-title">
                <Zap size={18} />
                Quick Actions
              </h2>
              <div className="landing-actions-grid">
                {quickActions.map((action) => (
                  <Link key={action.href} href={action.href} className="landing-action-card">
                    <div className="landing-action-icon" style={{ background: `${action.color}18` }}>
                      <action.icon size={20} style={{ color: action.color }} />
                    </div>
                    <div className="landing-action-info">
                      <span className="landing-action-label">{action.label}</span>
                      <span className="landing-action-desc">{action.desc}</span>
                    </div>
                    <ArrowRight size={14} className="landing-action-arrow" />
                  </Link>
                ))}
              </div>
            </div>

            {/* Two Column: Recent Activity + DB Connectivity */}
            <div className="landing-two-col">
              {/* Recent Activity */}
              <div className="landing-section">
                <h2 className="landing-section-title">
                  <Clock size={18} />
                  Recent Activity
                </h2>
                <div className="landing-activity-feed">
                  {auditLogs.length === 0 ? (
                    <div className="landing-empty-state">
                      <Activity size={24} />
                      <p>No recent activity</p>
                    </div>
                  ) : (
                    auditLogs.map((log) => {
                      const Icon = actionIcons[log.action] || Activity;
                      return (
                        <div key={log.id} className="landing-activity-item">
                          <div className="landing-activity-icon">
                            <Icon size={14} />
                          </div>
                          <div className="landing-activity-content">
                            <span className="landing-activity-action">
                              {log.action.replace(/_/g, ' ')}
                            </span>
                            {log.username && (
                              <span className="landing-activity-user">by {log.username}</span>
                            )}
                            {log.details && (
                              <span className="landing-activity-details">{log.details}</span>
                            )}
                          </div>
                          <span className="landing-activity-time">
                            {getTimeAgo(log.timestamp)}
                          </span>
                        </div>
                      );
                    })
                  )}
                  {auditLogs.length > 0 && (
                    <Link href="/audit" className="landing-view-all">
                      View all activity <ArrowRight size={14} />
                    </Link>
                  )}
                </div>
              </div>

              {/* Database Connectivity */}
              <div className="landing-section">
                <h2 className="landing-section-title">
                  <HardDrive size={18} />
                  Database Connectivity
                </h2>
                <div className="landing-db-cards">
                  {/* MongoDB */}
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
                          <><XCircle size={12} /> Disconnected</>
                        )}
                      </span>
                    </div>
                    <Link href="/databases" className="landing-db-action">
                      Manage Connection <ArrowRight size={14} />
                    </Link>
                  </div>

                  {/* SQL */}
                  <div className="landing-db-card">
                    <div className="landing-db-header">
                      <div className="landing-db-icon sql">
                        <BarChart3 size={18} />
                      </div>
                      <div className="landing-db-name">
                        <span>SQL Database</span>
                        <span className="landing-db-type">{dbStatus?.sql?.engine || 'SQLite (local)'}</span>
                      </div>
                      <span className={`landing-db-badge ${dbStatus?.sql?.connected ? 'connected' : 'disconnected'}`}>
                        {dbStatus?.sql?.connected ? (
                          <><CheckCircle2 size={12} /> Connected</>
                        ) : (
                          <><XCircle size={12} /> Disconnected</>
                        )}
                      </span>
                    </div>
                    <Link href="/databases" className="landing-db-action">
                      Open Query Editor <ArrowRight size={14} />
                    </Link>
                  </div>
                </div>
              </div>
            </div>

            {/* Service Health */}
            <div className="landing-section">
              <h2 className="landing-section-title">
                <MonitorCheck size={18} />
                Service Health
              </h2>
              <div className="landing-health-strip">
                {[
                  { key: 'api', label: 'FastAPI', icon: Server },
                  { key: 'ollama', label: 'Ollama LLM', icon: Brain },
                  { key: 'qdrant', label: 'Qdrant', icon: Database },
                  { key: 'langgraph', label: 'LangGraph', icon: Cpu },
                ].map((svc) => {
                  const status = health[svc.key];
                  const isHealthy = status === 'healthy' || (status as unknown) === true;
                  return (
                    <div key={svc.key} className="landing-health-item">
                      <svc.icon size={16} />
                      <span className="landing-health-label">{svc.label}</span>
                      <span className={`landing-health-dot ${isHealthy ? 'healthy' : 'unhealthy'}`} />
                    </div>
                  );
                })}
              </div>
            </div>

          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
