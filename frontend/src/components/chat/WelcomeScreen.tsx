'use client';

/**
 * WelcomeScreen — clean enterprise hero with capability cards.
 */

import { MessageSquare, FileText, Code, Bot, Layers } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';

interface CapCard {
  icon: React.ElementType;
  title: string;
  desc: string;
  prompt: string;
  mode: 'chat' | 'rag' | 'agent';
}

const CAPABILITIES: CapCard[] = [
  {
    icon: MessageSquare,
    title: 'Chat',
    desc: 'General Q&A with local LLM',
    prompt: 'What is machine learning and how does it work?',
    mode: 'chat',
  },
  {
    icon: FileText,
    title: 'RAG',
    desc: 'Search indexed documents',
    prompt: 'What does the document say about the main topic?',
    mode: 'rag',
  },
  {
    icon: Code,
    title: 'Code Agent',
    desc: 'Generate & run Python',
    prompt: 'Write and execute Python code to calculate the first 20 Fibonacci numbers',
    mode: 'agent',
  },
  {
    icon: Bot,
    title: 'File Agent',
    desc: 'Read, write & manage files',
    prompt: 'List the files in the workspace directory',
    mode: 'agent',
  },
];

interface WelcomeScreenProps {
  onSend: (text: string) => void;
}

export default function WelcomeScreen({ onSend }: WelcomeScreenProps) {
  const setMode = useAppStore((s) => s.setMode);

  const handleClick = (card: CapCard) => {
    setMode(card.mode);
    setTimeout(() => onSend(card.prompt), 80);
  };

  return (
    <div className="welcome-screen">
      <div className="welcome-icon">
        <Layers size={28} />
      </div>
      <h2 className="welcome-title">EurekaX AI Assistant</h2>
      <p className="welcome-subtitle">
        Enterprise AI platform — local LLM, RAG document search, and multi-agent workflows
      </p>

      <div className="welcome-prompts">
        {CAPABILITIES.map((card) => (
          <button
            key={card.title}
            className="welcome-prompt-btn"
            onClick={() => handleClick(card)}
          >
            <card.icon size={16} />
            <div>
              <div style={{ fontWeight: 600, color: 'var(--text-1)', marginBottom: 2 }}>{card.title}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>{card.desc}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
