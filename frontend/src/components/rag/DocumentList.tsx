'use client';

/**
 * DocumentList — list of indexed RAG documents with delete button.
 */

import { X } from 'lucide-react';
import type { DocumentInfo } from '@/lib/types';

interface DocumentListProps {
  documents: DocumentInfo[];
  onDelete: (docId: string) => void;
}

export default function DocumentList({ documents, onDelete }: DocumentListProps) {
  if (documents.length === 0) {
    return <div className="doc-empty">No documents indexed yet</div>;
  }

  return (
    <div className="doc-list">
      {documents.map((doc) => {
        const ext = (doc.file_type || '').replace('.', '') || 'txt';
        return (
          <div key={doc.doc_id} className="doc-item">
            <div className="doc-icon">{ext}</div>
            <div className="doc-info">
              <div className="doc-name" title={doc.filename}>
                {doc.filename}
              </div>
              <div className="doc-meta">{doc.chunk_count} chunks</div>
            </div>
            <button
              className="doc-delete"
              onClick={() => onDelete(doc.doc_id)}
              title="Delete"
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
