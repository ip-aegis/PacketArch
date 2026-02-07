/**
 * AgentDetailsDrawer - Detailed view of a traffic agent
 *
 * Shows:
 * - Connection status and system stats
 * - Agent information
 * - Network interfaces
 * - Active deployments
 * - Diagnostics (ping test, logs)
 * - Update progress modal
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
  message,
  Row,
  Space,
  Statistic,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  CloudUploadOutlined,
  DesktopOutlined,
  FileTextOutlined,
  ReloadOutlined,
  WifiOutlined,
} from '@ant-design/icons';

import { useAgentsStore } from '../../stores/agentsStore';
import { agentsApi } from '../../api/agents';
import type { AgentUpdateStatus } from '../../types/agent';

import AgentConnectionCard from '../agents/AgentConnectionCard';
import AgentInterfacesList from '../agents/AgentInterfacesList';
import AgentDeploymentsCard from '../agents/AgentDeploymentsCard';
import AgentUpdateCard from '../agents/AgentUpdateCard';

const { Text } = Typography;

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
  const [updateStatus, setUpdateStatus] =
    useState<AgentUpdateStatus | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Diagnostics state
  const [logs, setLogs] = useState<string[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsExpanded, setLogsExpanded] = useState(false);
  const [pingResult, setPingResult] = useState<{
    round_trip_ms: number;
    server_to_agent_ms: number;
    agent_to_server_ms: number;
  } | null>(null);
  const [pingLoading, setPingLoading] = useState(false);

  const agent = agents.find((a) => a.id === agentId) || null;

  // ── Update polling ──────────────────────────────────────────────
  const pollUpdateStatus = useCallback(async () => {
    if (!agentId) return;
    try {
      const status = await agentsApi.getUpdateStatus(agentId);
      setUpdateStatus(status);

      if (
        ['complete', 'failed', 'timeout', 'idle', 'error'].includes(
          status.status,
        )
      ) {
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
        if (status.status === 'complete') {
          loadAgentDetails();
        }
      }
    } catch (err) {
      console.error('Failed to poll update status:', err);
    }
  }, [agentId]);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  useEffect(() => {
    if (
      updateModalOpen &&
      updateStatus &&
      !['complete', 'failed', 'timeout', 'idle', 'error'].includes(
        updateStatus.status,
      )
    ) {
      pollIntervalRef.current = setInterval(pollUpdateStatus, 2000);
    }
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [updateModalOpen, pollUpdateStatus]);

  // ── Fetch details on open ───────────────────────────────────────
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
      const a = agents.find((x) => x.id === agentId);
      if (a?.status === 'online') {
        await fetchInterfaces(agentId);
      }
    } catch {
      // Errors handled by store
    } finally {
      setRefreshing(false);
    }
  };

  // ── Deployment actions ──────────────────────────────────────────
  const handleStopDeployment = async (scenarioId: string) => {
    if (!agentId) return;
    try {
      await stopDeployment(agentId, scenarioId);
      message.success('Deployment stopped');
      fetchDeployments(agentId, false);
    } catch {
      message.error('Failed to stop deployment');
    }
  };

  // ── Update actions ──────────────────────────────────────────────
  const handleUpdateAgent = async () => {
    if (!agentId) return;
    setUpdating(true);
    try {
      const result = await agentsApi.triggerUpdate(agentId);
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
      pollIntervalRef.current = setInterval(pollUpdateStatus, 2000);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const errorMsg =
        axiosErr?.response?.data?.detail || 'Failed to trigger update';
      message.error(errorMsg);
    } finally {
      setUpdating(false);
    }
  };

  const handleCloseUpdateModal = async () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    if (
      agentId &&
      updateStatus &&
      ['complete', 'failed', 'timeout', 'error'].includes(
        updateStatus.status,
      )
    ) {
      try {
        await agentsApi.clearUpdateStatus(agentId);
      } catch {
        // Ignore cleanup errors
      }
    }
    setUpdateModalOpen(false);
    setUpdateStatus(null);
  };

  // ── Diagnostics ─────────────────────────────────────────────────
  const handleLoadLogs = async () => {
    if (!agentId) return;
    setLogsLoading(true);
    try {
      const result = await agentsApi.getLogs(agentId, 200);
      setLogs(result.logs);
      setLogsExpanded(true);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const errorMsg =
        axiosErr?.response?.data?.detail || 'Failed to load logs';
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
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const errorMsg =
        axiosErr?.response?.data?.detail || 'Ping test failed';
      message.error(errorMsg);
    } finally {
      setPingLoading(false);
    }
  };

  // ── Guard: agent not found ──────────────────────────────────────
  if (!agent) {
    return (
      <Drawer title="Agent Details" open={open} onClose={onClose} width={700}>
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
          <Tooltip
            title={
              isOnline
                ? 'Update agent to latest version'
                : 'Agent must be online to update'
            }
          >
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
        {/* Connection Status */}
        <AgentConnectionCard
          isLoading={isLoadingConnection}
          connectionInfo={connectionInfo}
        />

        {/* Agent Info */}
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
              {agent.hostname || (
                <Text type="secondary">Unknown</Text>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Platform">
              {agent.platform || (
                <Text type="secondary">Unknown</Text>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Version">
              {agent.version ? (
                <Space>
                  <Text code>v{agent.version}</Text>
                  {standardVersion &&
                    agent.version !== standardVersion && (
                      <Tag color="warning">
                        Update to v{standardVersion}
                      </Tag>
                    )}
                  {standardVersion &&
                    agent.version === standardVersion && (
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
              {agent.last_seen ? (
                new Date(agent.last_seen).toLocaleString()
              ) : (
                <Text type="secondary">Never</Text>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Created">
              {new Date(agent.created_at).toLocaleString()}
            </Descriptions.Item>
          </Descriptions>
        </Card>

        {/* Network Interfaces */}
        <AgentInterfacesList
          isOnline={isOnline}
          isLoading={isLoadingInterfaces}
          interfaces={interfaces}
        />

        {/* Deployments */}
        <AgentDeploymentsCard
          isLoading={isLoadingDeployments}
          deployments={deployments}
          onStopDeployment={handleStopDeployment}
        />

        {/* Diagnostics */}
        <Card
          title={
            <Space>
              <WifiOutlined />
              Diagnostics
            </Space>
          }
          size="small"
        >
          <Space
            direction="vertical"
            size="middle"
            style={{ width: '100%' }}
          >
            {/* Connection Test */}
            <Row align="middle" gutter={16}>
              <Col flex="auto">
                <Space direction="vertical" size={0}>
                  <Text strong>Connection Test</Text>
                  <Text type="secondary">
                    Measure round-trip latency to agent
                  </Text>
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
                      valueStyle={{
                        fontSize: '16px',
                        color:
                          pingResult.round_trip_ms > 200
                            ? '#ff4d4f'
                            : '#52c41a',
                      }}
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
                  <Text type="secondary">
                    View recent agent container logs
                  </Text>
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
                  <Empty
                    description="No logs available"
                    style={{ padding: '20px' }}
                  />
                )}
              </Card>
            )}

            {!isOnline && (
              <Text
                type="secondary"
                style={{ display: 'block', textAlign: 'center' }}
              >
                Agent must be online to run diagnostics
              </Text>
            )}
          </Space>
        </Card>
      </Space>

      {/* Update Progress Modal */}
      <AgentUpdateCard
        open={updateModalOpen}
        updateStatus={updateStatus}
        onClose={handleCloseUpdateModal}
      />
    </Drawer>
  );
};

export default AgentDetailsDrawer;
