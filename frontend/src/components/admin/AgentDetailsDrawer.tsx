/**
 * AgentDetailsDrawer - Detailed view of a traffic agent
 *
 * Shows:
 * - Connection status and system stats
 * - Network interfaces
 * - Active deployments
 * - Deployment history
 */

import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Empty,
  List,
  message,
  Modal,
  Progress,
  Result,
  Row,
  Skeleton,
  Space,
  Statistic,
  Steps,
  Table,
  Tag,
  Timeline,
  Tooltip,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  ApiOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  CloudServerOutlined,
  CloudUploadOutlined,
  DesktopOutlined,
  DisconnectOutlined,
  DownloadOutlined,
  FileTextOutlined,
  GlobalOutlined,
  HddOutlined,
  LoadingOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  SyncOutlined,
  StopOutlined,
  ThunderboltOutlined,
  WifiOutlined,
} from '@ant-design/icons';

import { useAgentsStore } from '../../stores/agentsStore';
import { agentsApi } from '../../api/agents';
import type { AgentDeployment, AgentInterface, AgentUpdateStatus } from '../../types/agent';

const { Text, Title } = Typography;

interface AgentDetailsDrawerProps {
  agentId: string | null;
  open: boolean;
  onClose: () => void;
}

const AgentDetailsDrawer: React.FC<AgentDetailsDrawerProps> = ({
  agentId,
  open,
  onClose,
}) => {
  const {
    agents,
    connectionInfo,
    interfaces,
    deployments,
    standardVersion,
    isLoadingConnection,
    isLoadingInterfaces,
    isLoadingDeployments,
    fetchAgent,
    fetchConnection,
    fetchInterfaces,
    fetchDeployments,
    stopDeployment,
    clearConnectionInfo,
  } = useAgentsStore();

  const [refreshing, setRefreshing] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [updateModalOpen, setUpdateModalOpen] = useState(false);
  const [updateStatus, setUpdateStatus] = useState<AgentUpdateStatus | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Diagnostics state
  const [logs, setLogs] = useState<string[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsExpanded, setLogsExpanded] = useState(false);
  const [pingResult, setPingResult] = useState<{ round_trip_ms: number; server_to_agent_ms: number; agent_to_server_ms: number } | null>(null);
  const [pingLoading, setPingLoading] = useState(false);

  const agent = agents.find((a) => a.id === agentId) || null;

  // Poll for update status
  const pollUpdateStatus = useCallback(async () => {
    if (!agentId) return;
    try {
      const status = await agentsApi.getUpdateStatus(agentId);
      setUpdateStatus(status);

      // Stop polling if update is complete or failed
      if (['complete', 'failed', 'timeout', 'idle', 'error'].includes(status.status)) {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
        // Refresh agent details if update completed
        if (status.status === 'complete') {
          loadAgentDetails();
        }
      }
    } catch (err) {
      console.error('Failed to poll update status:', err);
    }
  }, [agentId]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Start polling when modal opens with active update
  useEffect(() => {
    if (updateModalOpen && updateStatus && !['complete', 'failed', 'timeout', 'idle', 'error'].includes(updateStatus.status)) {
      pollIntervalRef.current = setInterval(pollUpdateStatus, 2000);
    }
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [updateModalOpen, pollUpdateStatus]);

  // Fetch details when drawer opens
  useEffect(() => {
    if (open && agentId) {
      loadAgentDetails();
    } else {
      clearConnectionInfo();
    }
  }, [open, agentId]);

  const loadAgentDetails = async () => {
    if (!agentId) return;

    setRefreshing(true);
    try {
      await Promise.all([
        fetchAgent(agentId),
        fetchConnection(agentId),
        fetchDeployments(agentId, false),
      ]);

      // Only fetch interfaces if agent is online
      const agent = agents.find((a) => a.id === agentId);
      if (agent?.status === 'online') {
        await fetchInterfaces(agentId);
      }
    } catch (err) {
      // Errors handled by store
    } finally {
      setRefreshing(false);
    }
  };

  const handleStopDeployment = async (scenarioId: string) => {
    if (!agentId) return;
    try {
      await stopDeployment(agentId, scenarioId);
      message.success('Deployment stopped');
      fetchDeployments(agentId, false);
    } catch (err) {
      message.error('Failed to stop deployment');
    }
  };

  const handleUpdateAgent = async () => {
    if (!agentId) return;
    setUpdating(true);
    try {
      const result = await agentsApi.triggerUpdate(agentId);
      // Set initial status and open modal
      setUpdateStatus({
        agent_id: agentId,
        status: 'initiated',
        progress: null,
        message: result.message,
        target_version: result.target_version || null,
        initiated_at: new Date().toISOString(),
        completed_at: null,
        error: null,
      });
      setUpdateModalOpen(true);
      // Start polling for updates
      pollIntervalRef.current = setInterval(pollUpdateStatus, 2000);
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || 'Failed to trigger update';
      message.error(errorMsg);
    } finally {
      setUpdating(false);
    }
  };

  const handleCloseUpdateModal = async () => {
    // Stop polling
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    // Clear status on server if complete/failed
    if (agentId && updateStatus && ['complete', 'failed', 'timeout', 'error'].includes(updateStatus.status)) {
      try {
        await agentsApi.clearUpdateStatus(agentId);
      } catch (err) {
        // Ignore cleanup errors
      }
    }
    setUpdateModalOpen(false);
    setUpdateStatus(null);
  };

  const handleLoadLogs = async () => {
    if (!agentId) return;
    setLogsLoading(true);
    try {
      const result = await agentsApi.getLogs(agentId, 200);
      setLogs(result.logs);
      setLogsExpanded(true);
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || 'Failed to load logs';
      message.error(errorMsg);
    } finally {
      setLogsLoading(false);
    }
  };

  const handlePingTest = async () => {
    if (!agentId) return;
    setPingLoading(true);
    setPingResult(null);
    try {
      const result = await agentsApi.pingTest(agentId);
      setPingResult({
        round_trip_ms: result.round_trip_ms,
        server_to_agent_ms: result.server_to_agent_ms,
        agent_to_server_ms: result.agent_to_server_ms,
      });
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || 'Ping test failed';
      message.error(errorMsg);
    } finally {
      setPingLoading(false);
    }
  };

  // Map update status to step index
  const getUpdateStepIndex = (status: string): number => {
    switch (status) {
      case 'initiated':
        return 0;
      case 'downloading':
        return 1;
      case 'loading':
        return 2;
      case 'restarting':
        return 3;
      case 'complete':
        return 4;
      case 'failed':
      case 'timeout':
        return -1; // Error state
      default:
        return 0;
    }
  };

  const getUpdateStepStatus = (stepIndex: number, currentIndex: number, hasError: boolean): 'wait' | 'process' | 'finish' | 'error' => {
    if (hasError) return currentIndex === stepIndex ? 'error' : 'wait';
    if (stepIndex < currentIndex) return 'finish';
    if (stepIndex === currentIndex) return 'process';
    return 'wait';
  };

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

  const deploymentColumns: ColumnsType<AgentDeployment> = [
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
      render: (iface: string | null) => <Text code>{iface || 'default'}</Text>,
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
            onClick={() => handleStopDeployment(record.scenario_id)}
          >
            Stop
          </Button>
        ) : null,
    },
  ];

  if (!agent) {
    return (
      <Drawer
        title="Agent Details"
        open={open}
        onClose={onClose}
        width={700}
      >
        <Empty description="Agent not found" />
      </Drawer>
    );
  }

  const isOnline = agent.status === 'online';

  return (
    <Drawer
      title={
        <Space>
          <Badge status={isOnline ? 'success' : 'default'} />
          <span>{agent.name}</span>
          {!agent.is_active && <Tag color="orange">Disabled</Tag>}
        </Space>
      }
      open={open}
      onClose={onClose}
      width={700}
      extra={
        <Space>
          <Tooltip title={isOnline ? 'Update agent to latest version' : 'Agent must be online to update'}>
            <Button
              icon={<CloudUploadOutlined />}
              onClick={handleUpdateAgent}
              loading={updating}
              disabled={!isOnline}
            >
              Update
            </Button>
          </Tooltip>
          <Tooltip title="Refresh">
            <Button
              icon={<ReloadOutlined spin={refreshing} />}
              onClick={loadAgentDetails}
              loading={refreshing}
            />
          </Tooltip>
        </Space>
      }
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Connection Status Card */}
        <Card
          title={
            <Space>
              <CloudServerOutlined />
              Connection Status
            </Space>
          }
          size="small"
        >
          {isLoadingConnection ? (
            <Skeleton active paragraph={{ rows: 2 }} />
          ) : connectionInfo ? (
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="CPU Usage"
                  value={connectionInfo.cpu_percent}
                  suffix="%"
                  valueStyle={{
                    color: connectionInfo.cpu_percent > 80 ? '#ff4d4f' : undefined,
                  }}
                  prefix={
                    <Progress
                      type="circle"
                      percent={connectionInfo.cpu_percent}
                      size={40}
                      strokeColor={connectionInfo.cpu_percent > 80 ? '#ff4d4f' : '#1890ff'}
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
                    color: connectionInfo.memory_percent > 80 ? '#ff4d4f' : undefined,
                  }}
                  prefix={
                    <Progress
                      type="circle"
                      percent={connectionInfo.memory_percent}
                      size={40}
                      strokeColor={connectionInfo.memory_percent > 80 ? '#ff4d4f' : '#52c41a'}
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
                    {new Date(connectionInfo.last_heartbeat).toLocaleString()}
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
              image={<DisconnectOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
              description="Agent is offline"
            />
          )}
        </Card>

        {/* Agent Info Card */}
        <Card
          title={
            <Space>
              <DesktopOutlined />
              Agent Information
            </Space>
          }
          size="small"
        >
          <Descriptions size="small" column={2}>
            <Descriptions.Item label="ID">
              <Text copyable code>
                {agent.id}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="Hostname">
              {agent.hostname || <Text type="secondary">Unknown</Text>}
            </Descriptions.Item>
            <Descriptions.Item label="Platform">
              {agent.platform || <Text type="secondary">Unknown</Text>}
            </Descriptions.Item>
            <Descriptions.Item label="Version">
              {agent.version ? (
                <Space>
                  <Text code>v{agent.version}</Text>
                  {standardVersion && agent.version !== standardVersion && (
                    <Tag color="warning">Update to v{standardVersion}</Tag>
                  )}
                  {standardVersion && agent.version === standardVersion && (
                    <Tag color="success">Latest</Tag>
                  )}
                </Space>
              ) : (
                <Text type="secondary">Unknown</Text>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Default Interface">
              <Text code>{agent.default_interface || 'eth0'}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Last Seen">
              {agent.last_seen
                ? new Date(agent.last_seen).toLocaleString()
                : <Text type="secondary">Never</Text>}
            </Descriptions.Item>
            <Descriptions.Item label="Created">
              {new Date(agent.created_at).toLocaleString()}
            </Descriptions.Item>
          </Descriptions>
        </Card>

        {/* Network Interfaces Card */}
        <Card
          title={
            <Space>
              <GlobalOutlined />
              Network Interfaces
            </Space>
          }
          size="small"
        >
          {isLoadingInterfaces ? (
            <Skeleton active paragraph={{ rows: 3 }} />
          ) : interfaces.length > 0 ? (
            <List
              size="small"
              dataSource={interfaces}
              renderItem={(iface: AgentInterface) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={<ApiOutlined />}
                    title={
                      <Space>
                        <Text code>{iface.name}</Text>
                        {iface.mac && <Text type="secondary">({iface.mac})</Text>}
                      </Space>
                    }
                    description={
                      iface.error ? (
                        <Text type="danger">{iface.error}</Text>
                      ) : (
                        <Space direction="vertical" size={0}>
                          {iface.addresses.map((addr, idx) => (
                            <Text key={idx} type="secondary">
                              {addr.type.toUpperCase()}: {addr.address}
                              {addr.netmask && ` / ${addr.netmask}`}
                            </Text>
                          ))}
                          {iface.addresses.length === 0 && (
                            <Text type="secondary">No addresses</Text>
                          )}
                        </Space>
                      )
                    }
                  />
                </List.Item>
              )}
            />
          ) : isOnline ? (
            <Empty description="No interfaces available" />
          ) : (
            <Empty
              image={<DisconnectOutlined style={{ fontSize: 32, color: '#d9d9d9' }} />}
              description="Connect the agent to view interfaces"
            />
          )}
        </Card>

        {/* Deployments Card */}
        <Card
          title={
            <Space>
              <ThunderboltOutlined />
              Deployments
              <Badge
                count={deployments.filter((d) => ['starting', 'running'].includes(d.state)).length}
                style={{ backgroundColor: '#52c41a' }}
              />
            </Space>
          }
          size="small"
        >
          {isLoadingDeployments ? (
            <Skeleton active paragraph={{ rows: 3 }} />
          ) : deployments.length > 0 ? (
            <Table
              columns={deploymentColumns}
              dataSource={deployments}
              rowKey="id"
              size="small"
              pagination={false}
            />
          ) : (
            <Empty description="No deployments" />
          )}
        </Card>

        {/* Diagnostics Card */}
        <Card
          title={
            <Space>
              <WifiOutlined />
              Diagnostics
            </Space>
          }
          size="small"
        >
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {/* Connection Test */}
            <Row align="middle" gutter={16}>
              <Col flex="auto">
                <Space direction="vertical" size={0}>
                  <Text strong>Connection Test</Text>
                  <Text type="secondary">Measure round-trip latency to agent</Text>
                </Space>
              </Col>
              <Col>
                <Button
                  icon={<WifiOutlined />}
                  onClick={handlePingTest}
                  loading={pingLoading}
                  disabled={!isOnline}
                >
                  Test
                </Button>
              </Col>
            </Row>

            {pingResult && (
              <Card size="small" style={{ backgroundColor: '#f6ffed' }}>
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic
                      title="Round Trip"
                      value={pingResult.round_trip_ms}
                      suffix="ms"
                      valueStyle={{ fontSize: '16px', color: pingResult.round_trip_ms > 200 ? '#ff4d4f' : '#52c41a' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Server → Agent"
                      value={pingResult.server_to_agent_ms}
                      suffix="ms"
                      valueStyle={{ fontSize: '16px' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="Agent → Server"
                      value={pingResult.agent_to_server_ms}
                      suffix="ms"
                      valueStyle={{ fontSize: '16px' }}
                    />
                  </Col>
                </Row>
              </Card>
            )}

            {/* Agent Logs */}
            <Row align="middle" gutter={16}>
              <Col flex="auto">
                <Space direction="vertical" size={0}>
                  <Text strong>Agent Logs</Text>
                  <Text type="secondary">View recent agent container logs</Text>
                </Space>
              </Col>
              <Col>
                <Button
                  icon={<FileTextOutlined />}
                  onClick={handleLoadLogs}
                  loading={logsLoading}
                  disabled={!isOnline}
                >
                  {logsExpanded ? 'Refresh' : 'Load Logs'}
                </Button>
              </Col>
            </Row>

            {logsExpanded && (
              <Card
                size="small"
                style={{ maxHeight: 400, overflow: 'auto' }}
                bodyStyle={{ padding: 0 }}
              >
                {logs.length > 0 ? (
                  <pre
                    style={{
                      margin: 0,
                      padding: '12px',
                      fontSize: '11px',
                      fontFamily: 'Monaco, Consolas, monospace',
                      backgroundColor: '#1a1a1a',
                      color: '#d4d4d4',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-all',
                      lineHeight: '1.4',
                    }}
                  >
                    {logs.join('\n')}
                  </pre>
                ) : (
                  <Empty description="No logs available" style={{ padding: '20px' }} />
                )}
              </Card>
            )}

            {!isOnline && (
              <Text type="secondary" style={{ display: 'block', textAlign: 'center' }}>
                Agent must be online to run diagnostics
              </Text>
            )}
          </Space>
        </Card>
      </Space>

      {/* Update Progress Modal */}
      <Modal
        title={
          <Space>
            <CloudUploadOutlined />
            Agent Update
          </Space>
        }
        open={updateModalOpen}
        onCancel={handleCloseUpdateModal}
        footer={
          updateStatus && ['complete', 'failed', 'timeout', 'error'].includes(updateStatus.status) ? (
            <Button type="primary" onClick={handleCloseUpdateModal}>
              Close
            </Button>
          ) : (
            <Text type="secondary">Please wait while the agent updates...</Text>
          )
        }
        closable={updateStatus ? ['complete', 'failed', 'timeout', 'error'].includes(updateStatus.status) : true}
        maskClosable={false}
        width={500}
      >
        {updateStatus && (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {/* Status display for terminal states */}
            {updateStatus.status === 'complete' && (
              <Result
                status="success"
                title="Update Complete"
                subTitle={updateStatus.message}
                extra={
                  updateStatus.target_version && (
                    <Tag color="success">v{updateStatus.target_version}</Tag>
                  )
                }
              />
            )}

            {['failed', 'timeout', 'error'].includes(updateStatus.status) && (
              <Result
                status="error"
                title="Update Failed"
                subTitle={updateStatus.error || updateStatus.message}
              />
            )}

            {/* Progress steps for in-progress states */}
            {!['complete', 'failed', 'timeout', 'error'].includes(updateStatus.status) && (
              <>
                <Steps
                  direction="vertical"
                  size="small"
                  current={getUpdateStepIndex(updateStatus.status)}
                  items={[
                    {
                      title: 'Initiating Update',
                      description: 'Sending update command to agent',
                      icon: updateStatus.status === 'initiated' ? <LoadingOutlined /> : undefined,
                      status: getUpdateStepStatus(0, getUpdateStepIndex(updateStatus.status), false),
                    },
                    {
                      title: 'Downloading Image',
                      description: updateStatus.progress !== null
                        ? `${updateStatus.progress}% complete`
                        : 'Downloading latest agent image',
                      icon: updateStatus.status === 'downloading' ? <DownloadOutlined /> : undefined,
                      status: getUpdateStepStatus(1, getUpdateStepIndex(updateStatus.status), false),
                    },
                    {
                      title: 'Loading Image',
                      description: 'Loading new Docker image',
                      icon: updateStatus.status === 'loading' ? <LoadingOutlined /> : undefined,
                      status: getUpdateStepStatus(2, getUpdateStepIndex(updateStatus.status), false),
                    },
                    {
                      title: 'Restarting Agent',
                      description: 'Agent is restarting with new version',
                      icon: updateStatus.status === 'restarting' ? <SyncOutlined spin /> : undefined,
                      status: getUpdateStepStatus(3, getUpdateStepIndex(updateStatus.status), false),
                    },
                  ]}
                />

                {/* Download progress bar */}
                {updateStatus.status === 'downloading' && updateStatus.progress !== null && (
                  <Progress
                    percent={updateStatus.progress}
                    status="active"
                    strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
                  />
                )}

                {/* Current status message */}
                <Card size="small">
                  <Text type="secondary">{updateStatus.message}</Text>
                </Card>

                {/* Target version */}
                {updateStatus.target_version && (
                  <Text type="secondary">
                    Target version: <Text code>v{updateStatus.target_version}</Text>
                  </Text>
                )}
              </>
            )}
          </Space>
        )}
      </Modal>
    </Drawer>
  );
};

export default AgentDetailsDrawer;
