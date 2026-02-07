/**
 * Deployment Panel - Deploy scenarios to remote Docker hosts or traffic agents
 */

import React, { useEffect, useMemo, useState } from 'react';
import {
  Form,
  Typography,
  Alert,
  Divider,
  Tag,
  Progress,
  Card,
  Tooltip,
  Empty,
  Space,
  Button,
  message,
} from 'antd';
import {
  CloudServerOutlined,
  StopOutlined,
  DeleteOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { useDockerHostsStore } from '../../stores/dockerHostsStore';
import { useDeploymentsStore } from '../../stores/deploymentsStore';
import { useAgentsStore } from '../../stores/agentsStore';
import { scenariosApi, type ScenarioValidationResponse } from '../../api/scenarios';
import type {
  UnifiedDeployment,
  DeploymentRequest,
  NetworkInterface,
  RunMode,
} from '../../types/docker';
import type { AgentInterface } from '../../types/agent';
import { formatElapsedTime } from '../../utils/dateUtils';
import { extractErrorMessage } from '../../utils/errorUtils';

import DeploymentForm, { type TargetType } from './DeploymentForm';
import ValidationModal from './ValidationModal';
import LogsModal from './LogsModal';

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

const DeploymentPanel: React.FC<DeploymentPanelProps> = ({
  scenarioId,
}) => {
  const [form] = Form.useForm();
  const [targetType, setTargetType] = useState<TargetType>('agent');
  const [interfaces, setInterfaces] = useState<NetworkInterface[]>([]);
  const [agentInterfaces, setAgentInterfaces] = useState<AgentInterface[]>(
    [],
  );
  const [loadingInterfaces, setLoadingInterfaces] = useState(false);
  const [logsModalVisible, setLogsModalVisible] = useState(false);
  const [validationModalVisible, setValidationModalVisible] =
    useState(false);
  const [validationResult, setValidationResult] =
    useState<ScenarioValidationResponse | null>(null);
  const [validating, setValidating] = useState(false);
  const [repairing, setRepairing] = useState(false);
  const [pendingDeployData, setPendingDeployData] =
    useState<DeploymentRequest | null>(null);

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

  const scenarioDeployments = useMemo(
    () => deployments.filter((d) => d.scenario_id === scenarioId),
    [deployments, scenarioId],
  );

  // ── Fetch on mount ──────────────────────────────────────────────
  useEffect(() => {
    fetchHosts();
    fetchAgents();
    if (scenarioId) fetchDeployments({ scenario_id: scenarioId });
    return () => {
      stopPolling();
    };
  }, [fetchHosts, fetchAgents, fetchDeployments, scenarioId, stopPolling]);

  // ── Poll active deployments ─────────────────────────────────────
  useEffect(() => {
    const hasActive = scenarioDeployments.some((d) =>
      ['running', 'starting', 'stopping'].includes(d.status),
    );
    if (!hasActive || !scenarioId) return;

    const pollInterval = setInterval(() => {
      fetchDeployments({ scenario_id: scenarioId });
    }, 5000);

    return () => clearInterval(pollInterval);
  }, [scenarioDeployments, scenarioId, fetchDeployments]);

  // ── Target type change ──────────────────────────────────────────
  const handleTargetTypeChange = (type: TargetType) => {
    setTargetType(type);
    setInterfaces([]);
    setAgentInterfaces([]);
    form.setFieldValue('docker_host_id', undefined);
    form.setFieldValue('agent_id', undefined);
    form.setFieldValue('network_interface', undefined);
  };

  // ── Host selection ──────────────────────────────────────────────
  const handleHostChange = async (hostId: string) => {
    setLoadingInterfaces(true);
    setInterfaces([]);
    form.setFieldValue('network_interface', undefined);
    try {
      const result = await fetchInterfaces(hostId);
      setInterfaces(result.interfaces);
      const host = hosts.find((h) => h.id === hostId);
      if (host?.default_interface) {
        const hasDefault = result.interfaces.some(
          (i) => i.name === host.default_interface,
        );
        if (hasDefault)
          form.setFieldValue(
            'network_interface',
            host.default_interface,
          );
      }
    } catch {
      // Error handled in store
    } finally {
      setLoadingInterfaces(false);
    }
  };

  // ── Agent selection ─────────────────────────────────────────────
  const handleAgentChange = async (agentId: string) => {
    setLoadingInterfaces(true);
    setAgentInterfaces([]);
    form.setFieldValue('network_interface', undefined);
    try {
      const result = await fetchAgentInterfaces(agentId);
      setAgentInterfaces(result);
      const agent = agents.find((a) => a.id === agentId);
      if (agent?.default_interface) {
        const hasDefault = result.some(
          (i) => i.name === agent.default_interface,
        );
        if (hasDefault)
          form.setFieldValue(
            'network_interface',
            agent.default_interface,
          );
      }
    } catch {
      // Error handled in store
    } finally {
      setLoadingInterfaces(false);
    }
  };

  // ── Validate ────────────────────────────────────────────────────
  const validateScenario =
    async (): Promise<ScenarioValidationResponse | null> => {
      if (!scenarioId) return null;
      setValidating(true);
      try {
        return await scenariosApi.validate(scenarioId);
      } catch {
        return null;
      } finally {
        setValidating(false);
      }
    };

  // ── Execute deployment ──────────────────────────────────────────
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

  // ── Deploy handler ──────────────────────────────────────────────
  const handleDeploy = async (values: {
    docker_host_id?: string;
    agent_id?: string;
    network_interface: string;
    run_mode: RunMode;
    duration_minutes?: number;
  }) => {
    if (!scenarioId) return;

    const validation = await validateScenario();

    if (targetType === 'agent') {
      if (!values.agent_id) return;

      const agentDeployData = {
        scenario_id: scenarioId,
        agent_id: values.agent_id,
        interface: values.network_interface,
      };

      if (!validation || validation.warnings.length === 0) {
        try {
          await deployToAgent(values.agent_id, {
            scenario_id: scenarioId,
            interface: values.network_interface,
          });
          message.success(
            'Scenario deployed to agent successfully! Traffic generation started.',
          );
          form.resetFields(['agent_id', 'network_interface']);
          setAgentInterfaces([]);
          await fetchDeployments({ scenario_id: scenarioId });
        } catch (err: unknown) {
          message.error(
            extractErrorMessage(
              err,
              'Failed to deploy scenario to agent',
            ),
          );
        }
      } else {
        setPendingDeployData({
          ...agentDeployData,
          docker_host_id: '',
          network_interface: values.network_interface,
          run_mode: 'perpetual',
        });
        setValidationResult(validation);
        setValidationModalVisible(true);
      }
    } else {
      if (!values.docker_host_id) return;

      const data: DeploymentRequest = {
        scenario_id: scenarioId,
        docker_host_id: values.docker_host_id,
        network_interface: values.network_interface,
        run_mode: values.run_mode,
        duration_ms:
          values.run_mode === 'perpetual'
            ? undefined
            : (values.duration_minutes ?? 5) * 60 * 1000,
      };

      if (!validation) {
        await executeDeployment(data);
        return;
      }

      if (validation.warnings.length > 0) {
        setPendingDeployData(data);
        setValidationResult(validation);
        setValidationModalVisible(true);
      } else {
        await executeDeployment(data);
      }
    }
  };

  // ── Proceed after validation ────────────────────────────────────
  const handleProceedWithDeployment = async () => {
    setValidationModalVisible(false);
    if (pendingDeployData) await executeDeployment(pendingDeployData);
  };

  // ── Repair protocols ────────────────────────────────────────────
  const handleRepairProtocols = async () => {
    if (!scenarioId) return;
    setRepairing(true);
    try {
      const result = await scenariosApi.repairProtocols(scenarioId);
      message.success(result.message);

      setValidating(true);
      const validation = await scenariosApi.validate(scenarioId);
      setValidationResult(validation);

      if (validation.warnings.length === 0) {
        setValidationModalVisible(false);
        message.success('All issues fixed! You can now deploy.');
      }
    } catch (err: unknown) {
      message.error(
        extractErrorMessage(err, 'Failed to repair protocols'),
      );
    } finally {
      setRepairing(false);
      setValidating(false);
    }
  };

  // ── Stop deployment ─────────────────────────────────────────────
  const handleStop = async (deployment: UnifiedDeployment) => {
    try {
      if (
        deployment.deployment_type === 'agent' &&
        deployment.agent_id
      ) {
        const { stopDeployment: stopAgentDeployment } =
          useAgentsStore.getState();
        await stopAgentDeployment(
          deployment.agent_id,
          deployment.scenario_id,
        );
        message.success('Stop command sent to agent');
        await fetchDeployments({ scenario_id: scenarioId! });
      } else {
        await stopDeployment(deployment.id);
        message.success('Deployment stopped');
      }
    } catch (err: unknown) {
      message.error(
        extractErrorMessage(err, 'Failed to stop deployment'),
      );
    }
  };

  // ── Remove / logs ───────────────────────────────────────────────
  const handleRemove = async (deploymentId: string) => {
    try {
      await removeDeployment(deploymentId);
    } catch {
      // Error handled in store
    }
  };

  const handleViewLogs = async (deployment: UnifiedDeployment) => {
    setActiveDeployment(deployment);
    setLogsModalVisible(true);
    try {
      await fetchLogs(deployment.id);
    } catch {
      // Error handled in store
    }
  };

  const handleRefreshLogs = async () => {
    if (activeDeployment) {
      try {
        await fetchLogs(activeDeployment.id);
      } catch {
        // Error handled in store
      }
    }
  };

  const activeHosts = useMemo(
    () => hosts.filter((h) => h.is_active),
    [hosts],
  );
  const onlineAgents = useMemo(
    () => agents.filter((a) => a.status === 'online' && a.is_active),
    [agents],
  );

  // ── Guard: no scenario ──────────────────────────────────────────
  if (!scenarioId) {
    return (
      <div style={{ padding: '16px' }}>
        <Empty
          image={
            <CloudServerOutlined
              style={{ fontSize: 48, color: '#4a6a8a' }}
            />
          }
          description={
            <Text style={{ color: '#8aa4bc' }}>
              Save the scenario first to enable deployment
            </Text>
          }
        />
      </div>
    );
  }

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
      <DeploymentForm
        form={form}
        targetType={targetType}
        onTargetTypeChange={handleTargetTypeChange}
        onlineAgents={onlineAgents}
        agentsLoading={agentsLoading}
        agentInterfaces={agentInterfaces}
        onAgentChange={handleAgentChange}
        activeHosts={activeHosts}
        hostsLoading={hostsLoading}
        interfaces={interfaces}
        onHostChange={handleHostChange}
        loadingInterfaces={loadingInterfaces}
        validating={validating}
        deploymentsLoading={deploymentsLoading}
        onFinish={handleDeploy}
      />

      {/* Active Deployments */}
      {scenarioDeployments.length > 0 && (
        <>
          <Divider
            style={{ margin: '8px 0', borderColor: '#2a3f54' }}
          />
          <div>
            <Title
              level={5}
              style={{
                color: '#8aa4bc',
                marginBottom: 12,
                fontSize: 13,
              }}
            >
              Deployments
            </Title>
            <Space
              direction="vertical"
              style={{ width: '100%' }}
              size="small"
            >
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
      <LogsModal
        open={logsModalVisible}
        logs={logs}
        onClose={() => setLogsModalVisible(false)}
        onRefresh={handleRefreshLogs}
      />

      {/* Validation Modal */}
      <ValidationModal
        open={validationModalVisible}
        validationResult={validationResult}
        deploymentsLoading={deploymentsLoading}
        repairing={repairing}
        onCancel={() => {
          setValidationModalVisible(false);
          setPendingDeployData(null);
        }}
        onProceed={handleProceedWithDeployment}
        onRepair={handleRepairProtocols}
      />
    </div>
  );
};

// ── Deployment Card ─────────────────────────────────────────────────
const DeploymentCard: React.FC<{
  deployment: UnifiedDeployment;
  onStop: (deployment: UnifiedDeployment) => void;
  onRemove: (id: string) => void;
  onViewLogs: (deployment: UnifiedDeployment) => void;
}> = ({ deployment, onStop, onRemove, onViewLogs }) => {
  const config =
    statusConfig[deployment.status] || statusConfig.pending;
  const isRunning = ['running', 'starting', 'stopping'].includes(
    deployment.status,
  );
  const isPerpetual = (deployment.run_mode ?? 'timed') === 'perpetual';
  const isAgent = deployment.deployment_type === 'agent';
  const targetName = isAgent
    ? deployment.agent_name
    : deployment.docker_host_name;

  // Track current time in state for progress calculation (avoids impure Date.now() in render)
  const [now, setNow] = useState(() => new Date().getTime());
  const needsProgress =
    deployment.started_at &&
    deployment.status === 'running' &&
    !isPerpetual &&
    deployment.duration_ms;

  useEffect(() => {
    if (!needsProgress) return;
    const id = setInterval(() => setNow(new Date().getTime()), 1000);
    return () => clearInterval(id);
  }, [needsProgress]);

  let computedProgress = 0;
  if (needsProgress && deployment.started_at && deployment.duration_ms) {
    const startTime = new Date(deployment.started_at).getTime();
    const elapsed = now - startTime;
    computedProgress = Math.min(100, (elapsed / deployment.duration_ms) * 100);
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
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ marginBottom: 4 }}>
            <Text
              strong
              style={{ color: '#e6f1ff', fontSize: 13 }}
            >
              {targetName || 'Unknown'}
            </Text>
          </div>

          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 4,
              marginBottom: 4,
            }}
          >
            <Tag
              color={config.color}
              icon={config.icon}
              style={{ margin: 0 }}
            >
              {config.label}
            </Tag>
            {isAgent && (
              <Tag
                color="blue"
                icon={<RocketOutlined />}
                style={{ margin: 0 }}
              >
                Agent
              </Tag>
            )}
            {isPerpetual && (
              <Tag color="purple" style={{ margin: 0 }}>
                Perpetual
              </Tag>
            )}
          </div>

          <div style={{ marginTop: 4 }}>
            <Text style={{ color: '#6a8caf', fontSize: 11 }}>
              Interface:{' '}
              <Text code style={{ fontSize: 10 }}>
                {deployment.network_interface}
              </Text>
            </Text>
            {deployment.packets_injected > 0 && (
              <Text
                style={{
                  color: '#6a8caf',
                  fontSize: 11,
                  marginLeft: 12,
                }}
              >
                Packets:{' '}
                {deployment.packets_injected.toLocaleString()}
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

          {deployment.status === 'running' &&
            (isPerpetual || isAgent ? (
              <div style={{ marginTop: 8 }}>
                <Text style={{ color: '#6a8caf', fontSize: 11 }}>
                  Running for{' '}
                  {formatElapsedTime(deployment.started_at)}
                </Text>
              </div>
            ) : (
              <Progress
                percent={Math.round(computedProgress)}
                size="small"
                strokeColor="#5a9fd4"
                style={{ marginTop: 8, marginBottom: 0 }}
              />
            ))}
        </div>

        <div
          style={{ display: 'flex', gap: 2, marginLeft: 8 }}
        >
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
