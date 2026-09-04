'use client';

/**
 * ChatHeader — top bar with mode-colored title, model pill, and action buttons.
 */

import { useAppStore } from '@/stores/appStore';
import { Menu, Trash2 } from 'lucide-react';

const MODE_CONFIG = {
  chat: {
    title: 'Local LLM Chat',
    pill: 'Chat',
    pillClass: 'chat-pill',
  },
  rag: {
    title: 'RAG Document Q&A',
    pill: 'RAG',
    pillClass: 'rag-pill',
  },
  agent: {
    title: '🤖 Multi-Agent Workflow',
    pill: 'Agent',
    pillClass: 'agent-pill',
  },
} as const;

export default function ChatHeader() {
  const mode = useAppStore((s) => s.mode);
  const currentModel = useAppStore((s) => s.currentModel);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const clearMessages = useAppStore((s) => s.clearMessages);

  const config = MODE_CONFIG[mode];

  return (
    <header className="chat-header">
      <div className="header-left">
        <button
          className="icon-btn"
          onClick={toggleSidebar}
          title="Toggle Sidebar"
        >
          <Menu size={18} />
        </button>
        <div className="header-title-group">
          <h1 className="header-title">{config.title}</h1>
          <div className="header-meta">
            <span className="header-model-pill">{currentModel}</span>
            <span className={`header-mode-pill ${config.pillClass}`}>
              {config.pill}
            </span>
          </div>
        </div>
      </div>
      <div className="header-right">
        <button
          className="icon-btn"
          onClick={clearMessages}
          title="Clear chat"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </header>
  );
}
