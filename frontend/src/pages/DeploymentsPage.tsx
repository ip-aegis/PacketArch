/**
 * Deployments Page - View all deployment history
 */

import React, { useEffect, useState } from 'react';
import {
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Card,
  Select,
  Tooltip,
  message,
} from 'antd';
import {
  CloudServerOutlined,
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  LinkOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import { useDeploymentsStore } from '../stores/deploymentsStore';
import { useAgentsStore } from '../stores/agentsStore';
import type { UnifiedDeployment, DeploymentStatus } from '../types/docker';

const { Title, Text } = Typography;

const statusConfig: Record<
  string,
  { color: string; icon: React.ReactNode; label: string }
> = {
  pending: {
    color: 'default',
    icon: <ClockCircleOutlined />,
    label: 'Pending',
  },
  starting: {
    color: 'processing',
    icon: <LoadingOutlined spin />,
    label: 'Starting',
  },
  running: {
    color: 'success',
    icon: <CheckCircleOutlined />,
    label: 'Running',
  },
  stopping: {
    color: 'warning',
    icon: <LoadingOutlined spin />,
    label: 'Stopping',
  },
  stopped: {
    color: 'default',
    icon: <StopOutlined />,
    label: 'Stopped',
  },
  failed: {
    color: 'error',
    icon: <CloseCircleOutlined />,
    label: 'Failed',
  },
  error: {
    color: 'error',
    icon: <CloseCircleOutlined />,
    label: 'Error',
  },
  disconnected: {
    color: 'warning',
    icon: <CloseCircleOutlined />,
    label: 'Disconnected',
  },
};

const DeploymentsPage: React.FC = () => {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState<DeploymentStatus | undefined>();

  const {
    deployments,
    isLoading,
    fetchDeployments,
    removeDeployment,
  } = useDeploymentsStore();

  const { agents, fetchAgents } = useAgentsStore();

  // Fetch all deployments and agents on mount
  useEffect(() => {
    fetchDeployments();
    fetchAgents();
  }, [fetchDeployments, fetchAgents]);

  // Refetch with filters
  useEffect(() => {
    fetchDeployments({ status: statusFilter });
  }, [statusFilter, fetchDeployments]);

  // Poll for updates when there are active deployments
  useEffect(() => {
    const hasActiveDeployments = deployments.some(
      (d) => ['running', 'starting', 'stopping', 'disconnected'].includes(d.status)
    );

    if (!hasActiveDeployments) return;

    const pollInterval = setInterval(() => {
      fetchDeployments({ status: statusFilter });
    }, 3000);

    return () => clearInterval(pollInterval);
  }, [deployments, statusFilter, fetchDeployments]);

  const handleStop = async (deployment: UnifiedDeployment) => {
    try {
      if (deployment.agent_id) {
        const { stopDeployment: stopAgentDeployment } = useAgentsStore.getState();
        await stopAgentDeployment(deployment.agent_id, deployment.scenario_id);
        message.success('Stop command sent to agent');
        await fetchDeployments({ status: statusFilter });
      }
    } catch {
      message.error('Failed to stop deployment');
    }
  };

  const handleRemove = async (id: string) => {
    try {
      await removeDeployment(id);
      message.success('Deployment removed');
    } catch {
      message.error('Failed to remove deployment');
    }
  };

  const handleRestart = async (deployment: UnifiedDeployment) => {
    if (!deployment.agent_id) {
      message.error('No agent associated with this deployment');
      return;
    }

    try {
      const { deployScenario } = useAgentsStore.getState();
      await deployScenario(deployment.agent_id, {
        scenario_id: deployment.scenario_id,
        interface: deployment.network_interface || 'eth0',
      });
      message.success('Scenario restarted on agent');
      await removeDeployment(deployment.id);
      await fetchDeployments({ status: statusFilter });
    } catch {
      message.error('Failed to restart deployment');
    }
  };

  const formatTimestamp = (ts: string | null): string => {
    if (!ts) return '-';
    return new Date(ts).toLocaleString();
  };

  const formatElapsedTime = (startedAt: string | null, stoppedAt: string | null): string => {
    if (!startedAt) return '-';
    const start = new Date(startedAt).getTime();
    const end = stoppedAt ? new Date(stoppedAt).getTime() : Date.now();
    const elapsed = end - start;
    const hours = Math.floor(elapsed / 3600000);
    const minutes = Math.floor((elapsed % 3600000) / 60000);
    const seconds = Math.floor((elapsed % 60000) / 1000);

    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m ${seconds}s`;
    return `${seconds}s`;
  };

  const columns: ColumnsType<UnifiedDeployment> = [
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const config = statusConfig[status] || statusConfig.pending;
        return (
          <Tag color={config.color} icon={config.icon}>
            {config.label}
          </Tag>
        );
      },
    },
    {
      title: 'Scenario',
      dataIndex: 'scenario_name',
      key: 'scenario_name',
      render: (name: string, record: UnifiedDeployment) => (
        <Button
          type="link"
          size="small"
          icon={<LinkOutlined />}
          onClick={() => navigate(`/studio?scenario=${record.scenario_id}`)}
          style={{ padding: 0 }}
        >
          {name || 'Unknown'}
        </Button>
      ),
    },
    {
      title: 'Agent',
      key: 'agent',
      render: (_: unknown, record: UnifiedDeployment) => (
        <Space>
          <RocketOutlined />
          <span>{record.agent_name || 'Unknown Agent'}</span>
        </Space>
      ),
    },
    {
      title: 'Interface',
      dataIndex: 'network_interface',
      key: 'network_interface',
      render: (iface: string) => <Text code>{iface}</Text>,
    },
    {
      title: 'Runtime',
      key: 'runtime',
      width: 100,
      render: (_: unknown, record: UnifiedDeployment) => (
        <Text style={{ color: '#8aa4bc' }}>
          {formatElapsedTime(record.started_at, record.stopped_at)}
        </Text>
      ),
    },
    {
      title: 'Started',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 180,
      render: (ts: string) => (
        <Text style={{ color: '#6a8caf', fontSize: 12 }}>
          {formatTimestamp(ts)}
        </Text>
      ),
      sorter: (a, b) => {
        if (!a.started_at) return 1;
        if (!b.started_at) return -1;
        return new Date(b.started_at).getTime() - new Date(a.started_at).getTime();
      },
      defaultSortOrder: 'ascend',
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 140,
      render: (_: unknown, record: UnifiedDeployment) => {
        const canStop = ['running', 'starting', 'stopping'].includes(record.status);
        const isDisconnected = record.status === 'disconnected';

        const agent = record.agent_id
          ? agents.find(a => a.id === record.agent_id)
          : null;
        const agentOnline = agent?.status === 'online';

        return (
          <Space size="small">
            {canStop ? (
              <Tooltip title="Stop">
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<StopOutlined />}
                  onClick={() => handleStop(record)}
                />
              </Tooltip>
            ) : (
              <>
                {isDisconnected && agentOnline && (
                  <Tooltip title="Restart on agent">
                    <Button
                      type="text"
                      size="small"
                      icon={<PlayCircleOutlined />}
                      onClick={() => handleRestart(record)}
                      style={{ color: '#52c41a' }}
                    />
                  </Tooltip>
                )}
                <Tooltip title="Remove">
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    onClick={() => handleRemove(record.id)}
                  />
                </Tooltip>
              </>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <div style={{ padding: '0 0 24px 0' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ color: '#fff', marginBottom: 8 }}>
          <CloudServerOutlined style={{ marginRight: 12 }} />
          Deployments
        </Title>
        <Text style={{ color: '#8aa4bc' }}>
          View deployment history and status
        </Text>
      </div>

      <Card
        style={{ background: '#1a2734', border: '1px solid #2a3f54' }}
        styles={{ body: { padding: '16px 24px' } }}
      >
        {/* Filters */}
        <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <Select
            placeholder="Filter by status"
            allowClear
            style={{ width: 160 }}
            value={statusFilter}
            onChange={setStatusFilter}
            options={[
              { value: 'running', label: 'Running' },
              { value: 'disconnected', label: 'Disconnected' },
              { value: 'stopped', label: 'Stopped' },
              { value: 'failed', label: 'Failed' },
              { value: 'pending', label: 'Pending' },
            ]}
          />
          <Button
            icon={<ReloadOutlined />}
            onClick={() => fetchDeployments({ status: statusFilter })}
          >
            Refresh
          </Button>
          <div style={{ flex: 1 }} />
          <Text style={{ color: '#6a8caf', fontSize: 12 }}>
            {deployments.length} deployment{deployments.length !== 1 ? 's' : ''}
          </Text>
        </div>

        <Table
          columns={columns}
          dataSource={deployments}
          rowKey="id"
          loading={isLoading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `${total} deployments`,
          }}
          size="middle"
          style={{
            background: 'transparent',
          }}
          expandable={{
            expandedRowRender: (record) => (
              <div style={{ padding: '8px 0' }}>
                {record.error_message && (
                  <div style={{ marginBottom: 8 }}>
                    <Text type="danger">
                      <strong>Error:</strong> {record.error_message}
                    </Text>
                  </div>
                )}
                <Space size="large">
                  <Text style={{ color: '#6a8caf', fontSize: 12 }}>
                    <strong>Packets:</strong> {record.packets_injected.toLocaleString()}
                  </Text>
                  <Text style={{ color: '#6a8caf', fontSize: 12 }}>
                    <strong>Created:</strong> {formatTimestamp(record.created_at)}
                  </Text>
                  {record.stopped_at && (
                    <Text style={{ color: '#6a8caf', fontSize: 12 }}>
                      <strong>Stopped:</strong> {formatTimestamp(record.stopped_at)}
                    </Text>
                  )}
                </Space>
              </div>
            ),
            rowExpandable: (record) => !!record.error_message,
          }}
        />
      </Card>
    </div>
  );
};

export default DeploymentsPage;
