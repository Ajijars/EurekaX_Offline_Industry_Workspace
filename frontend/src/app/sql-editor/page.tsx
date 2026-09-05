'use client';

/**
 * SQL Editor Page — execute queries with syntax-highlighted editor, results table, history.
 */

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { ArrowLeft, Play, Clock, Save, Download, Table2, AlertCircle, Bookmark, Database } from 'lucide-react';
import AmbientBackground from '@/components/layout/AmbientBackground';
import Sidebar from '@/components/layout/Sidebar';
import AuthGuard from '@/components/auth/AuthGuard';
import { authFetch } from '@/lib/auth';

interface QueryResult {
  success: boolean; columns: string[]; rows: Record<string, unknown>[];
  row_count?: number; duration_ms?: number; truncated?: boolean; error?: string;
}

interface HistoryItem {
  id: number; query_text: string; status: string; row_count?: number;
  duration_ms?: number; created_at: string; source_name: string;
}

interface SavedItem {
  id: number; name: string; query_text: string; description: string;
}

export default function SQLEditorPage() {
  const [sql, setSql] = useState('SELECT 1 as test_value, "hello" as greeting;');
  const [result, setResult] = useState<QueryResult | null>(null);
  const [running, setRunning] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [saved, setSaved] = useState<SavedItem[]>([]);
  const [activeTab, setActiveTab] = useState<'results' | 'history' | 'saved'>('results');
  const [saveName, setSaveName] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    loadHistory();
    loadSaved();
  }, []);

  const runQuery = async () => {
    if (!sql.trim()) return;
    setRunning(true);
    setActiveTab('results');
    try {
      const res = await authFetch('/api/query/sql', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql, source_name: 'local' }),
      });
      const data = await res.json();
      if (!res.ok) {
        setResult({ success: false, columns: [], rows: [], error: data.detail || 'Query failed' });
      } else {
        setResult(data);
      }
      loadHistory();
    } catch (err) {
      setResult({ success: false, columns: [], rows: [], error: 'Network error' });
    }
    setRunning(false);
  };

  const loadHistory = async () => {
    try {
      const res = await authFetch('/api/query/history');
      const data = await res.json();
      setHistory(data);
    } catch {}
  };

  const loadSaved = async () => {
    try {
      const res = await authFetch('/api/query/saved');
      const data = await res.json();
      setSaved(data);
    } catch {}
  };

  const saveQuery = async () => {
    if (!saveName.trim()) return;
    await authFetch('/api/query/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: saveName, query_text: sql }),
    });
    setSaveName('');
    loadSaved();
  };

  const exportCSV = () => {
    if (!result?.columns.length) return;
    const header = result.columns.join(',') + '\n';
    const rows = result.rows.map(r => result.columns.map(c => `"${r[c] ?? ''}"`).join(',')).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'query_results.csv'; a.click();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      runQuery();
    }
  };

  return (
    <AuthGuard>
      <AmbientBackground />
      <div className="app-layout">
        <Sidebar />
        <main className="chat-main">
          <div className="dashboard-page">
            <Link href="/" className="back-link"><ArrowLeft size={16} /> Back to Chat</Link>
            <h1 className="dashboard-title">SQL Editor</h1>
            <p className="dashboard-subtitle">Execute queries against local or connected data sources</p>

            {/* Editor */}
            <div className="sql-editor-wrap">
              <textarea
                ref={textareaRef}
                className="sql-textarea"
                value={sql}
                onChange={e => setSql(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Write your SQL query here..."
                spellCheck={false}
                rows={8}
              />
              <div className="sql-editor-actions">
                <button className="sql-run-btn" onClick={runQuery} disabled={running || !sql.trim()}>
                  {running ? <div className="login-btn-spinner" /> : <><Play size={14} /> Run (Ctrl+Enter)</>}
                </button>
                <div className="sql-save-group">
                  <input placeholder="Query name..." value={saveName} onChange={e => setSaveName(e.target.value)} className="sql-save-input" />
                  <button className="governance-add-btn" onClick={saveQuery} disabled={!saveName.trim()}>
                    <Save size={14} /> Save Query
                  </button>
                </div>
              </div>
            </div>

            {/* Tab Bar */}
            <div className="sql-tabs">
              <button className={`sql-tab ${activeTab === 'results' ? 'active' : ''}`} onClick={() => setActiveTab('results')}>
                <Table2 size={14} /> Results {result && result.success && <span className="sql-tab-count">{result.row_count}</span>}
              </button>
              <button className={`sql-tab ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')}>
                <Clock size={14} /> History <span className="sql-tab-count">{history.length}</span>
              </button>
              <button className={`sql-tab ${activeTab === 'saved' ? 'active' : ''}`} onClick={() => setActiveTab('saved')}>
                <Bookmark size={14} /> Saved <span className="sql-tab-count">{saved.length}</span>
              </button>
              {result?.success && result.columns.length > 0 && (
                <button className="governance-add-btn" style={{ marginLeft: 'auto' }} onClick={exportCSV}><Download size={14} /> Export</button>
              )}
            </div>

            {/* Results Area */}
            {activeTab === 'results' && (
              <div className="sql-results">
                {!result ? (
                  <div className="sql-empty-state">
                    <Database size={32} style={{ opacity: 0.5, marginBottom: 8 }} />
                    <p style={{ color: 'var(--text-2)', fontSize: '0.9rem' }}>No results to display.</p>
                    <p style={{ color: 'var(--text-3)', fontSize: '0.8rem' }}>Write and run a query to see the output here.</p>
                  </div>
                ) : !result.success ? (
                  <div className="sql-error"><AlertCircle size={16} /> {result.error}</div>
                ) : result.columns.length > 0 ? (
                  <>
                    <div className="sql-result-meta">
                      {result.row_count} rows · {result.duration_ms}ms{result.truncated ? ' · truncated' : ''}
                    </div>
                    <div className="audit-table-wrap">
                      <table className="audit-table">
                        <thead><tr>{result.columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
                        <tbody>
                          {result.rows.map((row, i) => (
                            <tr key={i}>{result.columns.map(c => <td key={c}>{String(row[c] ?? 'NULL')}</td>)}</tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                ) : (
                  <div className="sql-result-meta">Query executed successfully · {result.row_count ?? 0} rows affected · {result.duration_ms}ms</div>
                )}
              </div>
            )}

            {/* History */}
            {activeTab === 'history' && (
              <div className="sql-history-list">
                {history.map(h => (
                  <div key={h.id} className="sql-history-item" onClick={() => { setSql(h.query_text); setActiveTab('results'); }}>
                    <div className="sql-history-query">{h.query_text.slice(0, 100)}</div>
                    <div className="sql-history-meta">
                      <span className={`audit-action-badge ${h.status === 'error' ? 'danger' : ''}`}>{h.status}</span>
                      {h.row_count != null && <span>{h.row_count} rows</span>}
                      {h.duration_ms != null && <span>{h.duration_ms}ms</span>}
                      <span>{new Date(h.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                ))}
                {history.length === 0 && <p style={{ color: 'var(--text-3)', fontSize: '0.82rem', padding: 16 }}>No query history</p>}
              </div>
            )}

            {/* Saved */}
            {activeTab === 'saved' && (
              <div className="sql-history-list">
                {saved.map(s => (
                  <div key={s.id} className="sql-history-item" onClick={() => { setSql(s.query_text); setActiveTab('results'); }}>
                    <div className="governance-catalog-name"><Bookmark size={14} /> {s.name}</div>
                    <div className="sql-history-query">{s.query_text.slice(0, 100)}</div>
                  </div>
                ))}
                {saved.length === 0 && <p style={{ color: 'var(--text-3)', fontSize: '0.82rem', padding: 16 }}>No saved queries</p>}
              </div>
            )}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
