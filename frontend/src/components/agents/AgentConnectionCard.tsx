/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * AgentConnectionCard - Displays connection status and system stats
 * for a traffic agent (CPU, memory, connected at, heartbeat).
 */

import React from 'react';
import {
  Badge,
  Card,
  Col,
  Descriptions,
  Empty,
  Progress,
  Row,
  Skeleton,
  Space,
  Statistic,
} from 'antd';
import {
  CloudServerOutlined,
  DisconnectOutlined,
} from '@ant-design/icons';
import type { AgentConnectionInfo } from '../../types/agent';

export interface AgentConnectionCardProps {
  isLoading: boolean;
  connectionInfo: AgentConnectionInfo | null;
}

const AgentConnectionCard: React.FC<AgentConnectionCardProps> = React.memo(({
  isLoading,
  connectionInfo,
}) => {
  return (
    <Card
      title={
        <Space>
          <CloudServerOutlined />
          Connection Status
        </Space>
      }
      size="small"
    >
      {isLoading ? (
        <Skeleton active paragraph={{ rows: 2 }} />
      ) : connectionInfo ? (
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Statistic
              title="CPU Usage"
              value={connectionInfo.cpu_percent}
              suffix="%"
              valueStyle={{
                color:
                  connectionInfo.cpu_percent > 80 ? '#ff4d4f' : undefined,
              }}
              prefix={
                <Progress
                  type="circle"
                  percent={connectionInfo.cpu_percent}
                  size={40}
                  strokeColor={
                    connectionInfo.cpu_percent > 80
                      ? '#ff4d4f'
                      : '#1890ff'
                  }
                />
              }
            />
          </Col>
          <Col span={12}>
            <Statistic
              title="Memory Usage"
              value={connectionInfo.memory_percent}
              suffix="%"
              valueStyle={{
                color:
                  connectionInfo.memory_percent > 80
                    ? '#ff4d4f'
                    : undefined,
              }}
              prefix={
                <Progress
                  type="circle"
                  percent={connectionInfo.memory_percent}
                  size={40}
                  strokeColor={
                    connectionInfo.memory_percent > 80
                      ? '#ff4d4f'
                      : '#52c41a'
                  }
                />
              }
            />
          </Col>
          <Col span={24}>
            <Descriptions size="small" column={2}>
              <Descriptions.Item label="Connected">
                {new Date(connectionInfo.connected_at).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="Last Heartbeat">
                {new Date(
                  connectionInfo.last_heartbeat,
                ).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label="Running Scenarios">
                <Badge
                  count={connectionInfo.running_scenarios.length}
                  showZero
                  style={{ backgroundColor: '#52c41a' }}
                />
              </Descriptions.Item>
            </Descriptions>
          </Col>
        </Row>
      ) : (
        <Empty
          image={
            <DisconnectOutlined
              style={{ fontSize: 48, color: '#d9d9d9' }}
            />
          }
          description="Agent is offline"
        />
      )}
    </Card>
  );
});

AgentConnectionCard.displayName = 'AgentConnectionCard';

export default AgentConnectionCard;
