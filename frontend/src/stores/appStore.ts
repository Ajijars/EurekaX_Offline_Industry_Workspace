/**
 * Zustand global store for application state.
 *
 * Manages mode, model selection, temperature, conversation history,
 * documents, agent files, sidebar state, and service health.
 */

import { create } from 'zustand';
import type { AppMode, ChatMessage, DocumentInfo, ServiceHealth, AgentFileInfo } from '@/lib/types';
import { DEFAULT_MODEL, DEFAULT_TEMPERATURE } from '@/lib/constants';

interface AppState {
  // ── Mode ──
  mode: AppMode;
  setMode: (mode: AppMode) => void;

  // ── Model & Temperature ──
  currentModel: string;
  setCurrentModel: (model: string) => void;
  temperature: number;
  setTemperature: (temp: number) => void;

  // ── Chat ──
  messages: ChatMessage[];
  addMessage: (msg: ChatMessage) => void;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
  clearMessages: () => void;
  isStreaming: boolean;
  setIsStreaming: (v: boolean) => void;

  // ── RAG Documents ──
  documents: DocumentInfo[];
  setDocuments: (docs: DocumentInfo[]) => void;

  // ── Agent Files ──
  agentFiles: AgentFileInfo[];
  addAgentFile: (file: AgentFileInfo) => void;
  removeAgentFile: (index: number) => void;
  clearAgentFiles: () => void;

  // ── Sidebar ──
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;

  // ── Health ──
  health: ServiceHealth;
  setHealth: (patch: Partial<ServiceHealth>) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // ── Mode ──
  mode: 'chat',
  setMode: (mode) => set({ mode }),

  // ── Model & Temperature ──
  currentModel: DEFAULT_MODEL,
  setCurrentModel: (currentModel) => set({ currentModel }),
  temperature: DEFAULT_TEMPERATURE,
  setTemperature: (temperature) => set({ temperature }),

  // ── Chat ──
  messages: [],
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  updateMessage: (id, patch) =>
    set((s) => ({
      messages: s.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    })),
  clearMessages: () => set({ messages: [] }),
  isStreaming: false,
  setIsStreaming: (isStreaming) => set({ isStreaming }),

  // ── RAG Documents ──
  documents: [],
  setDocuments: (documents) => set({ documents }),

  // ── Agent Files ──
  agentFiles: [],
  addAgentFile: (file) =>
    set((s) => {
      if (s.agentFiles.some((f) => f.path === file.path || f.filename === file.filename)) return s;
      return { agentFiles: [...s.agentFiles, file] };
    }),
  removeAgentFile: (index) =>
    set((s) => ({ agentFiles: s.agentFiles.filter((_, i) => i !== index) })),
  clearAgentFiles: () => set({ agentFiles: [] }),

  // ── Sidebar ──
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),

  // ── Health ──
  health: {
    api: 'checking',
    ollama: 'checking',
    qdrant: 'checking',
    langgraph: 'checking',
  },
  setHealth: (patch) => set((s) => ({ health: { ...s.health, ...patch } })),
}));
