'use client';

/**
 * DocumentUpload — drag-and-drop upload zone with progress bar for RAG documents.
 */

import { useState, useRef, useCallback } from 'react';
import { Upload } from 'lucide-react';
import { RAG_FILE_TYPES } from '@/lib/constants';

interface DocumentUploadProps {
  onUpload: (file: File) => Promise<unknown>;
  uploading: boolean;
  uploadProgress: string;
}

export default function DocumentUpload({
  onUpload,
  uploading,
  uploadProgress,
}: DocumentUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    async (files: FileList) => {
      for (let i = 0; i < files.length; i++) {
        try {
          await onUpload(files[i]);
        } catch {
          // Error handled by hook
        }
      }
    },
    [onUpload],
  );

  return (
    <>
      <div
        className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
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
          accept={RAG_FILE_TYPES}
          hidden
          multiple
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleFiles(e.target.files);
            }
            e.target.value = '';
          }}
        />
        <div className="drop-zone-inner">
          <div className="drop-icon">
            <Upload size={22} />
          </div>
          <span className="drop-label">Drop or click to upload</span>
          <span className="drop-hint">PDF · DOCX · PPTX · TXT · CSV</span>
        </div>
      </div>

      {/* Upload Progress */}
      {uploading && (
        <div className="upload-progress-wrap">
          <div className="upload-progress-bar">
            <div
              className="upload-progress-fill"
              style={{ width: uploadProgress.startsWith('✓') ? '100%' : '60%' }}
            />
          </div>
          <span className="upload-progress-text">{uploadProgress}</span>
        </div>
      )}
    </>
  );
}
