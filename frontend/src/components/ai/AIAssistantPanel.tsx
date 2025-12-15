/**
 * AI Assistant Panel - Docked side panel (always visible when open)
 */

import React from 'react';
import { Button, Space, Typography, Badge, Divider } from 'antd';
import {
  CloseOutlined,
  RobotOutlined,
  CheckCircleOutlined,
  DisconnectOutlined,
} from '@ant-design/icons';
import { useAIAssistantStore } from '../../stores/aiAssistantStore';
import ChatInterface from './ChatInterface';
import ChatInput from './ChatInput';

const { Title, Text } = Typography;

const AIAssistantPanel: React.FC = () => {
  const {
    isConnected,
    isProcessing,
    pendingActions,
    closePanel,
  } = useAIAssistantStore();

  return (
    <div
      style={{
        width: 400,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: '#1e2d3d',
        borderLeft: '1px solid #2a3f54',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 16px',
          backgroundColor: '#1a2734',
          borderBottom: '1px solid #2a3f54',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Space>
          <RobotOutlined style={{ fontSize: 20, color: '#5a9fd4' }} />
          <Title level={5} style={{ margin: 0, color: '#e0e8f0' }}>
            AI Assistant
          </Title>
          {isConnected ? (
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
          ) : (
            <DisconnectOutlined style={{ color: '#ff4d4f' }} />
          )}
        </Space>
        <Button
          type="text"
          size="small"
          icon={<CloseOutlined style={{ color: '#8aa4bc' }} />}
          onClick={closePanel}
        />
      </div>

      {/* Status bar */}
      <div style={{ padding: '8px 16px', backgroundColor: '#1a2734' }}>
        <Space size={12}>
          <Text style={{ fontSize: 12, color: '#8aa4bc' }}>
            {isConnected ? (
              <span style={{ color: '#52c41a' }}>Connected</span>
            ) : (
              <span style={{ color: '#ff4d4f' }}>Disconnected</span>
            )}
          </Text>
          {pendingActions.length > 0 && (
            <Badge count={pendingActions.length} size="small">
              <Text style={{ fontSize: 12, color: '#8aa4bc' }}>
                Pending
              </Text>
            </Badge>
          )}
        </Space>
      </div>

      <Divider style={{ margin: 0, borderColor: '#2a3f54' }} />

      {/* Chat messages - scrollable area */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
          backgroundColor: '#1e2d3d',
        }}
      >
        <ChatInterface />
      </div>

      <Divider style={{ margin: 0, borderColor: '#2a3f54' }} />

      {/* Input area - fixed at bottom */}
      <div style={{ padding: '12px 16px', backgroundColor: '#1a2734' }}>
        <ChatInput disabled={!isConnected || isProcessing} />
      </div>
    </div>
  );
};

export default AIAssistantPanel;
