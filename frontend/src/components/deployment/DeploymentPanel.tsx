/**
 * Deployment Panel - Deploy scenarios to remote Docker hosts or traffic agents
 */

import React, { useEffect, useState } from 'react';
import {
  Form,
  Select,
  InputNumber,
  Button,
  Space,
  Typography,
  Alert,
  Divider,
  Tag,
  Progress,
  Card,
  Tooltip,
  Spin,
  Empty,
  Modal,
  Radio,
  message,
} from 'antd';
import {
  CloudServerOutlined,
  PlayCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  DeleteOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
  RocketOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { useDockerHostsStore } from '../../stores/dockerHostsStore';
import { useDeploymentsStore } from '../../stores/deploymentsStore';
import { useAgentsStore } from '../../stores/agentsStore';
import { scenariosApi, type ScenarioValidationResponse } from '../../api/scenarios';
import type { UnifiedDeployment, DeploymentRequest, NetworkInterface, RunMode } from '../../types/docker';
import type { AgentInterface } from '../../types/agent';
import { formatElapsedTime } from '../../utils/dateUtils';

const { Text, Title } = Typography;

interface DeploymentPanelProps {
  scenarioId: string | null;
}

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
};

type TargetType = 'docker' | 'agent';

const DeploymentPanel: React.FC<DeploymentPanelProps> = ({ scenarioId }) => {
  const [form] = Form.useForm();
  const [targetType, setTargetType] = useState<TargetType>('agent');
  const [interfaces, setInterfaces] = useState<NetworkInterface[]>([]);
  const [agentInterfaces, setAgentInterfaces] = useState<AgentInterface[]>([]);
  const [loadingInterfaces, setLoadingInterfaces] = useState(false);
  const [logsModalVisible, setLogsModalVisible] = useState(false);
  const [validationModalVisible, setValidationModalVisible] = useState(false);
  const [validationResult, setValidationResult] = useState<ScenarioValidationResponse | null>(null);
  const [validating, setValidating] = useState(false);
  const [repairing, setRepairing] = useState(false);
  const [pendingDeployData, setPendingDeployData] = useState<DeploymentRequest | null>(null);

  const {
    hosts,
    fetchHosts,
    fetchInterfaces,
    isLoading: hostsLoading,
  } = useDockerHostsStore();

  const {
    agents,
    fetchAgents,
    fetchInterfaces: fetchAgentInterfaces,
    deployScenario: deployToAgent,
    isLoading: agentsLoading,
  } = useAgentsStore();

  const {
    deployments,
    activeDeployment,
    logs,
    isLoading: deploymentsLoading,
    error,
    fetchDeployments,
    startDeployment,
    stopDeployment,
    removeDeployment,
    fetchLogs,
    setActiveDeployment,
    clearError,
    stopPolling,
  } = useDeploymentsStore();

  // Filter deployments for current scenario
  const scenarioDeployments = deployments.filter(
    (d) => d.scenario_id === scenarioId
  );

  // Fetch hosts, agents, and deployments on mount
  useEffect(() => {
    fetchHosts();
    fetchAgents();
    if (scenarioId) {
      fetchDeployments({ scenario_id: scenarioId });
    }
    return () => {
      stopPolling();
    };
  }, [fetchHosts, fetchAgents, fetchDeployments, scenarioId, stopPolling]);

  // Poll for deployment status updates when there are active deployments
  useEffect(() => {
    const hasActiveDeployments = scenarioDeployments.some(
      (d) => ['running', 'starting', 'stopping'].includes(d.status)
    );

    if (!hasActiveDeployments || !scenarioId) return;

    const pollInterval = setInterval(() => {
      fetchDeployments({ scenario_id: scenarioId });
    }, 5000); // Poll every 5 seconds

    return () => clearInterval(pollInterval);
  }, [scenarioDeployments, scenarioId, fetchDeployments]);

  // Handle target type change
  const handleTargetTypeChange = (type: TargetType) => {
    setTargetType(type);
    setInterfaces([]);
    setAgentInterfaces([]);
    form.setFieldValue('docker_host_id', undefined);
    form.setFieldValue('agent_id', undefined);
    form.setFieldValue('network_interface', undefined);
  };

  // Handle host selection - load interfaces
  const handleHostChange = async (hostId: string) => {
    setLoadingInterfaces(true);
    setInterfaces([]);
    form.setFieldValue('network_interface', undefined);

    try {
      const result = await fetchInterfaces(hostId);
      setInterfaces(result.interfaces);
      // Set default if host has a default interface
      const host = hosts.find((h) => h.id === hostId);
      if (host?.default_interface) {
        const hasDefault = result.interfaces.some(
          (i) => i.name === host.default_interface
        );
        if (hasDefault) {
          form.setFieldValue('network_interface', host.default_interface);
        }
      }
    } catch (err) {
      // Error already handled in store
    } finally {
      setLoadingInterfaces(false);
    }
  };

  // Handle agent selection - load interfaces
  const handleAgentChange = async (agentId: string) => {
    setLoadingInterfaces(true);
    setAgentInterfaces([]);
    form.setFieldValue('network_interface', undefined);

    try {
      const result = await fetchAgentInterfaces(agentId);
      setAgentInterfaces(result);
      // Set default if agent has a default interface
      const agent = agents.find((a) => a.id === agentId);
      if (agent?.default_interface) {
        const hasDefault = result.some(
          (i) => i.name === agent.default_interface
        );
        if (hasDefault) {
          form.setFieldValue('network_interface', agent.default_interface);
        }
      }
    } catch (err) {
      // Error already handled in store - agent might be offline
    } finally {
      setLoadingInterfaces(false);
    }
  };

  // Validate scenario before deployment
  const validateScenario = async (): Promise<ScenarioValidationResponse | null> => {
    if (!scenarioId) return null;

    setValidating(true);
    try {
      const result = await scenariosApi.validate(scenarioId);
      return result;
    } catch (err) {
      console.error('Validation failed:', err);
      return null;
    } finally {
      setValidating(false);
    }
  };

  // Execute deployment (called after validation passes or user confirms)
  const executeDeployment = async (data: DeploymentRequest) => {
    try {
      await startDeployment(data);
      form.resetFields();
      setInterfaces([]);
      setPendingDeployData(null);
    } catch {
      // Error handled in store
    }
  };

  // Handle deploy - validate first
  const handleDeploy = async (values: {
    docker_host_id?: string;
    agent_id?: string;
    network_interface: string;
    run_mode: RunMode;
    duration_minutes?: number;
  }) => {
    if (!scenarioId) return;

    // Validate scenario first
    const validation = await validateScenario();

    if (targetType === 'agent') {
      // Deploy to traffic agent
      if (!values.agent_id) return;

      const agentDeployData = {
        scenario_id: scenarioId,
        agent_id: values.agent_id,
        interface: values.network_interface,
      };

      if (!validation || validation.warnings.length === 0) {
        // No issues, deploy directly
        try {
          await deployToAgent(values.agent_id, {
            scenario_id: scenarioId,
            interface: values.network_interface,
          });
          message.success('Scenario deployed to agent successfully! Traffic generation started.');
          form.resetFields(['agent_id', 'network_interface']);
          setAgentInterfaces([]);
          // Refresh deployments list to show the new agent deployment
          await fetchDeployments({ scenario_id: scenarioId });
        } catch (err: any) {
          message.error(err?.message || 'Failed to deploy scenario to agent');
        }
      } else {
        // Show validation modal - store pending data for agent deploy
        setPendingDeployData({ ...agentDeployData, docker_host_id: '', run_mode: 'perpetual' } as any);
        setValidationResult(validation);
        setValidationModalVisible(true);
      }
    } else {
      // Deploy to Docker host (legacy)
      if (!values.docker_host_id) return;

      const data: DeploymentRequest = {
        scenario_id: scenarioId,
        docker_host_id: values.docker_host_id,
        network_interface: values.network_interface,
        run_mode: values.run_mode,
        duration_ms: values.run_mode === 'perpetual' ? undefined : (values.duration_minutes ?? 5) * 60 * 1000,
      };

      if (!validation) {
        // Validation request failed, proceed anyway
        await executeDeployment(data);
        return;
      }

      // Check if there are any issues
      if (validation.warnings.length > 0) {
        // Store pending deploy data and show validation modal
        setPendingDeployData(data);
        setValidationResult(validation);
        setValidationModalVisible(true);
      } else {
        // No issues, deploy directly
        await executeDeployment(data);
      }
    }
  };

  // Handle proceed with deployment after seeing warnings
  const handleProceedWithDeployment = async () => {
    setValidationModalVisible(false);
    if (pendingDeployData) {
      await executeDeployment(pendingDeployData);
    }
  };

  // Handle repair protocols - fixes protocol_identity_mismatch errors
  const handleRepairProtocols = async () => {
    if (!scenarioId) return;

    setRepairing(true);
    try {
      const result = await scenariosApi.repairProtocols(scenarioId);
      message.success(result.message);

      // Re-validate after repair
      setValidating(true);
      const validation = await scenariosApi.validate(scenarioId);
      setValidationResult(validation);

      // If no more warnings, close modal
      if (validation.warnings.length === 0) {
        setValidationModalVisible(false);
        message.success('All issues fixed! You can now deploy.');
      }
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || error?.message || 'Failed to repair protocols';
      message.error(errorMsg);
    } finally {
      setRepairing(false);
      setValidating(false);
    }
  };

  // Check if there are protocol_identity_mismatch warnings
  const hasProtocolMismatchWarnings = validationResult?.warnings.some(
    (w) => w.code === 'protocol_identity_mismatch'
  );

  // Handle stop - routes to correct API based on deployment type
  const handleStop = async (deployment: UnifiedDeployment) => {
    try {
      if (deployment.deployment_type === 'agent' && deployment.agent_id) {
        // Agent deployment - use agents API
        const { stopDeployment: stopAgentDeployment } = useAgentsStore.getState();
        await stopAgentDeployment(deployment.agent_id, deployment.scenario_id);
        message.success('Stop command sent to agent');
        // Refresh deployments list
        await fetchDeployments({ scenario_id: scenarioId! });
      } else {
        // Docker deployment - use deployments API
        await stopDeployment(deployment.id);
        message.success('Deployment stopped');
      }
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || error?.message || 'Failed to stop deployment';
      message.error(errorMsg);
    }
  };

  // Handle remove
  const handleRemove = async (deploymentId: string) => {
    try {
      await removeDeployment(deploymentId);
    } catch {
      // Error handled in store
    }
  };

  // Handle view logs
  const handleViewLogs = async (deployment: UnifiedDeployment) => {
    setActiveDeployment(deployment);
    setLogsModalVisible(true);
    try {
      await fetchLogs(deployment.id);
    } catch {
      // Error handled in store
    }
  };

  // Refresh logs
  const handleRefreshLogs = async () => {
    if (activeDeployment) {
      try {
        await fetchLogs(activeDeployment.id);
      } catch {
        // Error handled in store
      }
    }
  };

  if (!scenarioId) {
    return (
      <div style={{ padding: '16px' }}>
        <Empty
          image={<CloudServerOutlined style={{ fontSize: 48, color: '#4a6a8a' }} />}
          description={
            <Text style={{ color: '#8aa4bc' }}>
              Save the scenario first to enable deployment
            </Text>
          }
        />
      </div>
    );
  }

  const activeHosts = hosts.filter((h) => h.is_active);
  const onlineAgents = agents.filter((a) => a.status === 'online' && a.is_active);
  const hasTargets = onlineAgents.length > 0 || activeHosts.length > 0;

  return (
    <div
      style={{
        padding: '16px',
        height: '100%',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}
    >
      {error && (
        <Alert
          message={error}
          type="error"
          showIcon
          closable
          onClose={clearError}
        />
      )}

      {/* New Deployment Form */}
      <Card
        size="small"
        title={
          <Space>
            <PlayCircleOutlined />
            <span>New Deployment</span>
          </Space>
        }
        style={{ background: '#1a2734' }}
        styles={{ body: { padding: '12px' } }}
      >
        {!hasTargets ? (
          <Alert
            message="No deployment targets available"
            description="Configure traffic agents in Settings > Traffic Agents, or Docker hosts in Settings > Docker Hosts"
            type="warning"
            showIcon
          />
        ) : (
          <Form
            form={form}
            layout="vertical"
            onFinish={handleDeploy}
            initialValues={{ duration_minutes: 5, run_mode: 'timed' }}
            size="small"
          >
            {/* Target Type Selector */}
            <Form.Item label="Deploy To" style={{ marginBottom: 12 }}>
              <Radio.Group
                value={targetType}
                onChange={(e) => handleTargetTypeChange(e.target.value)}
                size="small"
                style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
              >
                <Radio value="agent" disabled={onlineAgents.length === 0}>
                  <Space size={4}>
                    <RocketOutlined />
                    <span>Traffic Agent</span>
                    {onlineAgents.length > 0 ? (
                      <Tag color="green" style={{ fontSize: 10, marginLeft: 4 }}>
                        {onlineAgents.length} online
                      </Tag>
                    ) : (
                      <Tag color="default" style={{ fontSize: 10, marginLeft: 4 }}>
                        none online
                      </Tag>
                    )}
                  </Space>
                </Radio>
                <Radio value="docker" disabled={activeHosts.length === 0}>
                  <Space size={4}>
                    <CloudServerOutlined />
                    <span>Docker Host (Legacy)</span>
                    {activeHosts.length === 0 && (
                      <Tag color="default" style={{ fontSize: 10, marginLeft: 4 }}>
                        none configured
                      </Tag>
                    )}
                  </Space>
                </Radio>
              </Radio.Group>
            </Form.Item>

            {/* Agent Selection (when targetType === 'agent') */}
            {targetType === 'agent' && (
              <Form.Item
                name="agent_id"
                label="Traffic Agent"
                rules={[{ required: true, message: 'Select an agent' }]}
              >
                <Select
                  placeholder="Select agent"
                  loading={agentsLoading}
                  onChange={handleAgentChange}
                  options={onlineAgents.map((a) => ({
                    value: a.id,
                    label: (
                      <Space>
                        <span>{a.name}</span>
                        <Tag color="green" style={{ fontSize: 10 }}>Online</Tag>
                        {a.hostname && (
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            ({a.hostname})
                          </Text>
                        )}
                      </Space>
                    ),
                  }))}
                />
              </Form.Item>
            )}

            {/* Docker Host Selection (when targetType === 'docker') */}
            {targetType === 'docker' && (
              <Form.Item
                name="docker_host_id"
                label="Docker Host"
                rules={[{ required: true, message: 'Select a host' }]}
              >
                <Select
                  placeholder="Select host"
                  loading={hostsLoading}
                  onChange={handleHostChange}
                  options={activeHosts.map((h) => ({
                    value: h.id,
                    label: h.name,
                  }))}
                />
              </Form.Item>
            )}

            {/* Network Interface */}
            <Form.Item
              name="network_interface"
              label="Network Interface"
              rules={[{ required: true, message: 'Select an interface' }]}
            >
              <Select
                placeholder={
                  loadingInterfaces ? 'Loading interfaces...' : 'Select interface'
                }
                loading={loadingInterfaces}
                disabled={targetType === 'agent' ? agentInterfaces.length === 0 : interfaces.length === 0}
                options={
                  targetType === 'agent'
                    ? agentInterfaces.map((i) => ({
                        value: i.name,
                        label: (
                          <Space>
                            <span>{i.name}</span>
                            {i.mac && (
                              <Text type="secondary" style={{ fontSize: 10 }}>
                                {i.mac}
                              </Text>
                            )}
                          </Space>
                        ),
                      }))
                    : interfaces.map((i) => ({
                        value: i.name,
                        label: (
                          <Space>
                            <span>{i.name}</span>
                            {i.is_up ? (
                              <Tag color="green" style={{ fontSize: 10 }}>
                                UP
                              </Tag>
                            ) : (
                              <Tag color="default" style={{ fontSize: 10 }}>
                                DOWN
                              </Tag>
                            )}
                          </Space>
                        ),
                      }))
                }
              />
            </Form.Item>

            {/* Run Mode - only for Docker hosts */}
            {targetType === 'docker' && (
              <>
                <Form.Item
                  name="run_mode"
                  label="Run Mode"
                >
                  <Select
                    options={[
                      { value: 'timed', label: 'Timed (stops after duration)' },
                      { value: 'perpetual', label: 'Perpetual (runs until stopped)' },
                    ]}
                  />
                </Form.Item>

                <Form.Item noStyle shouldUpdate={(prev, curr) => prev.run_mode !== curr.run_mode}>
                  {({ getFieldValue }) =>
                    getFieldValue('run_mode') !== 'perpetual' && (
                      <Form.Item
                        name="duration_minutes"
                        label="Duration (minutes)"
                        rules={[{ required: true }]}
                      >
                        <InputNumber min={1} max={1440} style={{ width: '100%' }} />
                      </Form.Item>
                    )
                  }
                </Form.Item>
              </>
            )}

            <Form.Item style={{ marginBottom: 0 }}>
              <Button
                type="primary"
                htmlType="submit"
                loading={deploymentsLoading || validating}
                icon={<PlayCircleOutlined />}
                block
              >
                {validating ? 'Validating...' : 'Deploy'}
              </Button>
            </Form.Item>
          </Form>
        )}
      </Card>

      {/* Active Deployments */}
      {scenarioDeployments.length > 0 && (
        <>
          <Divider style={{ margin: '8px 0', borderColor: '#2a3f54' }} />
          <div>
            <Title
              level={5}
              style={{ color: '#8aa4bc', marginBottom: 12, fontSize: 13 }}
            >
              Deployments
            </Title>
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              {scenarioDeployments.map((deployment) => (
                <DeploymentCard
                  key={deployment.id}
                  deployment={deployment}
                  onStop={handleStop}
                  onRemove={handleRemove}
                  onViewLogs={handleViewLogs}
                />
              ))}
            </Space>
          </div>
        </>
      )}

      {/* Logs Modal */}
      <Modal
        title={
          <Space>
            <FileTextOutlined />
            Container Logs
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
        width={700}
      >
        {logs ? (
          <pre
            style={{
              background: '#0d1117',
              padding: 12,
              borderRadius: 4,
              maxHeight: 400,
              overflow: 'auto',
              fontSize: 11,
              fontFamily: 'monospace',
              color: '#c9d1d9',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
            }}
          >
            {logs.logs || 'No logs available'}
          </pre>
        ) : (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
          </div>
        )}
      </Modal>

      {/* Validation Modal */}
      <Modal
        title={
          <Space>
            {validationResult?.is_valid ? (
              <WarningOutlined style={{ color: '#faad14' }} />
            ) : (
              <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
            )}
            <span>Scenario Validation</span>
          </Space>
        }
        open={validationModalVisible}
        onCancel={() => {
          setValidationModalVisible(false);
          setPendingDeployData(null);
        }}
        footer={
          <Space>
            <Button
              onClick={() => {
                setValidationModalVisible(false);
                setPendingDeployData(null);
              }}
            >
              Cancel
            </Button>
            {hasProtocolMismatchWarnings && (
              <Button
                icon={<ToolOutlined />}
                onClick={handleRepairProtocols}
                loading={repairing}
              >
                Repair Protocols
              </Button>
            )}
            {validationResult?.is_valid && (
              <Button
                type="primary"
                onClick={handleProceedWithDeployment}
                loading={deploymentsLoading}
              >
                Deploy Anyway
              </Button>
            )}
          </Space>
        }
        width={600}
      >
        {validationResult && (
          <div>
            {/* Summary Stats */}
            <div style={{ marginBottom: 16, display: 'flex', gap: 16 }}>
              <Tag color="blue">{validationResult.device_count} Devices</Tag>
              <Tag color="green">{validationResult.flow_count} Flows</Tag>
              {validationResult.protocols_used.length > 0 && (
                <Tag color="purple">{validationResult.protocols_used.join(', ')}</Tag>
              )}
            </div>

            {/* Validation Status */}
            {validationResult.is_valid ? (
              <Alert
                message="Scenario has warnings but can be deployed"
                description="Review the warnings below. You can proceed with deployment, but the generated traffic may not be optimal."
                type="warning"
                showIcon
                style={{ marginBottom: 16 }}
              />
            ) : (
              <Alert
                message="Scenario has errors and cannot be deployed"
                description="Please fix the errors below before deploying."
                type="error"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            {/* Warnings/Errors List */}
            <div
              style={{
                maxHeight: 300,
                overflowY: 'auto',
                background: '#1a2734',
                borderRadius: 4,
                padding: 12,
              }}
            >
              {validationResult.warnings.map((warning, index) => (
                <div
                  key={index}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 8,
                    padding: '8px 0',
                    borderBottom:
                      index < validationResult.warnings.length - 1
                        ? '1px solid #2a3f54'
                        : 'none',
                  }}
                >
                  {warning.severity === 'error' ? (
                    <CloseCircleOutlined style={{ color: '#ff4d4f', marginTop: 2 }} />
                  ) : (
                    <ExclamationCircleOutlined style={{ color: '#faad14', marginTop: 2 }} />
                  )}
                  <div>
                    <Text style={{ color: '#e6f1ff', fontSize: 13 }}>
                      {warning.message}
                    </Text>
                    {warning.details && (
                      <div>
                        <Text style={{ color: '#6a8caf', fontSize: 11 }}>
                          {warning.details}
                        </Text>
                      </div>
                    )}
                    <Tag
                      style={{ marginTop: 4, fontSize: 10 }}
                      color={warning.severity === 'error' ? 'error' : 'warning'}
                    >
                      {warning.code}
                    </Tag>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

// Deployment Card Component
const DeploymentCard: React.FC<{
  deployment: UnifiedDeployment;
  onStop: (deployment: UnifiedDeployment) => void;
  onRemove: (id: string) => void;
  onViewLogs: (deployment: UnifiedDeployment) => void;
}> = ({ deployment, onStop, onRemove, onViewLogs }) => {
  const config = statusConfig[deployment.status] || statusConfig.pending;
  const isRunning = ['running', 'starting', 'stopping'].includes(deployment.status);
  const isPerpetual = (deployment.run_mode ?? 'timed') === 'perpetual';
  const isAgent = deployment.deployment_type === 'agent';
  const targetName = isAgent ? deployment.agent_name : deployment.docker_host_name;

  // Calculate progress if we have start time and duration (only for timed mode Docker deployments)
  let progress = 0;
  if (deployment.started_at && deployment.status === 'running' && !isPerpetual && deployment.duration_ms) {
    const startTime = new Date(deployment.started_at).getTime();
    const elapsed = Date.now() - startTime;
    progress = Math.min(100, (elapsed / deployment.duration_ms) * 100);
  }

  return (
    <Card
      size="small"
      style={{
        background: '#1a2734',
        border: '1px solid #2a3f54',
      }}
      styles={{ body: { padding: '8px 12px' } }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Target name on top */}
          <div style={{ marginBottom: 4 }}>
            <Text strong style={{ color: '#e6f1ff', fontSize: 13 }}>
              {targetName || 'Unknown'}
            </Text>
          </div>

          {/* Status tags */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 4 }}>
            <Tag color={config.color} icon={config.icon} style={{ margin: 0 }}>
              {config.label}
            </Tag>
            {isAgent && (
              <Tag color="blue" icon={<RocketOutlined />} style={{ margin: 0 }}>
                Agent
              </Tag>
            )}
            {isPerpetual && (
              <Tag color="purple" style={{ margin: 0 }}>
                Perpetual
              </Tag>
            )}
          </div>

          {/* Interface and packets */}
          <div style={{ marginTop: 4 }}>
            <Text style={{ color: '#6a8caf', fontSize: 11 }}>
              Interface: <Text code style={{ fontSize: 10 }}>{deployment.network_interface}</Text>
            </Text>
            {deployment.packets_injected > 0 && (
              <Text style={{ color: '#6a8caf', fontSize: 11, marginLeft: 12 }}>
                Packets: {deployment.packets_injected.toLocaleString()}
              </Text>
            )}
          </div>

          {deployment.error_message && (
            <div style={{ marginTop: 4 }}>
              <Text type="danger" style={{ fontSize: 11 }}>
                {deployment.error_message}
              </Text>
            </div>
          )}

          {deployment.status === 'running' && (
            isPerpetual || isAgent ? (
              <div style={{ marginTop: 8 }}>
                <Text style={{ color: '#6a8caf', fontSize: 11 }}>
                  Running for {formatElapsedTime(deployment.started_at)}
                </Text>
              </div>
            ) : (
              <Progress
                percent={Math.round(progress)}
                size="small"
                strokeColor="#5a9fd4"
                style={{ marginTop: 8, marginBottom: 0 }}
              />
            )
          )}
        </div>

        <div style={{ display: 'flex', gap: 2, marginLeft: 8 }}>
          {!isAgent && deployment.container_id && (
            <Tooltip title="View Logs">
              <Button
                type="text"
                size="small"
                icon={<FileTextOutlined />}
                onClick={() => onViewLogs(deployment)}
              />
            </Tooltip>
          )}

          {isRunning ? (
            <Tooltip title="Stop">
              <Button
                type="text"
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={() => onStop(deployment)}
              />
            </Tooltip>
          ) : (
            <Tooltip title="Remove">
              <Button
                type="text"
                size="small"
                icon={<DeleteOutlined />}
                onClick={() => onRemove(deployment.id)}
              />
            </Tooltip>
          )}
        </div>
      </div>
    </Card>
  );
};

export default DeploymentPanel;
