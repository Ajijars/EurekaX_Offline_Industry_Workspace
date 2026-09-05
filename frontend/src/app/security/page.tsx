'use client';

/**
 * Security Dashboard — alerts, policies, anomaly monitoring (admin only).
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Shield, AlertTriangle, CheckCircle, Eye } from 'lucide-react';
import AmbientBackground from '@/components/layout/AmbientBackground';
import AuthGuard from '@/components/auth/AuthGuard';
import { authFetch } from '@/lib/auth';

interface SecurityAlertItem {
  id: number; alert_type: string; severity: string;
  message: string; resolved: boolean; created_at: string; user_id?: string;
}

interface Policies {
  guardrails: { pii_patterns: string[]; injection_patterns: string[] };
  query_sanitizer: { sql_blocked_employee: string[]; mongo_blocked_employee: string[] };
  rate_limits: { max_queries_per_minute: number; bulk_row_threshold: number };
}

export default function SecurityPage() {
  const [alerts, setAlerts] = useState<SecurityAlertItem[]>([]);
  const [policies, setPolicies] = useState<Policies | null>(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [alertRes, policyRes] = await Promise.all([
        authFetch('/api/security/alerts').then(r => r.json()),
        authFetch('/api/security/policies').then(r => r.json()),
      ]);
      setAlerts(alertRes);
      setPolicies(policyRes);
    } catch {}
  };

  const resolveAlert = async (id: number) => {
    await authFetch(`/api/security/alerts/${id}/resolve`, { method: 'PUT' });
    loadData();
  };

  const unresolvedCount = alerts.filter(a => !a.resolved).length;

  return (
    <AuthGuard requireAdmin>
      <AmbientBackground />
      <div className="app-layout">
        <main className="chat-main">
          <div className="dashboard-page">
            <Link href="/" className="back-link"><ArrowLeft size={16} /> Back to Chat</Link>
            <h1 className="dashboard-title">Security Dashboard</h1>
            <p className="dashboard-subtitle">AI guardrails, query policies, and anomaly alerts</p>

            {/* Alert Summary */}
            <div className="dashboard-grid">
              <div className="dash-card">
                <div className="dash-card-header">
                  <div className="dash-card-icon" style={{ background: unresolvedCount > 0 ? 'rgba(248,113,113,0.15)' : 'rgba(34,211,160,0.15)' }}>
                    <AlertTriangle size={18} style={{ color: unresolvedCount > 0 ? 'var(--red)' : 'var(--green)' }} />
                  </div>
                  <span className="dash-card-title">Active Alerts</span>
                </div>
                <div className="dash-card-value">{unresolvedCount}</div>
              </div>
              <div className="dash-card">
                <div className="dash-card-header">
                  <div className="dash-card-icon" style={{ background: 'rgba(124,58,237,0.15)' }}>
                    <Shield size={18} style={{ color: 'var(--chat-light)' }} />
                  </div>
                  <span className="dash-card-title">PII Patterns</span>
                </div>
                <div className="dash-card-value">{policies?.guardrails?.pii_patterns?.length || 0}</div>
              </div>
              <div className="dash-card">
                <div className="dash-card-header">
                  <div className="dash-card-icon" style={{ background: 'rgba(14,165,233,0.15)' }}>
                    <Eye size={18} style={{ color: 'var(--rag-light)' }} />
                  </div>
                  <span className="dash-card-title">SQL Restrictions</span>
                </div>
                <div className="dash-card-value">{policies?.query_sanitizer?.sql_blocked_employee?.length || 0}</div>
              </div>
            </div>

            {/* Active Alerts */}
            <div className="sidebar-section">
              <p className="section-label">Security Alerts</p>
              <div className="security-alerts-list">
                {alerts.map(alert => (
                  <div key={alert.id} className={`security-alert-item ${alert.severity} ${alert.resolved ? 'resolved' : ''}`}>
                    <div className="security-alert-header">
                      <span className={`security-severity-badge ${alert.severity}`}>{alert.severity}</span>
                      <span className="security-alert-type">{alert.alert_type}</span>
                      <span className="security-alert-time">{new Date(alert.created_at).toLocaleString()}</span>
                    </div>
                    <p className="security-alert-msg">{alert.message}</p>
                    {!alert.resolved && (
                      <button className="governance-add-btn" style={{ marginTop: 8 }} onClick={() => resolveAlert(alert.id)}>
                        <CheckCircle size={14} /> Resolve
                      </button>
                    )}
                  </div>
                ))}
                {alerts.length === 0 && <p style={{ color: 'var(--text-3)', fontSize: '0.82rem' }}>No security alerts</p>}
              </div>
            </div>

            {/* Policies */}
            {policies && (
              <div className="sidebar-section">
                <p className="section-label">Active Policies</p>
                <div className="governance-catalog-list">
                  <div className="governance-catalog-item">
                    <div className="governance-catalog-name">Employee SQL Restrictions</div>
                    <div className="governance-catalog-desc">{policies.query_sanitizer.sql_blocked_employee.join(' · ')}</div>
                  </div>
                  <div className="governance-catalog-item">
                    <div className="governance-catalog-name">PII Scanning Patterns</div>
                    <div className="governance-catalog-desc">{policies.guardrails.pii_patterns.join(' · ')}</div>
                  </div>
                  <div className="governance-catalog-item">
                    <div className="governance-catalog-name">Rate Limits</div>
                    <div className="governance-catalog-desc">Max {policies.rate_limits.max_queries_per_minute} queries/min · Bulk threshold: {policies.rate_limits.bulk_row_threshold} rows</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
