'use client';

/**
 * Admin Panel — user management + dataset permission management (admin only).
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft, Shield, Users, Trash2, RefreshCw, Database,
  Lock, Unlock, ChevronDown, ChevronRight, Tag, Check, X
} from 'lucide-react';
import AmbientBackground from '@/components/layout/AmbientBackground';
import Sidebar from '@/components/layout/Sidebar';
import AuthGuard from '@/components/auth/AuthGuard';
import { authFetch, listUsers, changeUserRole, deactivateUser, type AuthUser } from '@/lib/auth';

interface CatalogEntry {
  id: number;
  table_name: string;
  description: string;
  tags: string[];
  data_source_id: string;
}

interface UserPermission {
  id: number;
  user_id: string;
  catalog_entry_id: number;
  access_level: string;
}

export default function AdminPage() {
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [entries, setEntries] = useState<CatalogEntry[]>([]);
  const [selectedUser, setSelectedUser] = useState<AuthUser | null>(null);
  const [userPerms, setUserPerms] = useState<UserPermission[]>([]);
  const [loadingPerms, setLoadingPerms] = useState(false);

  useEffect(() => {
    loadUsers();
    loadEntries();
  }, []);

  const loadUsers = async () => {
    try { setUsers(await listUsers()); } catch {}
  };

  const loadEntries = async () => {
    try {
      const res = await authFetch('/api/governance/catalog');
      const data = await res.json();
      if (Array.isArray(data)) setEntries(data);
    } catch {}
  };

  const loadUserPermissions = async (userId: string) => {
    setLoadingPerms(true);
    try {
      const res = await authFetch(`/api/governance/permissions/${userId}`);
      const data = await res.json();
      if (Array.isArray(data)) setUserPerms(data);
    } catch {}
    setLoadingPerms(false);
  };

  const selectUser = (user: AuthUser) => {
    if (selectedUser?.id === user.id) {
      setSelectedUser(null);
      setUserPerms([]);
    } else {
      setSelectedUser(user);
      loadUserPermissions(user.id);
    }
  };

  const toggleRole = async (userId: string, currentRole: string) => {
    try {
      const newRole = currentRole === 'admin' ? 'employee' : 'admin';
      await changeUserRole(userId, newRole);
      loadUsers();
    } catch (err: any) {
      alert(err.message || 'Failed to change role');
    }
  };

  const deactivate = async (userId: string) => {
    if (!confirm('Deactivate this user?')) return;
    try {
      await deactivateUser(userId);
      loadUsers();
    } catch (err: any) {
      alert(err.message || 'Failed to deactivate user');
    }
  };

  const grantAccess = async (entryId: number) => {
    if (!selectedUser) return;
    try {
      await authFetch('/api/governance/permissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: selectedUser.id,
          catalog_entry_id: entryId,
          access_level: 'read',
        }),
      });
      loadUserPermissions(selectedUser.id);
    } catch {}
  };

  const revokeAccess = async (permId: number) => {
    try {
      await authFetch(`/api/governance/permissions/${permId}`, { method: 'DELETE' });
      if (selectedUser) loadUserPermissions(selectedUser.id);
    } catch {}
  };

  const isGranted = (entryId: number) => userPerms.some(p => p.catalog_entry_id === entryId);
  const getPermId = (entryId: number) => userPerms.find(p => p.catalog_entry_id === entryId)?.id;

  const TAG_COLORS: Record<string, string> = {
    PII: 'var(--red)',
    sensitive: 'var(--red)',
    Confidential: 'var(--amber)',
    Finance: 'var(--green)',
    HR: 'var(--cyan)',
  };

  return (
    <AuthGuard requireAdmin>
      <AmbientBackground />
      <div className="app-layout">
        <Sidebar />
        <main className="chat-main">
          <div className="dashboard-page">
            <Link href="/" className="back-link"><ArrowLeft size={16} /> Back to Chat</Link>
            <h1 className="dashboard-title">Admin Panel</h1>
            <p className="dashboard-subtitle">Manage users, roles, and dataset permissions</p>

            {/* Stats Cards */}
            <div className="dashboard-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 24 }}>
              <div className="dash-card">
                <div className="dash-card-header">
                  <div className="dash-card-icon" style={{ background: 'rgba(124,58,237,0.15)' }}>
                    <Users size={18} style={{ color: '#a78bfa' }} />
                  </div>
                  <span className="dash-card-title">Total Users</span>
                </div>
                <div className="dash-card-value">{users.length}</div>
              </div>
              <div className="dash-card">
                <div className="dash-card-header">
                  <div className="dash-card-icon" style={{ background: 'rgba(245,158,11,0.15)' }}>
                    <Shield size={18} style={{ color: '#fbbf24' }} />
                  </div>
                  <span className="dash-card-title">Admins</span>
                </div>
                <div className="dash-card-value">{users.filter(u => u.role === 'admin').length}</div>
              </div>
              <div className="dash-card">
                <div className="dash-card-header">
                  <div className="dash-card-icon" style={{ background: 'rgba(14,165,233,0.15)' }}>
                    <Database size={18} style={{ color: '#38bdf8' }} />
                  </div>
                  <span className="dash-card-title">Datasets</span>
                </div>
                <div className="dash-card-value">{entries.length}</div>
              </div>
            </div>

            {/* Users Table */}
            <div style={{ marginBottom: 24 }}>
              <p className="section-label">Users</p>
              <div className="audit-table-wrap">
                <table className="audit-table">
                  <thead>
                    <tr><th>Username</th><th>Email</th><th>Role</th><th>Status</th><th>Joined</th><th>Actions</th></tr>
                  </thead>
                  <tbody>
                    {users.map(u => (
                      <tr
                        key={u.id}
                        style={{
                          cursor: u.role === 'employee' ? 'pointer' : 'default',
                          background: selectedUser?.id === u.id ? 'var(--bg-elevated)' : undefined,
                        }}
                        onClick={() => u.role === 'employee' && selectUser(u)}
                      >
                        <td style={{ fontWeight: 600 }}>
                          {u.username}
                          {selectedUser?.id === u.id ? <ChevronDown size={14} style={{ marginLeft: 4 }} /> : u.role === 'employee' ? <ChevronRight size={14} style={{ marginLeft: 4, opacity: 0.4 }} /> : null}
                        </td>
                        <td>{u.email}</td>
                        <td>
                          <span className="audit-action-badge" style={{
                            background: u.role === 'admin' ? 'var(--amber-dim)' : 'var(--primary-dim)',
                            color: u.role === 'admin' ? 'var(--amber)' : 'var(--primary-light)',
                          }}>
                            {u.role === 'admin' ? '🛡 Admin' : '👤 Employee'}
                          </span>
                        </td>
                        <td>
                          <span className={`dash-status-badge ${u.is_active ? 'healthy' : 'unhealthy'}`}>
                            <span className={`dash-status-dot ${u.is_active ? 'healthy' : 'unhealthy'}`} />
                            {u.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td>{new Date(u.created_at).toLocaleDateString()}</td>
                        <td>
                          <div style={{ display: 'flex', gap: 4 }}>
                            <button className="governance-add-btn" onClick={(e) => { e.stopPropagation(); toggleRole(u.id, u.role); }}>
                              <RefreshCw size={12} /> {u.role === 'admin' ? 'Demote' : 'Promote'}
                            </button>
                            {u.is_active && (
                              <button className="governance-add-btn" style={{ color: 'var(--red)' }} onClick={(e) => { e.stopPropagation(); deactivate(u.id); }}>
                                <Trash2 size={12} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Permission Management Panel */}
            {selectedUser && (
              <div style={{ marginBottom: 24 }}>
                <p className="section-label">
                  <Lock size={14} style={{ verticalAlign: 'middle', marginRight: 6 }} />
                  Dataset Permissions for {selectedUser.username}
                </p>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-2)', marginBottom: 12 }}>
                  Toggle access to catalog datasets. Employees can only query and view datasets they have been explicitly granted access to.
                </p>

                {loadingPerms ? (
                  <p style={{ color: 'var(--text-3)', fontSize: '0.82rem' }}>Loading permissions...</p>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 8 }}>
                    {entries.map(entry => {
                      const granted = isGranted(entry.id);
                      const permId = getPermId(entry.id);
                      return (
                        <div
                          key={entry.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '12px 16px',
                            borderRadius: 8,
                            background: granted ? 'var(--bg-elevated)' : 'var(--bg-surface)',
                            border: `1px solid ${granted ? 'var(--green)' : 'var(--border)'}`,
                            transition: 'all 0.15s ease',
                          }}
                        >
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <Database size={14} style={{ color: granted ? 'var(--green)' : 'var(--text-3)', flexShrink: 0 }} />
                              <span style={{ fontWeight: 600, fontSize: '0.84rem', color: 'var(--text-1)' }}>
                                {entry.table_name}
                              </span>
                            </div>
                            <p style={{ fontSize: '0.72rem', color: 'var(--text-3)', margin: '4px 0 0 22px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {entry.description}
                            </p>
                            {entry.tags.length > 0 && (
                              <div style={{ display: 'flex', gap: 3, marginTop: 4, marginLeft: 22, flexWrap: 'wrap' }}>
                                {entry.tags.slice(0, 4).map((t, i) => (
                                  <span key={i} style={{
                                    fontSize: '0.62rem',
                                    padding: '1px 6px',
                                    borderRadius: 99,
                                    background: TAG_COLORS[t] ? `${TAG_COLORS[t]}22` : 'var(--primary-dim)',
                                    color: TAG_COLORS[t] || 'var(--primary-light)',
                                    fontWeight: 500,
                                  }}>
                                    {t}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                          <button
                            onClick={() => granted && permId ? revokeAccess(permId) : grantAccess(entry.id)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 4,
                              padding: '6px 12px',
                              borderRadius: 6,
                              border: 'none',
                              cursor: 'pointer',
                              fontSize: '0.76rem',
                              fontWeight: 600,
                              fontFamily: 'var(--font)',
                              background: granted ? 'var(--green-dim)' : 'var(--bg-hover)',
                              color: granted ? 'var(--green)' : 'var(--text-2)',
                              transition: 'all 0.15s ease',
                              flexShrink: 0,
                              marginLeft: 12,
                            }}
                          >
                            {granted ? <><Unlock size={12} /> Granted</> : <><Lock size={12} /> Restricted</>}
                          </button>
                        </div>
                      );
                    })}
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
