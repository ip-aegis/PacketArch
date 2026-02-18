/**
 * Deployment Panel - Deploy scenarios to traffic agents
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
import { useDeploymentsStore } from '../../stores/deploymentsStore';
import { useAgentsStore } from '../../stores/agentsStore';
import { useScenarioStore } from '../../stores/scenarioStore';
import { scenariosApi, type ScenarioValidationResponse } from '../../api/scenarios';
import type {
  UnifiedDeployment,
  RunMode,
} from '../../types/docker';
import type { AgentInterface, DeploymentCreate } from '../../types/agent';
import { extractErrorMessage } from '../../utils/errorUtils';

import { PanelContainer, ErrorAlert, EmptyState } from '../common';
import { useAttackStore } from '../../stores/attackStore';
import DeploymentCard from './DeploymentCard';
import DeploymentForm, { type PhaseScheduleConfig } from './DeploymentForm';
import ReadinessChecklist from './ReadinessChecklist';
import ValidationModal from './ValidationModal';

const { Title } = Typography;

interface DeploymentPanelProps {
  scenarioId: string | null;
}

const DeploymentPanel: React.FC<DeploymentPanelProps> = ({
  scenarioId,
}) => {
  const [form] = Form.useForm();
  const [agentInterfaces, setAgentInterfaces] = useState<AgentInterface[]>([]);
  const [loadingInterfaces, setLoadingInterfaces] = useState(false);
  const [validationModalVisible, setValidationModalVisible] = useState(false);
  const [validationResult, setValidationResult] =
    useState<ScenarioValidationResponse | null>(null);
  const [validating, setValidating] = useState(false);
  const [repairing, setRepairing] = useState(false);
  const [hasReadinessErrors, setHasReadinessErrors] = useState(false);
  const [pendingAgentDeploy, setPendingAgentDeploy] = useState<{
    agentId: string;
    deployData: DeploymentCreate;
  } | null>(null);

  const {
    agents,
    fetchAgents,
    fetchInterfaces: fetchAgentInterfaces,
    deployScenario: deployToAgent,
    isLoading: agentsLoading,
  } = useAgentsStore();

  const {
    deployments,
    isLoading: deploymentsLoading,
    error,
    fetchDeployments,
    removeDeployment,
    clearError,
  } = useDeploymentsStore();

  const scenarioDeployments = useMemo(
    () => deployments.filter((d) => d.scenario_id === scenarioId),
    [deployments, scenarioId],
  );

  // ── Fetch on mount ──────────────────────────────────────────────
  useEffect(() => {
    fetchAgents();
    if (scenarioId) fetchDeployments({ scenario_id: scenarioId });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioId]);

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

  // ── Deploy handler ──────────────────────────────────────────────
  const handleDeploy = async (values: {
    agent_id?: string;
    network_interface: string;
    run_mode: RunMode;
    duration_minutes?: number;
    phase_schedule?: PhaseScheduleConfig;
  }) => {
    if (!scenarioId || !values.agent_id) return;

    const validation = await validateScenario();

    const deployData: DeploymentCreate = {
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

    if (!validation || validation.warnings.length === 0) {
      try {
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
      setPendingAgentDeploy({ agentId: values.agent_id, deployData });
      setValidationResult(validation);
      setValidationModalVisible(true);
    }
  };

  // ── Proceed after validation ────────────────────────────────────
  const handleProceedWithDeployment = async () => {
    setValidationModalVisible(false);
    if (pendingAgentDeploy) {
      try {
        await deployToAgent(pendingAgentDeploy.agentId, pendingAgentDeploy.deployData);
        message.success(
          'Scenario deployed to agent successfully! Traffic generation started.',
        );
        form.resetFields(['agent_id', 'network_interface']);
        setAgentInterfaces([]);
        if (scenarioId) await fetchDeployments({ scenario_id: scenarioId });
      } catch (err: unknown) {
        message.error(
          extractErrorMessage(err, 'Failed to deploy scenario to agent'),
        );
      } finally {
        setPendingAgentDeploy(null);
      }
    }
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
      if (deployment.agent_id) {
        const { stopDeployment: stopAgentDeployment } =
          useAgentsStore.getState();
        await stopAgentDeployment(
          deployment.agent_id,
          deployment.scenario_id,
        );
        message.success('Stop command sent to agent');
        await fetchDeployments({ scenario_id: scenarioId! });
      }
    } catch (err: unknown) {
      message.error(
        extractErrorMessage(err, 'Failed to stop deployment'),
      );
    }
  };

  // ── Remove ───────────────────────────────────────────────────
  const handleRemove = async (deploymentId: string) => {
    try {
      await removeDeployment(deploymentId);
    } catch {
      // Error handled in store
    }
  };

  const scenarioPhases = useScenarioStore((s) => s.phases);

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
        onlineAgents={onlineAgents}
        agentsLoading={agentsLoading}
        agentInterfaces={agentInterfaces}
        onAgentChange={handleAgentChange}
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
                />
              ))}
            </Space>
          </div>
        </>
      )}

      {/* Validation Modal */}
      <ValidationModal
        open={validationModalVisible}
        validationResult={validationResult}
        deploymentsLoading={deploymentsLoading}
        repairing={repairing}
        onCancel={() => {
          setValidationModalVisible(false);
          setPendingAgentDeploy(null);
        }}
        onProceed={handleProceedWithDeployment}
        onRepair={handleRepairProtocols}
      />
    </PanelContainer>
  );
};

export default DeploymentPanel;
