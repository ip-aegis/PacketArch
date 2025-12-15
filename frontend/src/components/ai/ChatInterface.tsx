/**
 * Chat Interface - Display messages and tool results
 */

import React, { useEffect, useRef } from 'react';
import { Space, Spin } from 'antd';
import { useAIAssistantStore } from '../../stores/aiAssistantStore';
import MessageBubble from './MessageBubble';
import SuggestionCard from './SuggestionCard';

const ChatInterface: React.FC = () => {
  const { messages, pendingActions, isProcessing } = useAIAssistantStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {messages.length === 0 && !isProcessing && (
        <div
          style={{
            textAlign: 'center',
            padding: '40px 20px',
            color: '#8aa4bc',
          }}
        >
          <p>Ask me anything about your scenario!</p>
          <p style={{ fontSize: 12, marginTop: 8, color: '#6a8caf' }}>
            I can help you add devices, create flows, validate topology, and more.
          </p>
        </div>
      )}

      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {/* Pending actions/suggestions */}
      {pendingActions.map((action) => (
        <SuggestionCard key={action.id} action={action} />
      ))}

      {/* Processing indicator */}
      {isProcessing && (
        <div style={{ textAlign: 'center', padding: '8px' }}>
          <Spin size="small" />
          <span style={{ marginLeft: 8, color: '#8aa4bc', fontSize: 12 }}>
            AI is thinking...
          </span>
        </div>
      )}

      <div ref={messagesEndRef} />
    </Space>
  );
};

export default ChatInterface;
