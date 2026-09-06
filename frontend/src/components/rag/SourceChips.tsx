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

  // Group sources by filename
  const groupedSources = sources.reduce((acc, curr) => {
    const filename = curr.filename || 'Unknown';
    if (!acc[filename]) {
      acc[filename] = [];
    }
    acc[filename].push(curr);
    return acc;
  }, {} as Record<string, SourceChunk[]>);

  const uniqueFiles = Object.keys(groupedSources);

  return (
    <div className="sources-block">
      <div className="sources-label">Sources ({uniqueFiles.length} file{uniqueFiles.length !== 1 ? 's' : ''}, {sources.length} references)</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
        {uniqueFiles.map((filename, i) => {
          const chunks = groupedSources[filename];
          // Get the highest relevance score from this file's chunks
          const maxScore = Math.max(...chunks.map((s) => s.score));
          return (
            <span
              key={i}
              className="source-chip"
              title={`${chunks.length} chunks referenced from this file`}
            >
              📄 {filename}{' '}
              <span style={{ opacity: 0.6 }}>
                ({chunks.length} refs • ~{(maxScore * 100).toFixed(0)}% match)
              </span>
            </span>
          );
        })}
      </div>
    </div>
  );
}
