'use client';

/**
 * ChatHeader — top bar with mode indicator, model pill, and action buttons.
 */

import { useAppStore } from '@/stores/appStore';
import { Menu, Trash2 } from 'lucide-react';

const MODE_CONFIG = {
  chat: {
    title: 'Local LLM Chat',
    badge: 'Chat',
    badgeClass: 'badge-chat',
  },
  rag: {
    title: 'RAG Document Q&A',
    badge: 'RAG',
    badgeClass: 'badge-rag',
  },
  agent: {
    title: 'Multi-Agent Workflow',
    badge: 'Agent',
    badgeClass: 'badge-agent',
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
          className="icon-btn icon-btn-md"
          onClick={toggleSidebar}
          title="Toggle Sidebar"
        >
          <Menu size={18} />
        </button>
        <span className={`header-mode-badge ${config.badgeClass}`}>
          {config.badge}
        </span>
        <span className="header-title">{config.title}</span>
        <span className="header-subtitle">{currentModel}</span>
      </div>
      <div className="header-right">
        <button
          className="icon-btn icon-btn-md"
          onClick={clearMessages}
          title="Clear chat"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </header>
  );
}
