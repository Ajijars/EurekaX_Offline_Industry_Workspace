'use client';

/**
 * WelcomeScreen — hero landing with capability cards.
 * Clicking a card sets the mode and fills the input with a sample prompt.
 */

import { Layers } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';

interface CapCard {
  emoji: string;
  title: string;
  desc: string;
  prompt: string;
  mode: 'chat' | 'rag' | 'agent';
  colorClass: string;
}

const CAPABILITIES: CapCard[] = [
  {
    emoji: '💬',
    title: 'Chat',
    desc: 'General Q&A with Ollama',
    prompt: 'What is machine learning and how does it work?',
    mode: 'chat',
    colorClass: 'cap-chat',
  },
  {
    emoji: '📚',
    title: 'RAG',
    desc: 'Search indexed documents',
    prompt: 'What does the document say about the main topic?',
    mode: 'rag',
    colorClass: 'cap-rag',
  },
  {
    emoji: '💻',
    title: 'Code Agent',
    desc: 'Generate & run Python',
    prompt: 'Write and execute Python code to calculate the first 20 Fibonacci numbers',
    mode: 'agent',
    colorClass: 'cap-code',
  },
  {
    emoji: '🤖',
    title: 'File Agent',
    desc: 'Read, write & manage files',
    prompt: 'List the files in the workspace directory',
    mode: 'agent',
    colorClass: 'cap-agent',
  },
];

interface WelcomeScreenProps {
  onSend: (text: string) => void;
}

export default function WelcomeScreen({ onSend }: WelcomeScreenProps) {
  const setMode = useAppStore((s) => s.setMode);

  const handleClick = (card: CapCard) => {
    setMode(card.mode);
    // Small delay for mode to update, then send
    setTimeout(() => onSend(card.prompt), 80);
  };

  return (
    <div className="welcome-screen">
      <div className="welcome-glow" aria-hidden="true" />
      <div className="welcome-logo">
        <Layers size={40} />
      </div>
      <h2 className="welcome-title">SIH Local AI Assistant</h2>
      <p className="welcome-subtitle">
        Fully offline · RAG-powered · Multi-Agent Orchestration
      </p>

      <div className="capability-cards">
        {CAPABILITIES.map((card) => (
          <div
            key={card.title}
            className={`cap-card ${card.colorClass}`}
            onClick={() => handleClick(card)}
          >
            <div className="cap-icon">{card.emoji}</div>
            <div className="cap-text">
              <strong>{card.title}</strong>
              <span>{card.desc}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
