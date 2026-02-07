/**
 * AgentDeploymentsCard - Table of deployments for an agent.
 */

import React from 'react';
import {
  Badge,
  Button,
  Card,
  Empty,
  Skeleton,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  CloseCircleOutlined,
  DisconnectOutlined,
  LoadingOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  StopOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { AgentDeployment } from '../../types/agent';

const { Text } = Typography;

export interface AgentDeploymentsCardProps {
  isLoading: boolean;
  deployments: AgentDeployment[];
  onStopDeployment: (scenarioId: string) => void;
}

const getDeploymentStateTag = (state: string) => {
  const configs: Record<string, { color: string; icon: React.ReactNode }> = {
    starting: { color: 'blue', icon: <LoadingOutlined /> },
    running: { color: 'green', icon: <PlayCircleOutlined /> },
    stopping: { color: 'orange', icon: <PauseCircleOutlined /> },
    stopped: { color: 'default', icon: <StopOutlined /> },
    error: { color: 'red', icon: <CloseCircleOutlined /> },
    disconnected: { color: 'default', icon: <DisconnectOutlined /> },
  };
  const config = configs[state] || { color: 'default', icon: null };
  return (
    <Tag color={config.color} icon={config.icon}>
      {state.charAt(0).toUpperCase() + state.slice(1)}
    </Tag>
  );
};

const AgentDeploymentsCard: React.FC<AgentDeploymentsCardProps> = React.memo(({
  isLoading,
  deployments,
  onStopDeployment,
}) => {
  const columns: ColumnsType<AgentDeployment> = [
    {
      title: 'Scenario',
      dataIndex: 'scenario_id',
      key: 'scenario_id',
      render: (id: string) => <Text code>{id.slice(0, 8)}...</Text>,
    },
    {
      title: 'State',
      dataIndex: 'state',
      key: 'state',
      render: (state: string) => getDeploymentStateTag(state),
    },
    {
      title: 'Packets',
      dataIndex: 'packets_sent',
      key: 'packets_sent',
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: 'Interface',
      dataIndex: 'interface',
      key: 'interface',
      render: (iface: string | null) => (
        <Text code>{iface || 'default'}</Text>
      ),
    },
    {
      title: 'Started',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) =>
        ['starting', 'running'].includes(record.state) ? (
          <Button
            size="small"
            danger
            icon={<StopOutlined />}
            onClick={() => onStopDeployment(record.scenario_id)}
          >
            Stop
          </Button>
        ) : null,
    },
  ];

  return (
    <Card
      title={
        <Space>
          <ThunderboltOutlined />
          Deployments
          <Badge
            count={
              deployments.filter((d) =>
                ['starting', 'running'].includes(d.state),
              ).length
            }
            style={{ backgroundColor: '#52c41a' }}
          />
        </Space>
      }
      size="small"
    >
      {isLoading ? (
        <Skeleton active paragraph={{ rows: 3 }} />
      ) : deployments.length > 0 ? (
        <Table
          columns={columns}
          dataSource={deployments}
          rowKey="id"
          size="small"
          pagination={false}
        />
      ) : (
        <Empty description="No deployments" />
      )}
    </Card>
  );
});

AgentDeploymentsCard.displayName = 'AgentDeploymentsCard';

export default AgentDeploymentsCard;
