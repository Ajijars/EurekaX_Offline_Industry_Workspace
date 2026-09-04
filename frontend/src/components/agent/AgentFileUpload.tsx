'use client';

/**
 * AgentFileUpload — agent-specific file drop zone (amber themed) with file list.
 * Files are uploaded to the FastAPI workspace so Data / Vision / File agents can read them.
 */

import { useState, useRef, useCallback } from 'react';
import { Upload, X } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import { AGENT_FILE_TYPES } from '@/lib/constants';
import { uploadAgentFile } from '@/lib/api';

export default function AgentFileUpload() {
  const agentFiles = useAppStore((s) => s.agentFiles);
  const addAgentFile = useAppStore((s) => s.addAgentFile);
  const removeAgentFile = useAppStore((s) => s.removeAgentFile);
  const health = useAppStore((s) => s.health);

  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    async (files: FileList) => {
      setError(null);
      setUploading(true);
      try {
        for (let i = 0; i < files.length; i++) {
          const saved = await uploadAgentFile(files[i]);
          addAgentFile(saved);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed');
      } finally {
        setUploading(false);
      }
    },
    [addAgentFile],
  );

  return (
    <>
      <div
        className={`drop-zone drop-zone-agent ${dragOver ? 'drag-over' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files);
          }
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={AGENT_FILE_TYPES}
          hidden
          multiple
          onChange={(e) => {
            if (e.target.files) handleFiles(e.target.files);
            e.target.value = '';
          }}
        />
        <div className="drop-zone-inner">
          <div className="drop-icon drop-icon-agent">
            <Upload size={20} />
          </div>
          <span className="drop-label">
            {uploading ? 'Uploading…' : 'Drop files for agents'}
          </span>
          <span className="drop-hint">CSV · JSON · Excel · Images · TXT</span>
        </div>
      </div>

      {error && (
        <div className="doc-empty" style={{ color: 'var(--red)' }}>
          {error}
        </div>
      )}

      {/* File list */}
      <div className="doc-list">
        {agentFiles.length === 0 ? (
          <div className="doc-empty">No files added yet</div>
        ) : (
          agentFiles.map((f, i) => (
            <div key={f.path} className="doc-item">
              <div className="doc-icon doc-icon-agent">
                {f.filename.split('.').pop() || '?'}
              </div>
              <div className="doc-info">
                <div className="doc-name" title={f.filename}>
                  {f.filename}
                </div>
                <div className="doc-meta">
                  {(f.size_bytes / 1024).toFixed(1)} KB
                </div>
              </div>
              <button
                className="doc-delete"
                onClick={() => removeAgentFile(i)}
                title="Remove"
              >
                <X size={14} />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Agent system status */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: '4px',
      }}>
        <span style={{ fontSize: '0.68rem', color: 'var(--text-3)' }}>
          Agent System
        </span>
        <span
          className={`status-dot status-${health.langgraph === 'healthy' ? 'healthy' : health.langgraph === 'checking' ? 'checking' : 'unhealthy'}`}
          style={{
            fontSize: '0.62rem',
            fontWeight: 600,
            padding: '2px 8px',
            borderRadius: 'var(--r-full)',
            background:
              health.langgraph === 'healthy'
                ? 'rgba(34,211,160,.1)'
                : health.langgraph === 'checking'
                ? 'rgba(255,255,255,.06)'
                : 'rgba(248,113,113,.1)',
            color:
              health.langgraph === 'healthy'
                ? 'var(--green)'
                : health.langgraph === 'checking'
                ? 'var(--text-3)'
                : 'var(--red)',
          }}
        >
          {health.langgraph === 'healthy' ? 'Ready' : health.langgraph === 'checking' ? 'Checking' : 'Offline'}
        </span>
      </div>
    </>
  );
}
