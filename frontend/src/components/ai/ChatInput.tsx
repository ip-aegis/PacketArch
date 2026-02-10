/**
 * Chat Input - Text input with send button
 */

import React, { useState, useMemo, KeyboardEvent } from 'react';
import { Input, Button, Space, Dropdown } from 'antd';
import type { MenuProps } from 'antd';
import { SendOutlined, BulbOutlined } from '@ant-design/icons';
import { useAIAssistantStore } from '../../stores/aiAssistantStore';
import { useScenarioStore } from '../../stores/scenarioStore';

const { TextArea } = Input;

interface ChatInputProps {
  disabled?: boolean;
}

/** Generate context-aware prompts based on current scenario state. */
function getSuggestedPrompts(
  deviceCount: number,
  flowCount: number,
  hasFingerprints: boolean,
): string[] {
  if (deviceCount === 0) {
    return [
      'Create a manufacturing scenario with 10 devices',
      'Build a water treatment SCADA network',
      'Design a building automation system',
      'Add 5 Siemens PLCs and 3 HMIs',
    ];
  }
  if (flowCount === 0) {
    return [
      'Connect these devices with appropriate protocol flows',
      'Suggest flows for my devices',
      'Create Modbus polling flows between PLCs and HMIs',
      'Validate my scenario topology',
    ];
  }
  if (!hasFingerprints) {
    return [
      'Assign vendor fingerprints to all devices',
      'Set Siemens identities on the PLCs',
      'Validate my scenario topology',
      'Score the realism of this scenario',
    ];
  }
  return [
    'Validate my scenario topology',
    'Score the realism of this scenario',
    'Add a vulnerable device for security testing',
    'Optimize timing intervals for realism',
  ];
}

const ChatInput: React.FC<ChatInputProps> = ({ disabled = false }) => {
  const [message, setMessage] = useState('');
  const { sendMessage, isProcessing } = useAIAssistantStore();

  const deviceCount = useScenarioStore((s) => Object.keys(s.devices).length);
  const flowCount = useScenarioStore((s) => Object.keys(s.flows).length);
  const hasFingerprints = useScenarioStore((s) =>
    Object.values(s.devices).some((d) => d.templateId || d.fingerprintModel),
  );

  const suggestedPrompts = useMemo(
    () => getSuggestedPrompts(deviceCount, flowCount, hasFingerprints),
    [deviceCount, flowCount, hasFingerprints],
  );

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

  const menuItems: MenuProps['items'] = suggestedPrompts.map((prompt, index) => ({
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
