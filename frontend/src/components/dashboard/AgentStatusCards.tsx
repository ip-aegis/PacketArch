/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React from 'react';
import { Card, Progress, Space, Typography, Tag } from 'antd';
import { CloudServerOutlined } from '@ant-design/icons';
import type { DashboardAgent } from '../../api/dashboard';
import { formatPacketRate } from '../../utils/formatUtils';

const { Text } = Typography;

interface AgentStatusCardsProps {
  agents: DashboardAgent[];
  healthStatuses?: Record<string, 'healthy' | 'warning' | 'critical' | 'offline'>;
}

const HEALTH_TAG_CONFIG: Record<string, { color: string; label: string }> = {
  healthy: { color: 'green', label: 'Healthy' },
  warning: { color: 'orange', label: 'Warning' },
  critical: { color: 'red', label: 'Critical' },
  offline: { color: 'default', label: 'Offline' },
};

const AgentStatusCards: React.FC<AgentStatusCardsProps> = ({ agents, healthStatuses }) => {
  if (agents.length === 0) return null;

  return (
    <div style={{ display: 'flex', gap: 16, overflowX: 'auto', paddingBottom: 8 }}>
      {agents.map((agent) => (
        <Card
          key={agent.agent_id}
          size="small"
          style={{
            background: '#1a1a2e',
            border: '1px solid #2d2d52',
            minWidth: 220,
            flex: '0 0 auto',
          }}
        >
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <CloudServerOutlined style={{ color: agent.is_online ? '#52c41a' : '#ff4d4f' }} />
              <Text strong style={{ color: '#fff' }}>{agent.agent_name}</Text>
              {(() => {
                const healthStatus = healthStatuses?.[agent.agent_id];
                const cfg = healthStatus
                  ? HEALTH_TAG_CONFIG[healthStatus]
                  : agent.is_online
                    ? HEALTH_TAG_CONFIG.healthy
                    : HEALTH_TAG_CONFIG.offline;
                return (
                  <Tag
                    color={cfg.color}
                    style={{ marginLeft: 'auto', marginRight: 0 }}
                  >
                    {cfg.label}
                  </Tag>
                );
              })()}
            </div>

            {agent.hostname && (
              <Text type="secondary" style={{ fontSize: 12 }}>{agent.hostname}</Text>
            )}

            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>CPU</Text>
              <Progress
                percent={Math.round(agent.cpu_percent)}
                size="small"
                strokeColor={agent.cpu_percent > 80 ? '#ff4d4f' : '#1890ff'}
                trailColor="#2d2d52"
              />
            </div>

            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>Memory</Text>
              <Progress
                percent={Math.round(agent.memory_percent)}
                size="small"
                strokeColor={agent.memory_percent > 80 ? '#ff4d4f' : '#722ed1'}
                trailColor="#2d2d52"
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {agent.active_deployments} deployment{agent.active_deployments !== 1 ? 's' : ''}
              </Text>
              <Text style={{ fontSize: 12, color: '#1890ff' }}>
                {formatPacketRate(agent.total_packets_per_second)} pkt/s
              </Text>
            </div>
          </Space>
        </Card>
      ))}
    </div>
  );
};

export default AgentStatusCards;
