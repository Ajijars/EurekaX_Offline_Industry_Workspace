'use client';

/**
 * Jobs Monitor Page — Centralized dashboard for ML Notebooks and Pipelines.
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, GitBranch, FileText, Activity } from 'lucide-react';
import AmbientBackground from '@/components/layout/AmbientBackground';
import AuthGuard from '@/components/auth/AuthGuard';
import { authFetch } from '@/lib/auth';
import { useAuthStore } from '@/stores/authStore';

interface JobItem {
  id: string;
  type: 'notebook' | 'pipeline';
  name: string;
  created_by: string;
  creator_name: string;
  created_at: string;
  item_count: number;
}

export default function JobsPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      const res = await authFetch('/api/jobs');
      const data = await res.json();
      setJobs(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load jobs', err);
    } finally {
      setLoading(false);
    }
  };

  const handleJobClick = (job: JobItem) => {
    if (job.type === 'notebook') {
      // Navigate to Workspace. (Since we don't have deep linking for notebook id yet, 
      // just go to the workspace where they can select it).
      router.push('/workspace');
    } else {
      router.push('/pipelines');
    }
  };

  return (
    <AuthGuard>
      <AmbientBackground />
      <div className="app-layout">
        <main className="chat-main">
          <div className="dashboard-page">
            <Link href="/" className="back-link"><ArrowLeft size={16} /> Back to Chat</Link>
            <h1 className="dashboard-title">Jobs Monitor</h1>
            <p className="dashboard-subtitle">
              {user?.role === 'admin' 
                ? 'Global view of all Notebooks and Pipelines across the organization'
                : 'Manage your ML Notebooks and scheduled ETL Pipelines'}
            </p>

            <div className="dashboard-grid" style={{ gridTemplateColumns: '1fr', marginTop: 16 }}>
              <div>
                <p className="section-label">Active Jobs ({jobs.length})</p>
                
                {loading ? (
                  <p style={{ color: 'var(--text-3)', fontSize: '0.82rem', padding: 16 }}>Loading jobs...</p>
                ) : (
                  <div className="nb-list">
                    {jobs.map((job) => (
                      <div key={`${job.type}-${job.id}`} className="nb-list-item" onClick={() => handleJobClick(job)}>
                        {job.type === 'notebook' ? <FileText size={18} /> : <GitBranch size={18} />}
                        
                        <div className="nb-list-info">
                          <div className="nb-list-name">{job.name}</div>
                          <div className="nb-list-meta">
                            <span style={{ color: 'var(--text-2)' }}>{job.type === 'notebook' ? 'Notebook' : 'Pipeline'}</span>
                            {' · '}
                            {job.item_count} {job.type === 'notebook' ? 'cells' : 'steps'}
                            {' · '}
                            {job.created_at ? new Date(job.created_at).toLocaleDateString() : 'Unknown Date'}
                          </div>
                        </div>

                        {/* Creator Tag (useful for Admins) */}
                        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
                           <span className="audit-action-badge">
                              {job.creator_name}
                           </span>
                           <button className="icon-btn icon-btn-sm" title="Open Job">
                             <Activity size={14} />
                           </button>
                        </div>
                      </div>
                    ))}

                    {jobs.length === 0 && !loading && (
                      <p style={{ color: 'var(--text-3)', fontSize: '0.82rem', padding: 16 }}>
                        No jobs found.
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
