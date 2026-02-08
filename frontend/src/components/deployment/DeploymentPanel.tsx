/**
 * Deployment Panel - Deploy scenarios to remote Docker hosts or traffic agents
 */

import React, { useEffect, useMemo, useState } from 'react';
import {
  Form,
  Typography,
  Divider,
  Space,
  message,
} from 'antd';
import { CloudServerOutlined } from '@ant-design/icons';
import { useDockerHostsStore } from '../../stores/dockerHostsStore';
import { useDeploymentsStore } from '../../stores/deploymentsStore';
import { useAgentsStore } from '../../stores/agentsStore';
import { useScenarioStore } from '../../stores/scenarioStore';
import { scenariosApi, type ScenarioValidationResponse } from '../../api/scenarios';
import type {
  UnifiedDeployment,
  DeploymentRequest,
  NetworkInterface,
  RunMode,
} from '../../types/docker';
import type { AgentInterface } from '../../types/agent';
import { extractErrorMessage } from '../../utils/errorUtils';

import { PanelContainer, ErrorAlert, EmptyState } from '../common';
import { useAttackStore } from '../../stores/attackStore';
import DeploymentCard from './DeploymentCard';
import DeploymentForm, { type TargetType, type PhaseScheduleConfig } from './DeploymentForm';
import ReadinessChecklist from './ReadinessChecklist';
import ValidationModal from './ValidationModal';
import LogsModal from './LogsModal';

const { Title } = Typography;

interface DeploymentPanelProps {
  scenarioId: string | null;
}

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
  const [hasReadinessErrors, setHasReadinessErrors] = useState(false);
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
    phase_schedule?: PhaseScheduleConfig;
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
          const deployData: { scenario_id: string; interface: string; adaptive_config?: Record<string, unknown>; attack_playbook?: Record<string, unknown> } = {
            scenario_id: scenarioId,
            interface: values.network_interface,
          };
          if (values.phase_schedule?.enabled) {
            deployData.adaptive_config = { phase_schedule: values.phase_schedule };
          }
          // Include attack playbook config if configured
          const attackConfig = useAttackStore.getState().playbookConfig;
          if (attackConfig?.playbook_id) {
            deployData.attack_playbook = attackConfig as unknown as Record<string, unknown>;
          }
          await deployToAgent(values.agent_id, deployData);
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

  const scenarioPhases = useScenarioStore((s) => s.phases);

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
      <PanelContainer>
        <EmptyState
          icon={<CloudServerOutlined />}
          message="Save the scenario first to enable deployment"
        />
      </PanelContainer>
    );
  }

  return (
    <PanelContainer>
      <ErrorAlert error={error} onClose={clearError} compact />

      {/* Readiness Checklist */}
      <ReadinessChecklist
        scenarioId={scenarioId}
        onReadinessChange={setHasReadinessErrors}
      />

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
        phases={scenarioPhases}
        loadingInterfaces={loadingInterfaces}
        validating={validating}
        deploymentsLoading={deploymentsLoading}
        deployDisabled={hasReadinessErrors}
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
    </PanelContainer>
  );
};

export default DeploymentPanel;
