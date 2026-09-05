'use client';

/**
 * Pipelines Page — ETL pipeline builder, execution, scheduling.
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { ArrowLeft, Plus, Play, Trash2, Clock, CheckCircle, XCircle, GitBranch, Calendar } from 'lucide-react';
import AmbientBackground from '@/components/layout/AmbientBackground';
import AuthGuard from '@/components/auth/AuthGuard';
import { authFetch } from '@/lib/auth';

interface PipelineStep { type: string; sql?: string; code?: string; message?: string; source?: string; }
interface PipelineItem { id: string; name: string; description: string; steps: PipelineStep[]; created_at: string; }
interface RunItem { id: number; status: string; started_at: string; duration_ms?: number; error?: string; step_results: Array<{ type: string; success: boolean; }>; }
interface ScheduleItem { id: string; name: string; job_type: string; cron_expression: string; is_active: boolean; last_status?: string; }

export default function PipelinesPage() {
  const [pipelines, setPipelines] = useState<PipelineItem[]>([]);
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [runs, setRuns] = useState<RunItem[]>([]);
  const [selectedPipeline, setSelectedPipeline] = useState<PipelineItem | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newPipeline, setNewPipeline] = useState({ name: '', description: '', steps: [{ type: 'query', sql: '' }] as PipelineStep[] });
  const [showSchedule, setShowSchedule] = useState(false);
  const [newSchedule, setNewSchedule] = useState({ name: '', cron_expression: '0 * * * *' });

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    try {
      const [pRes, sRes] = await Promise.all([
        authFetch('/api/pipelines/').then(r => r.json()),
        authFetch('/api/pipelines/schedules/all').then(r => r.json()),
      ]);
      setPipelines(Array.isArray(pRes) ? pRes : []);
      setSchedules(Array.isArray(sRes) ? sRes : []);
    } catch {}
  };

  const createPipeline = async () => {
    if (!newPipeline.name.trim()) return;
    await authFetch('/api/pipelines/', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newPipeline),
    });
    setShowCreate(false);
    setNewPipeline({ name: '', description: '', steps: [{ type: 'query', sql: '' }] });
    loadAll();
  };

  const runPipeline = async (id: string) => {
    const res = await authFetch(`/api/pipelines/${id}/run`, { method: 'POST' });
    await loadRuns(id);
    loadAll();
  };

  const loadRuns = async (id: string) => {
    try {
      const res = await authFetch(`/api/pipelines/${id}/runs`);
      setRuns(await res.json());
    } catch {}
  };

  const selectPipeline = (p: PipelineItem) => {
    setSelectedPipeline(p);
    loadRuns(p.id);
  };

  const deletePipeline = async (id: string) => {
    await authFetch(`/api/pipelines/${id}`, { method: 'DELETE' });
    if (selectedPipeline?.id === id) { setSelectedPipeline(null); setRuns([]); }
    loadAll();
  };

  const createSchedule = async () => {
    if (!selectedPipeline || !newSchedule.name.trim()) return;
    await authFetch('/api/pipelines/schedules', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...newSchedule, job_type: 'pipeline', target_id: selectedPipeline.id }),
    });
    setShowSchedule(false);
    setNewSchedule({ name: '', cron_expression: '0 * * * *' });
    loadAll();
  };

  const addStep = () => {
    setNewPipeline(p => ({ ...p, steps: [...p.steps, { type: 'query', sql: '' }] }));
  };

  const updateStep = (idx: number, field: string, value: string) => {
    const steps = [...newPipeline.steps];
    (steps[idx] as unknown as Record<string, string>)[field] = value;
    setNewPipeline(p => ({ ...p, steps }));
  };

  return (
    <AuthGuard>
      <AmbientBackground />
      <div className="app-layout">
        <main className="chat-main">
          <div className="dashboard-page">
            <Link href="/" className="back-link"><ArrowLeft size={16} /> Back to Chat</Link>
            <h1 className="dashboard-title">Pipelines</h1>
            <p className="dashboard-subtitle">Build, run, and schedule ETL pipelines</p>

            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              <button className="sql-run-btn" onClick={() => setShowCreate(!showCreate)}><Plus size={14} /> New Pipeline</button>
            </div>

            {/* Create Form */}
            {showCreate && (
              <div className="pipeline-create-form">
                <input placeholder="Pipeline name" value={newPipeline.name} onChange={e => setNewPipeline(p => ({ ...p, name: e.target.value }))} className="sql-save-input" />
                <input placeholder="Description" value={newPipeline.description} onChange={e => setNewPipeline(p => ({ ...p, description: e.target.value }))} className="sql-save-input" />

                <p className="section-label" style={{ marginTop: 12 }}>Steps</p>
                {newPipeline.steps.map((step, i) => (
                  <div key={i} className="pipeline-step-row">
                    <select value={step.type} onChange={e => updateStep(i, 'type', e.target.value)} className="styled-select" style={{ width: 120 }}>
                      <option value="query">SQL Query</option>
                      <option value="python">Python</option>
                      <option value="notify">Notify</option>
                    </select>
                    {step.type === 'query' && <input placeholder="SQL query..." value={step.sql || ''} onChange={e => updateStep(i, 'sql', e.target.value)} className="sql-save-input" style={{ flex: 1 }} />}
                    {step.type === 'python' && <input placeholder="Python code..." value={step.code || ''} onChange={e => updateStep(i, 'code', e.target.value)} className="sql-save-input" style={{ flex: 1 }} />}
                    {step.type === 'notify' && <input placeholder="Message..." value={step.message || ''} onChange={e => updateStep(i, 'message', e.target.value)} className="sql-save-input" style={{ flex: 1 }} />}
                  </div>
                ))}
                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                  <button className="governance-add-btn" onClick={addStep}><Plus size={14} /> Add Step</button>
                  <button className="sql-run-btn" onClick={createPipeline}>Create Pipeline</button>
                </div>
              </div>
            )}

            {/* Pipeline List */}
            <div className="dashboard-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
              <div>
                <p className="section-label">Pipelines ({pipelines.length})</p>
                <div className="nb-list">
                  {pipelines.map(p => (
                    <div key={p.id} className={`nb-list-item ${selectedPipeline?.id === p.id ? 'selected' : ''}`} onClick={() => selectPipeline(p)}>
                      <GitBranch size={18} />
                      <div className="nb-list-info">
                        <div className="nb-list-name">{p.name}</div>
                        <div className="nb-list-meta">{p.steps.length} steps · {new Date(p.created_at).toLocaleDateString()}</div>
                      </div>
                      <button className="icon-btn icon-btn-sm" onClick={e => { e.stopPropagation(); runPipeline(p.id); }} title="Run"><Play size={14} /></button>
                      <button className="icon-btn icon-btn-sm" onClick={e => { e.stopPropagation(); deletePipeline(p.id); }} title="Delete"><Trash2 size={14} /></button>
                    </div>
                  ))}
                  {pipelines.length === 0 && <p style={{ color: 'var(--text-3)', fontSize: '0.82rem', padding: 16 }}>No pipelines yet</p>}
                </div>
              </div>

              {/* Runs & Schedule */}
              <div>
                {selectedPipeline && (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <p className="section-label">Run History</p>
                      <button className="governance-add-btn" onClick={() => setShowSchedule(!showSchedule)}><Calendar size={14} /> Schedule</button>
                    </div>

                    {showSchedule && (
                      <div className="pipeline-create-form" style={{ marginBottom: 12 }}>
                        <input placeholder="Schedule name" value={newSchedule.name} onChange={e => setNewSchedule(s => ({ ...s, name: e.target.value }))} className="sql-save-input" />
                        <input placeholder="Cron expression (e.g. 0 * * * *)" value={newSchedule.cron_expression} onChange={e => setNewSchedule(s => ({ ...s, cron_expression: e.target.value }))} className="sql-save-input" />
                        <button className="sql-run-btn" onClick={createSchedule} style={{ marginTop: 8 }}>Create Schedule</button>
                      </div>
                    )}

                    <div className="pipeline-runs-list">
                      {runs.map(run => (
                        <div key={run.id} className={`pipeline-run-item ${run.status}`}>
                          <div className="pipeline-run-header">
                            {run.status === 'success' ? <CheckCircle size={14} style={{ color: 'var(--green)' }} /> : run.status === 'failed' ? <XCircle size={14} style={{ color: 'var(--red)' }} /> : <Clock size={14} />}
                            <span className={`audit-action-badge ${run.status === 'failed' ? 'danger' : ''}`}>{run.status}</span>
                            <span className="nb-list-meta">{run.duration_ms != null ? `${run.duration_ms}ms` : ''}</span>
                            <span className="nb-list-meta">{new Date(run.started_at).toLocaleString()}</span>
                          </div>
                          {run.error && <div className="sql-error" style={{ marginTop: 4 }}>{run.error}</div>}
                        </div>
                      ))}
                      {runs.length === 0 && <p style={{ color: 'var(--text-3)', fontSize: '0.82rem' }}>No runs yet</p>}
                    </div>
                  </>
                )}

                {/* Schedules */}
                {schedules.length > 0 && (
                  <>
                    <p className="section-label" style={{ marginTop: 16 }}>Active Schedules</p>
                    {schedules.map(s => (
                      <div key={s.id} className="pipeline-run-item">
                        <div className="pipeline-run-header">
                          <Calendar size={14} />
                          <span className="nb-list-name">{s.name}</span>
                          <code style={{ fontSize: '0.75rem', color: 'var(--text-2)' }}>{s.cron_expression}</code>
                          <span className={`audit-action-badge ${s.is_active ? '' : 'danger'}`}>{s.is_active ? 'active' : 'paused'}</span>
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
