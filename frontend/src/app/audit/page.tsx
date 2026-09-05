'use client';

/**
 * Audit Log Page — compliance trail viewer (admin only).
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, FileText, Filter, Download } from 'lucide-react';
import AmbientBackground from '@/components/layout/AmbientBackground';
import AuthGuard from '@/components/auth/AuthGuard';
import { authFetch } from '@/lib/auth';

interface AuditEntry {
  id: number; user_id: string; action: string;
  resource_type: string; resource_id: string;
  details: Record<string, unknown> | null;
  timestamp: string;
}

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [filterAction, setFilterAction] = useState('');

  useEffect(() => { loadLogs(); }, [filterAction]);

  const loadLogs = async () => {
    try {
      const params = new URLSearchParams({ limit: '100' });
      if (filterAction) params.set('action', filterAction);
      const res = await authFetch(`/api/governance/audit?${params}`);
      const data = await res.json();
      setLogs(data.logs || []);
      setTotal(data.total || 0);
    } catch {}
  };

  const exportCSV = () => {
    const header = 'ID,Timestamp,User,Action,Resource Type,Resource ID\n';
    const rows = logs.map(l => `${l.id},"${l.timestamp}","${l.user_id}","${l.action}","${l.resource_type || ''}","${l.resource_id || ''}"`).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'audit_log.csv'; a.click();
  };

  return (
    <AuthGuard requireAdmin>
      <AmbientBackground />
      <div className="app-layout">
        <main className="chat-main">
          <div className="dashboard-page">
            <Link href="/" className="back-link"><ArrowLeft size={16} /> Back to Chat</Link>
            <h1 className="dashboard-title">Audit Log</h1>
            <p className="dashboard-subtitle">Compliance trail — {total} events recorded</p>

            <div className="audit-controls">
              <div className="audit-filter">
                <Filter size={14} />
                <select value={filterAction} onChange={e => setFilterAction(e.target.value)}>
                  <option value="">All Actions</option>
                  <option value="login">Login</option>
                  <option value="register">Register</option>
                  <option value="sql_query">SQL Query</option>
                  <option value="mongodb_query">MongoDB Query</option>
                  <option value="create_source">Create Source</option>
                  <option value="blocked_query">Blocked Query</option>
                </select>
              </div>
              <button className="governance-add-btn" onClick={exportCSV}><Download size={14} /> Export CSV</button>
            </div>

            <div className="audit-table-wrap">
              <table className="audit-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Action</th>
                    <th>Resource</th>
                    <th>User ID</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map(log => (
                    <tr key={log.id}>
                      <td className="audit-ts">{new Date(log.timestamp).toLocaleString()}</td>
                      <td><span className={`audit-action-badge ${log.action.includes('block') ? 'danger' : ''}`}>{log.action}</span></td>
                      <td>{log.resource_type || '—'}</td>
                      <td className="audit-uid">{log.user_id?.slice(0, 8) || '—'}</td>
                      <td className="audit-details">{log.details ? JSON.stringify(log.details).slice(0, 60) : '—'}</td>
                    </tr>
                  ))}
                  {logs.length === 0 && <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-3)' }}>No audit logs</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
