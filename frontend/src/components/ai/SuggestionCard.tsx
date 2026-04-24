/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Suggestion Card - Display AI suggestion with accept/reject buttons
 */

import React from 'react';
import { Card, Typography, Space, Button, Tag } from 'antd';
import { CheckOutlined, CloseOutlined, BulbOutlined } from '@ant-design/icons';
import { useAIAssistantStore, type PendingAction } from '../../stores/aiAssistantStore';

const { Text, Paragraph } = Typography;

interface SuggestionCardProps {
  action: PendingAction;
}

const SuggestionCard: React.FC<SuggestionCardProps> = ({ action }) => {
  const { acceptAction, rejectAction } = useAIAssistantStore();

  const handleAccept = async () => {
    await acceptAction(action.id);
  };

  const handleReject = async () => {
    await rejectAction(action.id);
  };

  return (
    <Card
      size="small"
      style={{
        backgroundColor: '#2a3a28',
        borderColor: '#4a6a48',
      }}
      styles={{
        body: {
          padding: '12px',
        },
      }}
    >
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {/* Header */}
        <Space size={8}>
          <BulbOutlined style={{ color: '#7acc6a' }} />
          <Text strong style={{ fontSize: 12, color: '#e0e8f0' }}>
            Suggested Action
          </Text>
          <Tag color="success" style={{ fontSize: 11 }}>
            {action.action}
          </Tag>
        </Space>

        {/* Description */}
        <Paragraph style={{ margin: 0, color: '#c5d8ee' }}>{action.description}</Paragraph>

        {/* Preview of changes (if available) */}
        {Object.keys(action.params).length > 0 && (
          <div>
            <Text style={{ fontSize: 11, color: '#6a8caf' }}>
              Changes:
            </Text>
            <pre
              style={{
                fontSize: 11,
                backgroundColor: '#1a2734',
                color: '#b8c9dc',
                padding: '4px 8px',
                borderRadius: 4,
                marginTop: 4,
                border: '1px solid #3a5068',
                overflow: 'auto',
              }}
            >
              {JSON.stringify(action.params, null, 2)}
            </pre>
          </div>
        )}

        {/* Action buttons */}
        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
          <Button
            size="small"
            icon={<CloseOutlined />}
            onClick={handleReject}
          >
            Reject
          </Button>
          <Button
            type="primary"
            size="small"
            icon={<CheckOutlined />}
            onClick={handleAccept}
          >
            Accept
          </Button>
        </Space>
      </Space>
    </Card>
  );
};

export default SuggestionCard;
