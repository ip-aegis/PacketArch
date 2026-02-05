/**
 * Deployments Page - View all deployment history and logs
 */

import React, { useEffect, useState } from 'react';
import {
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Card,
  Modal,
  Spin,
  Select,
  Tooltip,
  message,
} from 'antd';
import {
  CloudServerOutlined,
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  LinkOutlined,
  DownloadOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import { useDeploymentsStore } from '../stores/deploymentsStore';
import { useDockerHostsStore } from '../stores/dockerHostsStore';
import { useAgentsStore } from '../stores/agentsStore';
import { deploymentsApi } from '../api/deployments';
import type { UnifiedDeployment, DeploymentStatus, DeploymentType } from '../types/docker';

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
  const [logsModalVisible, setLogsModalVisible] = useState(false);
  const [selectedDeployment, setSelectedDeployment] = useState<UnifiedDeployment | null>(null);
  const [statusFilter, setStatusFilter] = useState<DeploymentStatus | undefined>();
  const [hostFilter, setHostFilter] = useState<string | undefined>();
  const [typeFilter, setTypeFilter] = useState<DeploymentType | undefined>();
  const [pcapModalVisible, setPcapModalVisible] = useState(false);
  const [pcapFiles, setPcapFiles] = useState<string[]>([]);
  const [pcapLoading, setPcapLoading] = useState(false);

  const {
    deployments,
    logs,
    isLoading,
    fetchDeployments,
    stopDeployment,
    removeDeployment,
    fetchLogs,
  } = useDeploymentsStore();

  const { hosts, fetchHosts } = useDockerHostsStore();
  const { agents, fetchAgents } = useAgentsStore();

  // Fetch all deployments, hosts, and agents on mount
  useEffect(() => {
    fetchDeployments();
    fetchHosts();
    fetchAgents();
  }, [fetchDeployments, fetchHosts, fetchAgents]);

  // Refetch with filters
  useEffect(() => {
    fetchDeployments({
      status: statusFilter,
      docker_host_id: hostFilter,
      deployment_type: typeFilter,
    });
  }, [statusFilter, hostFilter, typeFilter, fetchDeployments]);

  // Poll for updates when there are active deployments (running, starting, stopping, disconnected)
  useEffect(() => {
    const hasActiveDeployments = deployments.some(
      (d) => ['running', 'starting', 'stopping', 'disconnected'].includes(d.status)
    );

    if (!hasActiveDeployments) return;

    const pollInterval = setInterval(() => {
      fetchDeployments({
        status: statusFilter,
        docker_host_id: hostFilter,
        deployment_type: typeFilter,
      });
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(pollInterval);
  }, [deployments, statusFilter, hostFilter, typeFilter, fetchDeployments]);

  const handleViewLogs = async (deployment: UnifiedDeployment) => {
    setSelectedDeployment(deployment);
    setLogsModalVisible(true);
    try {
      await fetchLogs(deployment.id, 500);
    } catch {
      message.error('Failed to fetch logs');
    }
  };

  const handleRefreshLogs = async () => {
    if (selectedDeployment) {
      try {
        await fetchLogs(selectedDeployment.id, 500);
      } catch {
        message.error('Failed to refresh logs');
      }
    }
  };

  const handleStop = async (deployment: UnifiedDeployment) => {
    try {
      if (deployment.deployment_type === 'agent' && deployment.agent_id) {
        // Agent deployment - use agents API
        const { stopDeployment: stopAgentDeployment } = useAgentsStore.getState();
        await stopAgentDeployment(deployment.agent_id, deployment.scenario_id);
        message.success('Stop command sent to agent');
        // Refresh deployments list
        await fetchDeployments({ status: statusFilter, docker_host_id: hostFilter, deployment_type: typeFilter });
      } else {
        // Docker deployment - use deployments API
        await stopDeployment(deployment.id);
        message.success('Deployment stopped');
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
    if (deployment.deployment_type !== 'agent' || !deployment.agent_id) {
      message.error('Restart only available for agent deployments');
      return;
    }

    try {
      const { deployScenario } = useAgentsStore.getState();
      await deployScenario(
        deployment.agent_id,
        deployment.scenario_id,
        deployment.network_interface || 'eth0'
      );
      message.success('Scenario restarted on agent');
      // Remove the old disconnected deployment
      await removeDeployment(deployment.id);
      // Refresh deployments list
      await fetchDeployments({ status: statusFilter, docker_host_id: hostFilter, deployment_type: typeFilter });
    } catch {
      message.error('Failed to restart deployment');
    }
  };

  const handleViewPcap = async (deployment: UnifiedDeployment) => {
    // PCAP download only available for Docker deployments
    if (deployment.deployment_type !== 'docker') {
      message.info('PCAP download not available for agent deployments');
      return;
    }
    setSelectedDeployment(deployment);
    setPcapModalVisible(true);
    setPcapLoading(true);
    try {
      const result = await deploymentsApi.listPcapFiles(deployment.id);
      setPcapFiles(result.files);
      if (result.files.length === 0) {
        message.info('No PCAP files available yet');
      }
    } catch {
      message.error('Failed to fetch PCAP files');
      setPcapFiles([]);
    } finally {
      setPcapLoading(false);
    }
  };

  const handleDownloadPcap = async (filename: string) => {
    if (!selectedDeployment) return;
    try {
      // Get auth token for download
      const token = localStorage.getItem('access_token');
      const url = `/api/v1/deployments/${selectedDeployment.id}/pcap/${encodeURIComponent(filename)}`;

      // Create a temporary link to download
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Download failed');
      }

      const blob = await response.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(downloadUrl);

      message.success(`Downloaded ${filename}`);
    } catch {
      message.error('Failed to download PCAP file');
    }
  };

  const formatDuration = (ms: number | null): string => {
    if (!ms) return '-';
    const minutes = Math.floor(ms / 60000);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
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
      title: 'Type',
      dataIndex: 'deployment_type',
      key: 'deployment_type',
      width: 100,
      render: (type: string) => (
        type === 'agent' ? (
          <Tag color="blue" icon={<RocketOutlined />}>Agent</Tag>
        ) : (
          <Tag color="default" icon={<CloudServerOutlined />}>Docker</Tag>
        )
      ),
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
      title: 'Target',
      key: 'target',
      render: (_: unknown, record: UnifiedDeployment) => (
        <Space>
          {record.deployment_type === 'agent' ? (
            <>
              <RocketOutlined />
              <span>{record.agent_name || 'Unknown Agent'}</span>
            </>
          ) : (
            <>
              <CloudServerOutlined />
              <span>{record.docker_host_name || 'Unknown Host'}</span>
            </>
          )}
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
      title: 'Mode',
      key: 'run_mode',
      width: 100,
      render: (_: unknown, record: UnifiedDeployment) => (
        record.run_mode === 'perpetual' ? (
          <Tag color="purple">Perpetual</Tag>
        ) : (
          <Tag>{formatDuration(record.duration_ms)}</Tag>
        )
      ),
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
      width: 180,
      render: (_: unknown, record: UnifiedDeployment) => {
        // Only truly running states can be stopped
        const canStop = ['running', 'starting', 'stopping'].includes(record.status);
        // Disconnected deployments are stale - allow delete and optionally restart
        const isDisconnected = record.status === 'disconnected';
        const isDocker = record.deployment_type === 'docker';

        // Check if agent is online for restart option
        const agent = record.deployment_type === 'agent' && record.agent_id
          ? agents.find(a => a.id === record.agent_id)
          : null;
        const agentOnline = agent?.status === 'online';

        return (
          <Space size="small">
            <Tooltip title={isDocker ? 'View Logs' : 'Logs not available for agent deployments'}>
              <Button
                type="text"
                size="small"
                icon={<FileTextOutlined />}
                onClick={() => handleViewLogs(record)}
                disabled={!isDocker || !record.container_id}
              />
            </Tooltip>
            <Tooltip title={isDocker ? 'Download PCAP' : 'PCAP not available for agent deployments'}>
              <Button
                type="text"
                size="small"
                icon={<DownloadOutlined />}
                onClick={() => handleViewPcap(record)}
                disabled={!isDocker || !record.container_id}
              />
            </Tooltip>
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
          View deployment history, status, and container logs
        </Text>
      </div>

      <Card
        style={{ background: '#1a2734', border: '1px solid #2a3f54' }}
        styles={{ body: { padding: '16px 24px' } }}
      >
        {/* Filters */}
        <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <Select
            placeholder="Filter by type"
            allowClear
            style={{ width: 140 }}
            value={typeFilter}
            onChange={setTypeFilter}
            options={[
              { value: 'docker', label: 'Docker' },
              { value: 'agent', label: 'Agent' },
            ]}
          />
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
          <Select
            placeholder="Filter by host"
            allowClear
            style={{ width: 200 }}
            value={hostFilter}
            onChange={setHostFilter}
            disabled={typeFilter === 'agent'}
            options={hosts.map((h) => ({ value: h.id, label: h.name }))}
          />
          <Button
            icon={<ReloadOutlined />}
            onClick={() => fetchDeployments({ status: statusFilter, docker_host_id: hostFilter, deployment_type: typeFilter })}
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
                  {record.deployment_type === 'docker' && (
                    <Text style={{ color: '#6a8caf', fontSize: 12 }}>
                      <strong>Container:</strong> {record.container_name || record.container_id || 'N/A'}
                    </Text>
                  )}
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
            rowExpandable: (record) => !!record.error_message || record.deployment_type === 'docker',
          }}
        />
      </Card>

      {/* Logs Modal */}
      <Modal
        title={
          <Space>
            <FileTextOutlined />
            Container Logs
            {selectedDeployment && (
              <Tag color={statusConfig[selectedDeployment.status]?.color}>
                {selectedDeployment.scenario_name}
              </Tag>
            )}
          </Space>
        }
        open={logsModalVisible}
        onCancel={() => setLogsModalVisible(false)}
        footer={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={handleRefreshLogs}>
              Refresh
            </Button>
            <Button onClick={() => setLogsModalVisible(false)}>Close</Button>
          </Space>
        }
        width={800}
      >
        {logs ? (
          <pre
            style={{
              background: '#0d1117',
              padding: 16,
              borderRadius: 6,
              maxHeight: 500,
              overflow: 'auto',
              fontSize: 12,
              fontFamily: 'Consolas, Monaco, "Courier New", monospace',
              color: '#c9d1d9',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
              margin: 0,
            }}
          >
            {logs.logs || 'No logs available'}
          </pre>
        ) : (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
          </div>
        )}
      </Modal>

      {/* PCAP Download Modal */}
      <Modal
        title={
          <Space>
            <DownloadOutlined />
            Download PCAP Files
            {selectedDeployment && (
              <Tag color={statusConfig[selectedDeployment.status]?.color}>
                {selectedDeployment.scenario_name}
              </Tag>
            )}
          </Space>
        }
        open={pcapModalVisible}
        onCancel={() => setPcapModalVisible(false)}
        footer={
          <Button onClick={() => setPcapModalVisible(false)}>Close</Button>
        }
        width={500}
      >
        {pcapLoading ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
          </div>
        ) : pcapFiles.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 48, color: '#8aa4bc' }}>
            No PCAP files available. Traffic generation may still be in progress.
          </div>
        ) : (
          <div>
            <Text style={{ color: '#8aa4bc', display: 'block', marginBottom: 16 }}>
              {pcapFiles.length} PCAP file{pcapFiles.length !== 1 ? 's' : ''} available
            </Text>
            {pcapFiles.map((file) => (
              <div
                key={file}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 12px',
                  background: '#1a2734',
                  borderRadius: 6,
                  marginBottom: 8,
                }}
              >
                <Text code style={{ flex: 1 }}>
                  {file}
                </Text>
                <Button
                  type="primary"
                  size="small"
                  icon={<DownloadOutlined />}
                  onClick={() => handleDownloadPcap(file)}
                >
                  Download
                </Button>
              </div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default DeploymentsPage;
