/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Dashboard page component
 */

import React, { useEffect } from 'react';
import { Typography, Card, Row, Col, Statistic, Space, Button, Tag, List, Spin } from 'antd';
import {
  AppstoreOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  PlusOutlined,
  SyncOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useDeploymentsStore } from '../stores/deploymentsStore';
import { getOverviewStats } from '../api/stats';
import type { UnifiedDeployment } from '../types/docker';

const { Title, Paragraph, Text } = Typography;

// Helper functions
const formatElapsedTime = (startedAt: string | null): string => {
  if (!startedAt) return '0s';
  const elapsed = Date.now() - new Date(startedAt).getTime();
  const hours = Math.floor(elapsed / 3600000);
  const minutes = Math.floor((elapsed % 3600000) / 60000);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
};

const calculateProgress = (deployment: UnifiedDeployment): number => {
  if (!deployment.started_at || !deployment.duration_ms) return 0;
  const elapsed = Date.now() - new Date(deployment.started_at).getTime();
  return Math.min(100, Math.round((elapsed / deployment.duration_ms) * 100));
};

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { deployments, fetchDeployments } = useDeploymentsStore();

  // Fetch overview stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats', 'overview'],
    queryFn: getOverviewStats,
  });

  useEffect(() => {
    fetchDeployments();
  }, [fetchDeployments]);

  const runningDeployments = deployments.filter((d) =>
    ['running', 'starting'].includes(d.status)
  );

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <img
            src="/dashboard_logo.png"
            alt="Industrial Packet Generator"
            style={{ width: 80, height: 80, objectFit: 'contain' }}
          />
          <div>
            <Title level={2} style={{ marginBottom: 4 }}>Industrial Packet Generator</Title>
            <Paragraph type="secondary" style={{ marginBottom: 0 }}>
              OT Traffic Simulation Platform - Generate hyper-realistic industrial network
              traffic for testing and training.
            </Paragraph>
          </div>
        </div>

        <Spin spinning={statsLoading}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Scenarios"
                  value={stats?.scenarios ?? 0}
                  prefix={<AppstoreOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Device Profiles"
                  value={stats?.devices ?? 0}
                  prefix={<ThunderboltOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Protocols Used"
                  value={stats?.protocols ?? 0}
                  prefix={<FileTextOutlined />}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Generated PCAPs"
                  value={stats?.pcaps ?? 0}
                  prefix={<FileTextOutlined />}
                  valueStyle={{ color: '#fa8c16' }}
                />
              </Card>
            </Col>
          </Row>
        </Spin>

        <Card title="Quick Actions">
          <Space wrap>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/studio')}
            >
              Create New Scenario
            </Button>
            <Button icon={<AppstoreOutlined />} onClick={() => navigate('/studio')}>
              Open Scenario Studio
            </Button>
          </Space>
        </Card>

        {runningDeployments.length > 0 && (
          <Card
            title={
              <Space>
                <SyncOutlined spin style={{ color: '#52c41a' }} />
                <span>Active Deployments ({runningDeployments.length})</span>
              </Space>
            }
          >
            <List
              dataSource={runningDeployments}
              renderItem={(deployment) => {
                const isPerpetual = (deployment.run_mode ?? 'timed') === 'perpetual';
                return (
                  <List.Item
                    actions={[
                      <Button
                        key="view"
                        size="small"
                        onClick={() => navigate(`/studio?scenario=${deployment.scenario_id}`)}
                      >
                        View
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      avatar={
                        <PlayCircleOutlined style={{ fontSize: 24, color: '#52c41a' }} />
                      }
                      title={
                        <Space>
                          <Text strong>{deployment.scenario_name || 'Unnamed Scenario'}</Text>
                          {isPerpetual && <Tag color="purple">Perpetual</Tag>}
                          <Tag color="green">Running</Tag>
                        </Space>
                      }
                      description={
                        <Space direction="vertical" size={0}>
                          <Text type="secondary">Agent: {deployment.agent_name || 'Unknown'}</Text>
                          <Text type="secondary">
                            {isPerpetual
                              ? `Running for ${formatElapsedTime(deployment.started_at)}`
                              : `Progress: ${calculateProgress(deployment)}%`}
                          </Text>
                        </Space>
                      }
                    />
                  </List.Item>
                );
              }}
            />
          </Card>
        )}

        <Card title="Getting Started">
          <Paragraph>
            PacketArch allows you to create realistic OT network traffic scenarios for:
          </Paragraph>
          <ul>
            <li>Security testing and validation</li>
            <li>Network monitoring tool evaluation</li>
            <li>Training data generation for ML/AI models</li>
            <li>Protocol analysis and research</li>
          </ul>
          <Paragraph>
            <strong>Supported Protocols:</strong> Modbus TCP, EtherNet/IP, PROFINET, OPC
            UA, DNP3, and more.
          </Paragraph>
          <Paragraph>
            <strong>Industry Verticals:</strong> Manufacturing, Water/Wastewater,
            Energy/Power, Oil & Gas.
          </Paragraph>
        </Card>
      </Space>
    </div>
  );
};

export default DashboardPage;
