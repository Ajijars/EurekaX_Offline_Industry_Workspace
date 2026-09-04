/**
 * useDocuments — CRUD operations for RAG documents.
 *
 * Loads, uploads, and deletes documents through the RAG API.
 * Updates the Zustand store with the current document list.
 */

'use client';

import { useEffect, useCallback, useState } from 'react';
import { useAppStore } from '@/stores/appStore';
import {
  listDocuments,
  uploadDocument,
  deleteDocument as apiDeleteDocument,
} from '@/lib/api';

export function useDocuments() {
  const documents = useAppStore((s) => s.documents);
  const setDocuments = useAppStore((s) => s.setDocuments);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');

  const loadDocuments = useCallback(async () => {
    try {
      const data = await listDocuments();
      setDocuments(data.documents || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  }, [setDocuments]);

  const upload = useCallback(
    async (file: File) => {
      setUploading(true);
      setUploadProgress(`Uploading ${file.name}...`);
      try {
        setUploadProgress('Processing & extracting text...');
        const result = await uploadDocument(file);
        setUploadProgress(
          `✓ ${file.name} indexed (${result.chunk_count} chunks)`,
        );
        await loadDocuments();
        // Clear progress after 2 seconds
        setTimeout(() => {
          setUploading(false);
          setUploadProgress('');
        }, 2000);
        return result;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Upload failed';
        setUploadProgress(`✗ ${message}`);
        setTimeout(() => {
          setUploading(false);
          setUploadProgress('');
        }, 3000);
        throw err;
      }
    },
    [loadDocuments],
  );

  const remove = useCallback(
    async (docId: string) => {
      try {
        await apiDeleteDocument(docId);
        await loadDocuments();
      } catch (err) {
        console.error('Failed to delete document:', err);
      }
    },
    [loadDocuments],
  );

  // Initial load
  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  return {
    documents,
    uploading,
    uploadProgress,
    upload,
    remove,
    reload: loadDocuments,
  };
}
