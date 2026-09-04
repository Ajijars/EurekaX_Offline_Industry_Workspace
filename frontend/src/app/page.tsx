'use client';

/**
 * Main Chat Page — assembles Sidebar + ChatHeader + Messages + ChatInput.
 * Renders WelcomeScreen when no messages exist.
 */

import { useEffect, useRef } from 'react';
import AmbientBackground from '@/components/layout/AmbientBackground';
import Sidebar from '@/components/layout/Sidebar';
import ChatHeader from '@/components/layout/ChatHeader';
import WelcomeScreen from '@/components/chat/WelcomeScreen';
import MessageBubble from '@/components/chat/MessageBubble';
import TypingIndicator from '@/components/chat/TypingIndicator';
import ChatInput from '@/components/chat/ChatInput';
import { useChat } from '@/hooks/useChat';
import { useHealth } from '@/hooks/useHealth';

export default function HomePage() {
  const { messages, isStreaming, sendMessage, clearMessages } = useChat();
  useHealth(); // Start health polling

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const hasMessages = messages.length > 0;

  return (
    <>
      <AmbientBackground />
      <div className="app-layout">
        <Sidebar />
        <main className="chat-main">
          <ChatHeader />

          <div className="messages-container">
            {!hasMessages ? (
              <WelcomeScreen onSend={sendMessage} />
            ) : (
              <>
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
                {isStreaming && (
                  <TypingIndicator />
                )}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          <ChatInput onSend={sendMessage} />
        </main>
      </div>
    </>
  );
}
