'use client';

/**
 * Data Governance Page — catalog browser, data source manager, lineage viewer.
 * Employees only see datasets they have been granted access to.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Database, Search, Tag, Plus, GitBranch, Layers, Lock, Shield } from 'lucide-react';
import AmbientBackground from '@/components/layout/AmbientBackground';
import Sidebar from '@/components/layout/Sidebar';
import AuthGuard from '@/components/auth/AuthGuard';
import { authFetch } from '@/lib/auth';
import { useAuthStore } from '@/stores/authStore';

interface CatalogEntry {
  id: number; table_name: string; data_source_id: string;
  description: string; tags: string[]; schema: Array<{name: string; type?: string}>;
  lineage: Record<string, unknown>; row_count?: number;
}

interface DataSourceItem {
  id: string; name: string; source_type: string; description: string;
}

export default function GovernancePage() {
  const user = useAuthStore((s) => s.user);
  const [entries, setEntries] = useState<CatalogEntry[]>([]);
  const [sources, setSources] = useState<DataSourceItem[]>([]);
  const [search, setSearch] = useState('');
  const [selectedEntry, setSelectedEntry] = useState<CatalogEntry | null>(null);
  const [showAddSource, setShowAddSource] = useState(false);
  const [newSource, setNewSource] = useState({ name: '', source_type: 'sql', description: '' });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [srcRes, catRes] = await Promise.all([
        authFetch('/api/governance/sources').then(r => r.json()),
        authFetch('/api/governance/catalog').then(r => r.json()),
      ]);
      setSources(Array.isArray(srcRes) ? srcRes : []);
      setEntries(Array.isArray(catRes) ? catRes : []);
    } catch {}
  };

  const addSource = async () => {
    try {
      await authFetch('/api/governance/sources', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSource),
      });
      setShowAddSource(false);
      setNewSource({ name: '', source_type: 'sql', description: '' });
      loadData();
    } catch {}
  };

  const filtered = entries.filter(e =>
    e.table_name.toLowerCase().includes(search.toLowerCase()) ||
    e.description.toLowerCase().includes(search.toLowerCase())
  );

  const isEmployee = user?.role === 'employee';

  return (
    <AuthGuard>
      <AmbientBackground />
      <div className="app-layout">
        <Sidebar />
        <main className="chat-main">
          <div className="dashboard-page">
            <Link href="/" className="back-link"><ArrowLeft size={16} /> Back to Chat</Link>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
              <h1 className="dashboard-title" style={{ margin: 0 }}>Data Catalog</h1>
              {isEmployee && (
                <span className="dash-status-badge" style={{ background: 'var(--amber-dim)', color: 'var(--amber)' }}>
                  <Lock size={10} /> Restricted View
                </span>
              )}
              {!isEmployee && (
                <span className="dash-status-badge healthy">
                  <Shield size={10} /> Full Access
                </span>
              )}
            </div>
            <p className="dashboard-subtitle">
              {isEmployee
                ? `Showing ${entries.length} datasets you have access to`
                : 'Browse data sources, explore schemas, and track lineage'
              }
            </p>

            {/* Search Bar */}
            <div className="governance-search">
              <Search size={16} />
              <input
                type="text" placeholder="Search tables, columns, tags..."
                value={search} onChange={e => setSearch(e.target.value)}
              />
            </div>

            {/* Data Sources */}
            <div className="sidebar-section">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <p className="section-label" style={{ margin: 0 }}>Data Sources ({sources.length})</p>
                {user?.role === 'admin' && (
                  <button className="governance-add-btn" onClick={() => setShowAddSource(!showAddSource)}>
                    <Plus size={14} /> Add Source
                  </button>
                )}
              </div>

              {showAddSource && (
                <div className="governance-add-form">
                  <input placeholder="Source name" value={newSource.name} onChange={e => setNewSource({...newSource, name: e.target.value})} />
                  <select value={newSource.source_type} onChange={e => setNewSource({...newSource, source_type: e.target.value})}>
                    <option value="sql">SQL Database</option>
                    <option value="mongodb">MongoDB</option>
                    <option value="csv">CSV Files</option>
                    <option value="excel">Excel</option>
                    <option value="image">Image Store</option>
                    <option value="databricks">Databricks</option>
                  </select>
                  <input placeholder="Description" value={newSource.description} onChange={e => setNewSource({...newSource, description: e.target.value})} />
                  <button className="login-submit-btn" style={{ height: 36, fontSize: '0.82rem' }} onClick={addSource}>Create</button>
                </div>
              )}

              <div className="governance-sources-grid">
                {sources.map(s => (
                  <div key={s.id} className="governance-source-card">
                    <Database size={16} />
                    <div>
                      <div className="governance-source-name">{s.name}</div>
                      <div className="governance-source-type">{s.source_type}</div>
                    </div>
                  </div>
                ))}
                {sources.length === 0 && <p style={{ color: 'var(--text-3)', fontSize: '0.82rem' }}>No data sources available</p>}
              </div>
            </div>

            {/* Catalog Entries */}
            <div className="sidebar-section">
              <p className="section-label">Catalog ({filtered.length} entries)</p>
              <div className="governance-catalog-list">
                {filtered.map(entry => (
                  <div key={entry.id} className={`governance-catalog-item ${selectedEntry?.id === entry.id ? 'selected' : ''}`} onClick={() => setSelectedEntry(entry)}>
                    <div className="governance-catalog-name">
                      <Layers size={14} /> {entry.table_name}
                    </div>
                    <div className="governance-catalog-desc">{entry.description || 'No description'}</div>
                    {entry.tags.length > 0 && (
                      <div className="governance-tags">
                        {entry.tags.map((t, i) => <span key={i} className="governance-tag"><Tag size={10} /> {t}</span>)}
                      </div>
                    )}
                  </div>
                ))}
                {filtered.length === 0 && <p style={{ color: 'var(--text-3)', fontSize: '0.82rem' }}>No catalog entries found</p>}
              </div>
            </div>

            {/* Detail Panel */}
            {selectedEntry && (
              <div className="sidebar-section">
                <p className="section-label">Schema: {selectedEntry.table_name}</p>
                <div className="governance-schema-table">
                  <table>
                    <thead><tr><th>Column</th><th>Type</th></tr></thead>
                    <tbody>
                      {selectedEntry.schema.map((col, i) => (
                        <tr key={i}><td>{col.name}</td><td>{col.type || 'unknown'}</td></tr>
                      ))}
                      {selectedEntry.schema.length === 0 && <tr><td colSpan={2}>No schema available</td></tr>}
                    </tbody>
                  </table>
                </div>
                {Object.keys(selectedEntry.lineage).length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <p className="section-label"><GitBranch size={14} /> Lineage</p>
                    <pre className="governance-lineage-json">{JSON.stringify(selectedEntry.lineage, null, 2)}</pre>
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
