import React from 'react';
import { List, Typography, Tag, Button, Space, Tooltip } from 'antd';
import {
  InfoCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import type { DashboardHealthData } from '../../api/dashboard';

const { Text } = Typography;

interface HealthEventsFeedProps {
  health: DashboardHealthData;
  onAcknowledge: (eventId: string) => void;
}

const SEVERITY_CONFIG = {
  info: { icon: <InfoCircleOutlined />, color: '#1890ff', tagColor: 'blue' },
  warning: { icon: <WarningOutlined />, color: '#fa8c16', tagColor: 'orange' },
  critical: { icon: <CloseCircleOutlined />, color: '#ff4d4f', tagColor: 'red' },
} as const;

function timeAgo(timestamp: string): string {
  const seconds = Math.round((Date.now() - new Date(timestamp).getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  return `${hours}h ago`;
}

const HealthEventsFeed: React.FC<HealthEventsFeedProps> = ({ health, onAcknowledge }) => {
  const events = health.recent_events.filter((e) => !e.acknowledged);

  if (events.length === 0) {
    return (
      <div
        style={{
          padding: '12px 16px',
          background: '#1a1a2e',
          border: '1px solid #2d2d52',
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
        <Text style={{ color: '#52c41a', fontSize: 13 }}>All systems healthy</Text>
      </div>
    );
  }

  return (
    <div
      style={{
        background: '#1a1a2e',
        border: '1px solid #2d2d52',
        borderRadius: 8,
        maxHeight: 250,
        overflowY: 'auto',
      }}
    >
      <List
        size="small"
        dataSource={events}
        renderItem={(event) => {
          const config = SEVERITY_CONFIG[event.severity] || SEVERITY_CONFIG.info;
          return (
            <List.Item
              style={{
                padding: '8px 16px',
                borderBottom: '1px solid #2d2d52',
              }}
              actions={[
                <Tooltip title="Dismiss" key="dismiss">
                  <Button
                    type="text"
                    size="small"
                    style={{ color: '#6b6b8a', fontSize: 11 }}
                    onClick={() => onAcknowledge(event.id)}
                  >
                    Dismiss
                  </Button>
                </Tooltip>,
              ]}
            >
              <Space size={8} style={{ flex: 1, minWidth: 0 }}>
                <span style={{ color: config.color, fontSize: 14 }}>{config.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Text
                    style={{ color: '#e0e0e0', fontSize: 12, display: 'block' }}
                    ellipsis
                  >
                    {event.message}
                  </Text>
                  <Space size={4}>
                    <Tag
                      color={config.tagColor}
                      style={{ fontSize: 10, lineHeight: '16px', margin: 0 }}
                    >
                      {event.agent_name}
                    </Tag>
                    <Text type="secondary" style={{ fontSize: 10 }}>
                      {timeAgo(event.timestamp)}
                    </Text>
                  </Space>
                </div>
              </Space>
            </List.Item>
          );
        }}
      />
    </div>
  );
};

export default HealthEventsFeed;
