'use client';

/**
 * Databases Page — unified MongoDB + SQL connectivity management.
 * Admins can manage connections; all users can query.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft, Database, HardDrive, Server, Play, RefreshCw,
  CheckCircle2, XCircle, Table2, ChevronRight, ChevronDown,
  Search, Clock, Trash2, Copy, AlertTriangle, Loader2,
  FolderOpen, Code, BarChart3,
} from 'lucide-react';
import AmbientBackground from '@/components/layout/AmbientBackground';
import Sidebar from '@/components/layout/Sidebar';
import AuthGuard from '@/components/auth/AuthGuard';
import { useAuthStore } from '@/stores/authStore';
import { authFetch } from '@/lib/auth';

type Tab = 'mongodb' | 'sql';

interface SchemaField {
  name: string;
  types: string[];
}

interface QueryResult {
  success: boolean;
  documents?: Record<string, unknown>[];
  columns?: string[];
  rows?: Record<string, unknown>[];
  count?: number;
  row_count?: number;
  duration_ms?: number;
  error?: string;
  truncated?: boolean;
}

interface HistoryEntry {
  id: number;
  source_name: string;
  query_text: string;
  status: string;
  row_count: number | null;
  duration_ms: number | null;
  error_message: string | null;
  created_at: string;
}

export default function DatabasesPage() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === 'admin';

  const [activeTab, setActiveTab] = useState<Tab>('mongodb');

  // MongoDB state
  const [mongoConnStr, setMongoConnStr] = useState('mongodb://localhost:27017');
  const [mongoConnected, setMongoConnected] = useState(false);
  const [mongoConnecting, setMongoConnecting] = useState(false);
  const [mongoDatabases, setMongoDatabases] = useState<string[]>([]);
  const [mongoSelectedDb, setMongoSelectedDb] = useState('');
  const [mongoCollections, setMongoCollections] = useState<string[]>([]);
  const [mongoSelectedColl, setMongoSelectedColl] = useState('');
  const [mongoSchema, setMongoSchema] = useState<SchemaField[]>([]);
  const [mongoQuery, setMongoQuery] = useState('{}');
  const [mongoLimit, setMongoLimit] = useState(50);
  const [mongoResult, setMongoResult] = useState<QueryResult | null>(null);
  const [mongoRunning, setMongoRunning] = useState(false);

  // SQL state
  const [sqlQuery, setSqlQuery] = useState('SELECT name FROM sqlite_master WHERE type=\'table\';');
  const [sqlSource, setSqlSource] = useState('local');
  const [sqlResult, setSqlResult] = useState<QueryResult | null>(null);
  const [sqlRunning, setSqlRunning] = useState(false);
  const [sqlHistory, setSqlHistory] = useState<HistoryEntry[]>([]);
  const [sqlTables, setSqlTables] = useState<string[]>([]);
  const [sqlSelectedTable, setSqlSelectedTable] = useState('');
  const [sqlSchema, setSqlSchema] = useState<any[]>([]);
  const [sqlConnStr, setSqlConnStr] = useState('mysql+aiomysql://root:root@localhost:3307/mysql');
  const [showHistory, setShowHistory] = useState(false);

  // Error
  const [error, setError] = useState('');

  useEffect(() => {
    checkMongoStatus();
    loadSqlHistory();
  }, []);

  useEffect(() => {
    if (activeTab === 'sql' && (sqlSource === 'local' || sqlSource === 'external')) {
      loadSqlTables();
    }
  }, [activeTab, sqlSource]);

  // ── MongoDB Functions ──

  const checkMongoStatus = async () => {
    try {
      const res = await authFetch('/api/db/mongodb/status');
      const data = await res.json();
      setMongoConnected(data.connected);
      if (data.connected) {
        loadMongoDatabases();
      }
    } catch {}
  };

  const connectMongo = async () => {
    setMongoConnecting(true);
    setError('');
    try {
      const res = await authFetch('/api/db/mongodb/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ connection_string: mongoConnStr }),
      });
      const data = await res.json();
      if (res.ok) {
        setMongoConnected(true);
        setMongoDatabases(data.databases || []);
      } else {
        setError(data.detail || 'Failed to connect');
      }
    } catch (e: any) {
      setError(e.message || 'Connection failed');
    }
    setMongoConnecting(false);
  };

  const loadMongoDatabases = async () => {
    try {
      const res = await authFetch('/api/db/mongodb/databases');
      const data = await res.json();
      setMongoDatabases(data.databases || []);
    } catch {}
  };

  const selectMongoDb = async (db: string) => {
    setMongoSelectedDb(db);
    setMongoSelectedColl('');
    setMongoSchema([]);
    setMongoResult(null);
    try {
      const res = await authFetch(`/api/db/mongodb/collections?database=${encodeURIComponent(db)}`);
      const data = await res.json();
      setMongoCollections(data.collections || []);
    } catch {}
  };

  const selectMongoColl = async (coll: string) => {
    setMongoSelectedColl(coll);
    setMongoResult(null);
    try {
      const res = await authFetch(
        `/api/db/mongodb/schema?database=${encodeURIComponent(mongoSelectedDb)}&collection=${encodeURIComponent(coll)}`
      );
      const data = await res.json();
      setMongoSchema(data.fields || []);
    } catch {}
  };

  const runMongoQuery = async () => {
    if (!mongoSelectedDb || !mongoSelectedColl) return;
    setMongoRunning(true);
    setError('');
    try {
      let filter = {};
      try { filter = JSON.parse(mongoQuery); } catch { setError('Invalid JSON filter'); setMongoRunning(false); return; }
      const res = await authFetch('/api/db/mongodb/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          database: mongoSelectedDb,
          collection: mongoSelectedColl,
          filter,
          limit: mongoLimit,
        }),
      });
      const data = await res.json();
      setMongoResult(data);
    } catch (e: any) {
      setError(e.message);
    }
    setMongoRunning(false);
  };

  // ── SQL Functions ──

  const loadSqlTables = async () => {
    try {
      let querySql = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';";
      if (sqlSource === 'external') {
        querySql = "SHOW TABLES;";
      }
      const res = await authFetch('/api/db/sql/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          sql: querySql, 
          source_name: sqlSource,
          connection_string: sqlSource === 'external' ? sqlConnStr : undefined
        }),
      });
      const data = await res.json();
      if (data.success && data.rows) {
        if (sqlSource === 'external') {
          setSqlTables(data.rows.map((r: any) => Object.values(r)[0] as string));
        } else {
          setSqlTables(data.rows.map((r: any) => r.name));
        }
      }
    } catch {}
  };

  const selectSqlTable = async (table: string) => {
    setSqlSelectedTable(table);
    try {
      let querySql = `PRAGMA table_info('${table}');`;
      if (sqlSource === 'external') {
        querySql = `DESCRIBE ${table};`;
      }
      const res = await authFetch('/api/db/sql/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          sql: querySql, 
          source_name: sqlSource,
          connection_string: sqlSource === 'external' ? sqlConnStr : undefined
        }),
      });
      const data = await res.json();
      if (data.success && data.rows) {
        if (sqlSource === 'external') {
          setSqlSchema(data.rows.map((r: any) => ({ name: r.Field, type: r.Type })));
        } else {
          setSqlSchema(data.rows);
        }
      }
    } catch {}
  };

  const runSqlQuery = async () => {
    setSqlRunning(true);
    setError('');
    try {
      const res = await authFetch('/api/db/sql/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          sql: sqlQuery, 
          source_name: sqlSource,
          connection_string: sqlSource === 'external' ? sqlConnStr : undefined
        }),
      });
      const data = await res.json();
      setSqlResult(data);
      loadSqlHistory();
    } catch (e: any) {
      setError(e.message);
    }
    setSqlRunning(false);
  };

  const loadSqlHistory = async () => {
    try {
      const res = await authFetch('/api/db/sql/history?limit=20');
      const data = await res.json();
      setSqlHistory(data.history || []);
    } catch {}
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <AuthGuard>
      <AmbientBackground />
      <div className="app-layout">
        <Sidebar />
        <main className="chat-main">
          <div className="dashboard-page databases-page">
            <Link href={user?.role === 'admin' ? '/admin-home' : '/employee-home'} className="back-link">
              <ArrowLeft size={16} /> Back to Home
            </Link>

            <h1 className="dashboard-title">
              <HardDrive size={24} style={{ verticalAlign: 'middle', marginRight: 8 }} />
              Database Connectivity
            </h1>
            <p className="dashboard-subtitle">
              Connect and query MongoDB and SQL databases from a unified interface
            </p>

            {/* Error Banner */}
            {error && (
              <div className="db-error-banner">
                <AlertTriangle size={16} />
                <span>{error}</span>
                <button onClick={() => setError('')}>×</button>
              </div>
            )}

            {/* Tab Switcher */}
            <div className="db-tabs">
              <button
                className={`db-tab ${activeTab === 'mongodb' ? 'active mongo-active' : ''}`}
                onClick={() => setActiveTab('mongodb')}
              >
                <Database size={16} />
                MongoDB
                <span className={`db-tab-dot ${mongoConnected ? 'connected' : 'disconnected'}`} />
              </button>
              <button
                className={`db-tab ${activeTab === 'sql' ? 'active sql-active' : ''}`}
                onClick={() => setActiveTab('sql')}
              >
                <BarChart3 size={16} />
                SQL
                <span className="db-tab-dot connected" />
              </button>
            </div>

            {/* ═══════════════════════════ MongoDB Tab ═══════════════════════════ */}
            {activeTab === 'mongodb' && (
              <div className="db-panel">
                {/* Connection Section */}
                <div className="db-section">
                  <h3 className="db-section-title">
                    <Server size={16} /> Connection
                  </h3>
                  <div className="db-connection-row">
                    {isAdmin ? (
                      <>
                        <input
                          type="text"
                          className="db-input"
                          placeholder="mongodb://localhost:27017"
                          value={mongoConnStr}
                          onChange={(e) => setMongoConnStr(e.target.value)}
                        />
                        <button
                          className="db-connect-btn"
                          onClick={connectMongo}
                          disabled={mongoConnecting}
                        >
                          {mongoConnecting ? (
                            <><Loader2 size={14} className="db-spin" /> Connecting...</>
                          ) : mongoConnected ? (
                            <><RefreshCw size={14} /> Reconnect</>
                          ) : (
                            <><Play size={14} /> Connect</>
                          )}
                        </button>
                      </>
                    ) : (
                      <div className="db-readonly-status">
                        <span className={`landing-db-badge ${mongoConnected ? 'connected' : 'disconnected'}`}>
                          {mongoConnected ? (
                            <><CheckCircle2 size={12} /> Connected</>
                          ) : (
                            <><XCircle size={12} /> Not Connected — Contact Admin</>
                          )}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {mongoConnected && (
                  <>
                    {/* Database Browser */}
                    <div className="db-section">
                      <h3 className="db-section-title">
                        <FolderOpen size={16} /> Browser
                      </h3>
                      <div className="db-browser">
                        {/* Databases List */}
                        <div className="db-browser-col">
                          <div className="db-browser-header">Databases ({mongoDatabases.length})</div>
                          <div className="db-browser-list">
                            {mongoDatabases.map((db) => (
                              <button
                                key={db}
                                className={`db-browser-item ${mongoSelectedDb === db ? 'selected' : ''}`}
                                onClick={() => selectMongoDb(db)}
                              >
                                <Database size={13} />
                                <span>{db}</span>
                                {mongoSelectedDb === db ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                              </button>
                            ))}
                          </div>
                        </div>

                        {/* Collections List */}
                        <div className="db-browser-col">
                          <div className="db-browser-header">
                            Collections {mongoSelectedDb && `(${mongoCollections.length})`}
                          </div>
                          <div className="db-browser-list">
                            {mongoCollections.map((coll) => (
                              <button
                                key={coll}
                                className={`db-browser-item ${mongoSelectedColl === coll ? 'selected' : ''}`}
                                onClick={() => selectMongoColl(coll)}
                              >
                                <Table2 size={13} />
                                <span>{coll}</span>
                              </button>
                            ))}
                            {mongoSelectedDb && mongoCollections.length === 0 && (
                              <div className="db-browser-empty">No collections</div>
                            )}
                          </div>
                        </div>

                        {/* Schema */}
                        <div className="db-browser-col">
                          <div className="db-browser-header">
                            Schema {mongoSelectedColl && `(${mongoSchema.length} fields)`}
                          </div>
                          <div className="db-browser-list">
                            {mongoSchema.map((field) => (
                              <div key={field.name} className="db-schema-item">
                                <Code size={11} />
                                <span className="db-schema-name">{field.name}</span>
                                <span className="db-schema-type">{field.types.join(' | ')}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Query Editor */}
                    {mongoSelectedColl && (
                      <div className="db-section">
                        <h3 className="db-section-title">
                          <Search size={16} /> Query
                          <span className="db-query-target">
                            {mongoSelectedDb}.{mongoSelectedColl}
                          </span>
                        </h3>
                        <div className="db-query-editor">
                          <label className="db-label">Filter (JSON)</label>
                          <textarea
                            className="db-textarea"
                            value={mongoQuery}
                            onChange={(e) => setMongoQuery(e.target.value)}
                            rows={3}
                            placeholder='{"field": "value"}'
                          />
                          <div className="db-query-controls">
                            <div className="db-limit-row">
                              <label className="db-label">Limit:</label>
                              <input
                                type="number"
                                className="db-input db-input-sm"
                                value={mongoLimit}
                                onChange={(e) => setMongoLimit(Number(e.target.value))}
                                min={1}
                                max={1000}
                              />
                            </div>
                            <button className="db-run-btn" onClick={runMongoQuery} disabled={mongoRunning}>
                              {mongoRunning ? (
                                <><Loader2 size={14} className="db-spin" /> Running...</>
                              ) : (
                                <><Play size={14} /> Run Query</>
                              )}
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* MongoDB Results */}
                    {mongoResult && (
                      <div className="db-section">
                        <h3 className="db-section-title">
                          <Table2 size={16} /> Results
                          {mongoResult.success && (
                            <span className="db-result-meta">
                              {mongoResult.count} docs • {mongoResult.duration_ms}ms
                            </span>
                          )}
                        </h3>
                        {!mongoResult.success ? (
                          <div className="db-error-box">
                            <AlertTriangle size={14} />
                            {mongoResult.error}
                          </div>
                        ) : mongoResult.documents && mongoResult.documents.length > 0 ? (
                          <div className="db-results-table-wrap">
                            <table className="db-results-table">
                              <thead>
                                <tr>
                                  {Object.keys(mongoResult.documents[0]).map((k) => (
                                    <th key={k}>{k}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {mongoResult.documents.map((doc, i) => (
                                  <tr key={i}>
                                    {Object.values(doc).map((v, j) => (
                                      <td key={j}>
                                        {typeof v === 'object' ? JSON.stringify(v) : String(v ?? '')}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <div className="db-empty-result">No documents found</div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* ═══════════════════════════ SQL Tab ═══════════════════════════ */}
            {activeTab === 'sql' && (
              <div className="db-panel">
                {/* SQL Connection Info */}
                <div className="db-section">
                  <h3 className="db-section-title">
                    <Server size={16} /> Connection
                  </h3>
                  <div className="db-connection-info">
                    {sqlSource === 'local' || sqlSource === 'databricks' ? (
                      <div className="landing-db-card" style={{ marginBottom: 0 }}>
                        <div className="landing-db-header">
                          <div className="landing-db-icon sql">
                            <BarChart3 size={18} />
                          </div>
                          <div className="landing-db-name">
                            <span>{sqlSource === 'local' ? 'SQLite (Local)' : 'Databricks'}</span>
                            <span className="landing-db-type">{sqlSource === 'local' ? 'data/eurekax.db — Always available' : 'External Data Warehouse'}</span>
                          </div>
                          <span className="landing-db-badge connected">
                            <CheckCircle2 size={12} /> Connected
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="db-connection-row">
                        <input
                          type="text"
                          className="db-input"
                          placeholder="mysql+aiomysql://user:pass@host:port/db"
                          value={sqlConnStr}
                          onChange={(e) => setSqlConnStr(e.target.value)}
                        />
                      </div>
                    )}
                  </div>
                </div>

                {/* SQL Table Browser */}
                {sqlSource === 'local' && (
                  <div className="db-section">
                    <h3 className="db-section-title">
                      <FolderOpen size={16} /> Table Browser
                    </h3>
                    <div className="db-browser" style={{ gridTemplateColumns: '1fr 1fr' }}>
                      <div className="db-browser-col">
                        <div className="db-browser-header">Tables ({sqlTables.length})</div>
                        <div className="db-browser-list">
                          {sqlTables.map((t) => (
                            <button
                              key={t}
                              className={`db-browser-item ${sqlSelectedTable === t ? 'selected' : ''}`}
                              onClick={() => selectSqlTable(t)}
                            >
                              <Table2 size={13} />
                              <span>{t}</span>
                              {sqlSelectedTable === t ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                            </button>
                          ))}
                        </div>
                      </div>
                      <div className="db-browser-col">
                        <div className="db-browser-header">
                          Schema {sqlSelectedTable && `(${sqlSchema.length} columns)`}
                        </div>
                        <div className="db-browser-list">
                          {sqlSchema.map((col) => (
                            <div key={col.name} className="db-schema-item">
                              <Code size={11} />
                              <span className="db-schema-name">{col.name}</span>
                              <span className="db-schema-type">{col.type}</span>
                            </div>
                          ))}
                          {sqlSelectedTable && sqlSchema.length === 0 && (
                            <div className="db-browser-empty">No columns found</div>
                          )}
                          {!sqlSelectedTable && (
                            <div className="db-browser-empty">Select a table to view schema</div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* SQL Query Editor */}
                <div className="db-section">
                  <h3 className="db-section-title">
                    <Code size={16} /> Query Editor
                  </h3>
                  <div className="db-query-editor">
                    <textarea
                      className="db-textarea db-sql-textarea"
                      value={sqlQuery}
                      onChange={(e) => setSqlQuery(e.target.value)}
                      rows={5}
                      placeholder="SELECT * FROM users LIMIT 10;"
                      spellCheck={false}
                    />
                    <div className="db-query-controls">
                      <div className="db-source-row">
                        <label className="db-label">Source:</label>
                        <select
                          className="db-select"
                          value={sqlSource}
                          onChange={(e) => setSqlSource(e.target.value)}
                        >
                          <option value="local">Local SQLite</option>
                          <option value="external">External (MySQL)</option>
                          <option value="databricks">Databricks</option>
                        </select>
                      </div>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <button
                          className="db-history-btn"
                          onClick={() => setShowHistory(!showHistory)}
                        >
                          <Clock size={14} />
                          History
                        </button>
                        <button className="db-run-btn" onClick={runSqlQuery} disabled={sqlRunning}>
                          {sqlRunning ? (
                            <><Loader2 size={14} className="db-spin" /> Running...</>
                          ) : (
                            <><Play size={14} /> Run Query</>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* SQL History */}
                {showHistory && (
                  <div className="db-section">
                    <h3 className="db-section-title">
                      <Clock size={16} /> Query History
                    </h3>
                    <div className="db-history-list">
                      {sqlHistory.length === 0 ? (
                        <div className="db-empty-result">No query history</div>
                      ) : (
                        sqlHistory.map((h) => (
                          <div key={h.id} className="db-history-item">
                            <div className="db-history-status">
                              {h.status === 'success' ? (
                                <CheckCircle2 size={12} style={{ color: 'var(--green)' }} />
                              ) : (
                                <XCircle size={12} style={{ color: 'var(--red)' }} />
                              )}
                            </div>
                            <div className="db-history-info">
                              <code className="db-history-query">{h.query_text}</code>
                              <span className="db-history-meta">
                                {h.row_count !== null && `${h.row_count} rows • `}
                                {h.duration_ms !== null && `${h.duration_ms}ms • `}
                                {h.source_name}
                              </span>
                            </div>
                            <button
                              className="db-history-use"
                              onClick={() => { setSqlQuery(h.query_text); setShowHistory(false); }}
                              title="Use this query"
                            >
                              <Copy size={12} />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}

                {/* SQL Results */}
                {sqlResult && (
                  <div className="db-section">
                    <h3 className="db-section-title">
                      <Table2 size={16} /> Results
                      {sqlResult.success && (
                        <span className="db-result-meta">
                          {sqlResult.row_count} rows • {sqlResult.duration_ms}ms
                          {sqlResult.truncated && ' (truncated)'}
                        </span>
                      )}
                    </h3>
                    {!sqlResult.success ? (
                      <div className="db-error-box">
                        <AlertTriangle size={14} />
                        {sqlResult.error}
                      </div>
                    ) : sqlResult.rows && sqlResult.rows.length > 0 ? (
                      <div className="db-results-table-wrap">
                        <table className="db-results-table">
                          <thead>
                            <tr>
                              {(sqlResult.columns || []).map((col) => (
                                <th key={col}>{col}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {sqlResult.rows.map((row, i) => (
                              <tr key={i}>
                                {(sqlResult.columns || []).map((col) => (
                                  <td key={col}>
                                    {typeof row[col] === 'object'
                                      ? JSON.stringify(row[col])
                                      : String(row[col] ?? '')}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="db-empty-result">
                        Query executed successfully — {sqlResult.row_count || 0} rows affected
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
