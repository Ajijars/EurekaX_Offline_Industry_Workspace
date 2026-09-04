'use client';

/**
 * SourceChips — displays RAG source citation chips with filename + similarity score.
 */

import type { SourceChunk } from '@/lib/types';

interface SourceChipsProps {
  sources: SourceChunk[];
}

export default function SourceChips({ sources }: SourceChipsProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources-block">
      <div className="sources-label">Sources ({sources.length})</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
        {sources.map((s, i) => (
          <span
            key={i}
            className="source-chip"
            title={s.chunk_text?.substring(0, 200) || ''}
          >
            📄 {s.filename || 'Unknown'}{' '}
            <span style={{ opacity: 0.6 }}>{(s.score * 100).toFixed(0)}%</span>
          </span>
        ))}
      </div>
    </div>
  );
}
