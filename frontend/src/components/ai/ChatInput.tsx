/**
 * Chat Input - Text input with send button
 */

import React, { useState, KeyboardEvent } from 'react';
import { Input, Button, Space, Dropdown } from 'antd';
import type { MenuProps } from 'antd';
import { SendOutlined, BulbOutlined } from '@ant-design/icons';
import { useAIAssistantStore } from '../../stores/aiAssistantStore';

const { TextArea } = Input;

interface ChatInputProps {
  disabled?: boolean;
}

const SUGGESTED_PROMPTS = [
  'Validate my scenario topology',
  'Score the realism of this scenario',
  'Suggest flows for my devices',
  'Auto-assign IP addresses',
  'Add a PLC to the plant floor',
  'What devices should I add for manufacturing?',
];

const ChatInput: React.FC<ChatInputProps> = ({ disabled = false }) => {
  const [message, setMessage] = useState('');
  const { sendMessage, isProcessing } = useAIAssistantStore();

  const handleSend = async () => {
    if (!message.trim() || disabled || isProcessing) return;

    await sendMessage(message.trim());
    setMessage('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Ctrl+Enter or Cmd+Enter to send
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSuggestedPrompt = (prompt: string) => {
    setMessage(prompt);
  };

  const menuItems: MenuProps['items'] = SUGGESTED_PROMPTS.map((prompt, index) => ({
    key: index.toString(),
    label: prompt,
    onClick: () => handleSuggestedPrompt(prompt),
  }));

  return (
    <Space.Compact style={{ width: '100%' }} direction="vertical" size={8}>
      <TextArea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask me anything... (Ctrl+Enter to send)"
        autoSize={{ minRows: 2, maxRows: 4 }}
        disabled={disabled}
        style={{
          background: '#253545',
          borderColor: '#3a5068',
          color: '#e0e8f0',
        }}
      />
      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Dropdown menu={{ items: menuItems }} placement="topLeft">
          <Button
            icon={<BulbOutlined />}
            size="small"
            type="text"
            disabled={disabled}
            style={{ color: '#8aa4bc' }}
          >
            Suggestions
          </Button>
        </Dropdown>
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSend}
          disabled={disabled || !message.trim() || isProcessing}
          loading={isProcessing}
        >
          Send
        </Button>
      </Space>
    </Space.Compact>
  );
};

export default ChatInput;
