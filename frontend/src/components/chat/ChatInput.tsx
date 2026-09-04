'use client';

/**
 * ChatInput — auto-resizing textarea with mode tag, send button, and keyboard shortcuts.
 */

import { useRef, useCallback } from 'react';
import { Send } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import { MAX_MESSAGE_LENGTH } from '@/lib/constants';

interface ChatInputProps {
  onSend: (text: string) => void;
}

const MODE_PLACEHOLDER = {
  chat: 'Type your message…',
  rag: 'Ask a question about your documents…',
  agent: 'Ask anything — agents will handle it automatically…',
} as const;

const MODE_TAG_CLASS = {
  chat: 'input-mode-tag',
  rag: 'input-mode-tag rag-tag',
  agent: 'input-mode-tag agent-tag',
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
      <div className="input-glass">
        <div className={MODE_TAG_CLASS[mode]}>
          {mode.charAt(0).toUpperCase() + mode.slice(1)}
        </div>
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
      <p className="input-hint">
        <kbd>Enter</kbd> to send &nbsp;·&nbsp; <kbd>Shift+Enter</kbd> for new
        line &nbsp;·&nbsp; Mode: <strong>{mode.charAt(0).toUpperCase() + mode.slice(1)}</strong>
      </p>
    </div>
  );
}
