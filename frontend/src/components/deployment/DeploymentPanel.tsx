/**
 * Deployment Panel - Deploy scenarios to remote Docker hosts
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
} from '@ant-design/icons';
import { useDockerHostsStore } from '../../stores/dockerHostsStore';
import { useDeploymentsStore } from '../../stores/deploymentsStore';
import { scenariosApi, type ScenarioValidationResponse } from '../../api/scenarios';
import type { Deployment, DeploymentRequest, NetworkInterface, RunMode } from '../../types/docker';

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

const DeploymentPanel: React.FC<DeploymentPanelProps> = ({ scenarioId }) => {
  const [form] = Form.useForm();
  const [interfaces, setInterfaces] = useState<NetworkInterface[]>([]);
  const [loadingInterfaces, setLoadingInterfaces] = useState(false);
  const [logsModalVisible, setLogsModalVisible] = useState(false);
  const [validationModalVisible, setValidationModalVisible] = useState(false);
  const [validationResult, setValidationResult] = useState<ScenarioValidationResponse | null>(null);
  const [validating, setValidating] = useState(false);
  const [pendingDeployData, setPendingDeployData] = useState<DeploymentRequest | null>(null);

  const {
    hosts,
    fetchHosts,
    fetchInterfaces,
    isLoading: hostsLoading,
  } = useDockerHostsStore();

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

  // Fetch hosts and deployments on mount
  useEffect(() => {
    fetchHosts();
    if (scenarioId) {
      fetchDeployments({ scenario_id: scenarioId });
    }
    return () => {
      stopPolling();
    };
  }, [fetchHosts, fetchDeployments, scenarioId, stopPolling]);

  // Filter deployments for current scenario
  const scenarioDeployments = deployments.filter(
    (d) => d.scenario_id === scenarioId
  );

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
    docker_host_id: string;
    network_interface: string;
    run_mode: RunMode;
    duration_minutes?: number;
  }) => {
    if (!scenarioId) return;

    const data: DeploymentRequest = {
      scenario_id: scenarioId,
      docker_host_id: values.docker_host_id,
      network_interface: values.network_interface,
      run_mode: values.run_mode,
      duration_ms: values.run_mode === 'perpetual' ? undefined : (values.duration_minutes ?? 5) * 60 * 1000,
    };

    // Validate scenario first
    const validation = await validateScenario();

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
  };

  // Handle proceed with deployment after seeing warnings
  const handleProceedWithDeployment = async () => {
    setValidationModalVisible(false);
    if (pendingDeployData) {
      await executeDeployment(pendingDeployData);
    }
  };

  // Handle stop
  const handleStop = async (deploymentId: string) => {
    try {
      await stopDeployment(deploymentId);
    } catch {
      // Error handled in store
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
  const handleViewLogs = async (deployment: Deployment) => {
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
        {activeHosts.length === 0 ? (
          <Alert
            message="No Docker hosts available"
            description="Configure Docker hosts in Settings > Docker Hosts"
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
                disabled={interfaces.length === 0}
                options={interfaces.map((i) => ({
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
                }))}
              />
            </Form.Item>

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

// Helper function to format elapsed time
const formatElapsedTime = (startedAt: string | null): string => {
  if (!startedAt) return '0s';
  const elapsed = Date.now() - new Date(startedAt).getTime();
  const hours = Math.floor(elapsed / 3600000);
  const minutes = Math.floor((elapsed % 3600000) / 60000);
  const seconds = Math.floor((elapsed % 60000) / 1000);

  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
};

// Deployment Card Component
const DeploymentCard: React.FC<{
  deployment: Deployment;
  onStop: (id: string) => void;
  onRemove: (id: string) => void;
  onViewLogs: (deployment: Deployment) => void;
}> = ({ deployment, onStop, onRemove, onViewLogs }) => {
  const config = statusConfig[deployment.status] || statusConfig.pending;
  const isRunning = ['running', 'starting', 'stopping'].includes(deployment.status);
  const isPerpetual = (deployment.run_mode ?? 'timed') === 'perpetual';

  // Calculate progress if we have start time and duration (only for timed mode)
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
        <div style={{ flex: 1 }}>
          <Space>
            <Tag color={config.color} icon={config.icon}>
              {config.label}
            </Tag>
            {isPerpetual && (
              <Tag color="purple">
                Perpetual
              </Tag>
            )}
            <Text style={{ color: '#8aa4bc', fontSize: 12 }}>
              {deployment.docker_host_name}
            </Text>
          </Space>

          <div style={{ marginTop: 4 }}>
            <Text style={{ color: '#6a8caf', fontSize: 11 }}>
              Interface: <Text code style={{ fontSize: 10 }}>{deployment.network_interface}</Text>
            </Text>
          </div>

          {deployment.error_message && (
            <div style={{ marginTop: 4 }}>
              <Text type="danger" style={{ fontSize: 11 }}>
                {deployment.error_message}
              </Text>
            </div>
          )}

          {deployment.status === 'running' && (
            isPerpetual ? (
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

        <Space size="small">
          <Tooltip title="View Logs">
            <Button
              type="text"
              size="small"
              icon={<FileTextOutlined />}
              onClick={() => onViewLogs(deployment)}
              disabled={!deployment.container_id}
            />
          </Tooltip>

          {isRunning ? (
            <Tooltip title="Stop">
              <Button
                type="text"
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={() => onStop(deployment.id)}
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
        </Space>
      </div>
    </Card>
  );
};

export default DeploymentPanel;
