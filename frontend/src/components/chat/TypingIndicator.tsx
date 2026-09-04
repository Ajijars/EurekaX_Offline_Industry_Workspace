'use client';

/**
 * TypingIndicator — animated 3-dot bounce indicator shown while streaming.
 */

import { Layers } from 'lucide-react';

export default function TypingIndicator() {
  return (
    <div className="typing-indicator">
      <div className="message-avatar">
        <Layers size={16} />
      </div>
      <div className="typing-bubble">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  );
}
