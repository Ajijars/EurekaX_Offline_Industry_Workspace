'use client';

/**
 * ChatInput — auto-resizing textarea with send button, and keyboard shortcuts.
 */

import { useRef, useCallback } from 'react';
import { Send } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import { MAX_MESSAGE_LENGTH } from '@/lib/constants';

interface ChatInputProps {
  onSend: (text: string) => void;
}

const MODE_PLACEHOLDER = {
  chat: 'Type your message...',
  rag: 'Ask a question about your documents...',
  agent: 'Ask anything — agents will handle it automatically...',
} as const;

export default function ChatInput({ onSend }: ChatInputProps) {
  const mode = useAppStore((s) => s.mode);
  const isStreaming = useAppStore((s) => s.isStreaming);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const autoResize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 150) + 'px';
  }, []);

  const handleSend = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    const text = el.value.trim();
    if (!text || isStreaming) return;
    onSend(text);
    el.value = '';
    el.style.height = 'auto';
  }, [onSend, isStreaming]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return (
    <div className="input-area">
      <div className="input-wrapper">
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          placeholder={MODE_PLACEHOLDER[mode]}
          rows={1}
          maxLength={MAX_MESSAGE_LENGTH}
          onInput={autoResize}
          onKeyDown={handleKeyDown}
          autoFocus
        />
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={isStreaming}
          title="Send"
        >
          <Send size={18} />
        </button>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', marginTop: 12 }}>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-3)', fontFamily: 'var(--font)' }}>
          <kbd style={{ background: 'var(--bg-elevated)', padding: '2px 6px', borderRadius: 4, border: '1px solid var(--border)', color: 'var(--text-2)', fontFamily: 'var(--mono)', fontSize: '0.7rem' }}>Enter</kbd> to send &nbsp;·&nbsp; <kbd style={{ background: 'var(--bg-elevated)', padding: '2px 6px', borderRadius: 4, border: '1px solid var(--border)', color: 'var(--text-2)', fontFamily: 'var(--mono)', fontSize: '0.7rem' }}>Shift+Enter</kbd> for new
          line &nbsp;·&nbsp; Mode: <strong style={{ color: 'var(--text-2)' }}>{mode.charAt(0).toUpperCase() + mode.slice(1)}</strong>
        </p>
      </div>
    </div>
  );
}
