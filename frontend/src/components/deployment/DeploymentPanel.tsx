/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Deployment Panel - Deploy scenarios to traffic agents
 */

import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Form,
  Progress,
  Typography,
  Divider,
  Space,
  Button,
  Tag,
  Tooltip,
  message,
} from 'antd';
import { CloudServerOutlined, ApiOutlined, LoadingOutlined } from '@ant-design/icons';
import type { CVProvisionStatus } from '../../api/cyberVision';
import { useDeploymentsStore } from '../../stores/deploymentsStore';
import { useAgentsStore } from '../../stores/agentsStore';
import { useScenarioStore } from '../../stores/scenarioStore';
import { scenariosApi, type ScenarioValidationResponse } from '../../api/scenarios';
import { cyberVisionApi } from '../../api/cyberVision';
import localSensorApi, { type LocalLabItem } from '../../api/localSensor';
import type {
  UnifiedDeployment,
  RunMode,
} from '../../types/docker';
import type { AgentInterface, DeploymentCreate, DeployNewLabRequest } from '../../types/agent';
import { extractErrorMessage } from '../../utils/errorUtils';

import { PanelContainer, ErrorAlert, EmptyState } from '../common';
import { useAttackStore } from '../../stores/attackStore';
import DeploymentCard from './DeploymentCard';
import DeploymentForm, { type PhaseScheduleConfig } from './DeploymentForm';
import ReadinessChecklist from './ReadinessChecklist';
import ValidationModal from './ValidationModal';

const { Title, Text } = Typography;

interface DeploymentPanelProps {
  scenarioId: string | null;
  /** Scenario phases override — Studio v2 passes its own document's phases
      (the v1 scenarioStore is empty on the /studio2 route). */
  phases?: import('../../types').Phase[];
  /** Scenario name override — same reasoning as phases above. Defaults the
      "New Local Lab" name field. */
  scenarioName?: string;
}

const DeploymentPanel: React.FC<DeploymentPanelProps> = ({
  scenarioId,
  phases,
  scenarioName: scenarioNameProp,
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
  const [cvConfigured, setCvConfigured] = useState(false);
  const [cvProvision, setCvProvision] = useState<CVProvisionStatus | null>(null);
  const [cvProvisioning, setCvProvisioning] = useState(false);
  const [pendingAgentDeploy, setPendingAgentDeploy] = useState<
    | { mode: 'existing'; agentId: string; deployData: DeploymentCreate }
    | { mode: 'new_lab'; payload: DeployNewLabRequest }
    | null
  >(null);
  // New-lab deploys go through a different store than deploymentsLoading —
  // tracked separately so the Deploy button shows it's actually working.
  const [newLabDeploying, setNewLabDeploying] = useState(false);
  // Persistent status for a lab created via "New Local Lab", from the
  // moment it's queued until its scenario deployment actually appears (or it
  // errors) — a toast alone gave no lasting sign anything had happened.
  const [provisioningLab, setProvisioningLab] = useState<LocalLabItem | null>(null);

  const {
    agents,
    fetchAgents,
    fetchInterfaces: fetchAgentInterfaces,
    deployScenario: deployToAgent,
    deployToNewLab,
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

  // ── Detect whether Cyber Vision is configured ───────────────────
  useEffect(() => {
    let cancelled = false;
    cyberVisionApi
      .getSettings()
      .then((s) => {
        if (!cancelled) setCvConfigured(!!s.cyber_vision_url && s.cyber_vision_api_token_set);
      })
      .catch(() => {
        if (!cancelled) setCvConfigured(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // ── Load CV provisioning state for this scenario ────────────────
  useEffect(() => {
    if (!scenarioId || !cvConfigured) return;
    let cancelled = false;
    cyberVisionApi
      .getProvisionStatus(scenarioId)
      .then((s) => {
        if (!cancelled) setCvProvision(s);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [scenarioId, cvConfigured]);

  // ── Poll CV provisioning while groups are being created ─────────
  useEffect(() => {
    if (!scenarioId || cvProvision?.status !== 'polling') return;
    const id = setInterval(() => {
      cyberVisionApi
        .getProvisionStatus(scenarioId)
        .then((s) => setCvProvision(s))
        .catch(() => undefined);
    }, 15000);
    return () => clearInterval(id);
  }, [scenarioId, cvProvision?.status]);

  // ── Manual "Push to Cyber Vision" ───────────────────────────────
  const handleProvisionCv = async () => {
    if (!scenarioId) return;
    setCvProvisioning(true);
    try {
      const state = await cyberVisionApi.provisionScenario(scenarioId);
      setCvProvision(state);
      message.success('Cyber Vision preset created. Zone groups will appear once CV discovers the devices.');
    } catch (err: unknown) {
      message.error(extractErrorMessage(err, 'Failed to provision Cyber Vision'));
    } finally {
      setCvProvisioning(false);
    }
  };

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

  // ── Poll a newly-provisioned lab until its scenario deployment fires ────
  // A lab built via "New Local Lab" has no AgentDeployment row yet (it's
  // created once the agent connects, see agent_manager.resolve_pending_deploy)
  // — the existing active-deployment poll above never starts without one.
  useEffect(() => {
    if (!provisioningLab || !scenarioId) return;

    const fired = scenarioDeployments.some(
      (d) => d.agent_id === provisioningLab.agent_id,
    );
    if (fired) {
      setProvisioningLab(null);
      return;
    }

    const pollInterval = setInterval(() => {
      localSensorApi.getLab(provisioningLab.lab_id).then(setProvisioningLab).catch(() => undefined);
      fetchDeployments({ scenario_id: scenarioId });
    }, 3000);

    return () => clearInterval(pollInterval);
  }, [provisioningLab, scenarioDeployments, scenarioId, fetchDeployments]);

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
        // Managed (local-lab / CML) agents have an authoritative injection
        // interface — set it unconditionally so the locked picker always
        // carries the right value even if the live interface query lags or
        // doesn't list it. Manual agents only pre-select when present.
        const isManaged = !!(agent.local_lab_id || agent.cml_lab_id);
        const hasDefault = result.some(
          (i) => i.name === agent.default_interface,
        );
        if (isManaged || hasDefault)
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

  // ── Shared deploy-field assembly (both existing-agent and new-lab modes) ─
  const buildCommonDeployFields = (values: {
    phase_schedule?: PhaseScheduleConfig;
    cell_isolation_mode?: 'inherit' | 'off' | 'conduit_gated' | 'strict_northbound';
    provision_cyber_vision?: boolean;
  }) => {
    const fields: Pick<
      DeploymentCreate,
      'adaptive_config' | 'attack_playbook' | 'cell_isolation_override' | 'provision_cyber_vision'
    > = {};
    if (values.provision_cyber_vision) {
      fields.provision_cyber_vision = true;
    }
    if (values.phase_schedule?.enabled) {
      fields.adaptive_config = { phase_schedule: values.phase_schedule };
    }
    const attackConfig = useAttackStore.getState().playbookConfig;
    if (attackConfig?.playbook_id) {
      fields.attack_playbook = attackConfig as unknown as Record<string, unknown>;
    }
    if (values.cell_isolation_mode && values.cell_isolation_mode !== 'inherit') {
      fields.cell_isolation_override = { mode: values.cell_isolation_mode };
    }
    return fields;
  };

  const runExistingDeploy = async (agentId: string, deployData: DeploymentCreate) => {
    try {
      await deployToAgent(agentId, deployData);
      message.success(
        'Scenario deployed to agent successfully! Traffic generation started.',
      );
      form.resetFields(['agent_id', 'network_interface']);
      setAgentInterfaces([]);
      if (scenarioId) await fetchDeployments({ scenario_id: scenarioId });
    } catch (err: unknown) {
      message.error(extractErrorMessage(err, 'Failed to deploy scenario to agent'));
    }
  };

  const runNewLabDeploy = async (payload: DeployNewLabRequest) => {
    setNewLabDeploying(true);
    try {
      const result = await deployToNewLab(payload);
      message.success(
        'Local sensor lab queued for provisioning — the scenario will deploy '
        + 'automatically once the sensor comes online.',
      );
      form.resetFields(['lab_name', 'agent_name']);
      if (result.lab_id) {
        try {
          setProvisioningLab(await localSensorApi.getLab(result.lab_id));
        } catch {
          // Status card is a nice-to-have; the deploy itself already succeeded.
        }
      }
      if (scenarioId) await fetchDeployments({ scenario_id: scenarioId });
    } catch (err: unknown) {
      message.error(extractErrorMessage(err, 'Failed to deploy to a new local lab'));
    } finally {
      setNewLabDeploying(false);
    }
  };

  // ── Deploy handler ──────────────────────────────────────────────
  const handleDeploy = async (values: {
    mode: 'existing' | 'new_lab';
    agent_id?: string;
    network_interface?: string;
    lab_name?: string;
    agent_name?: string;
    run_mode: RunMode;
    duration_minutes?: number;
    phase_schedule?: PhaseScheduleConfig;
    cell_isolation_mode?: 'inherit' | 'off' | 'conduit_gated' | 'strict_northbound';
    provision_cyber_vision?: boolean;
  }) => {
    if (!scenarioId) return;
    if (values.mode === 'existing' && !values.agent_id) return;
    if (values.mode === 'new_lab' && !values.lab_name) return;

    const validation = await validateScenario();
    const common = buildCommonDeployFields(values);

    if (values.mode === 'existing') {
      const deployData: DeploymentCreate = {
        scenario_id: scenarioId,
        interface: values.network_interface,
        ...common,
      };
      if (!validation || validation.warnings.length === 0) {
        await runExistingDeploy(values.agent_id!, deployData);
      } else {
        setPendingAgentDeploy({ mode: 'existing', agentId: values.agent_id!, deployData });
        setValidationResult(validation);
        setValidationModalVisible(true);
      }
    } else {
      const payload: DeployNewLabRequest = {
        scenario_id: scenarioId,
        lab_name: values.lab_name!,
        agent_name: values.agent_name || null,
        ...common,
      };
      if (!validation || validation.warnings.length === 0) {
        await runNewLabDeploy(payload);
      } else {
        setPendingAgentDeploy({ mode: 'new_lab', payload });
        setValidationResult(validation);
        setValidationModalVisible(true);
      }
    }
  };

  // ── Proceed after validation ────────────────────────────────────
  const handleProceedWithDeployment = async () => {
    setValidationModalVisible(false);
    if (pendingAgentDeploy) {
      try {
        if (pendingAgentDeploy.mode === 'existing') {
          await runExistingDeploy(pendingAgentDeploy.agentId, pendingAgentDeploy.deployData);
        } else {
          await runNewLabDeploy(pendingAgentDeploy.payload);
        }
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

  const storePhases = useScenarioStore((s) => s.phases);
  const scenarioPhases = phases ?? storePhases;
  const storeScenarioName = useScenarioStore((s) => s.name);
  const scenarioName = scenarioNameProp ?? storeScenarioName;

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
        scenarioId={scenarioId}
        scenarioName={scenarioName}
        cvConfigured={cvConfigured}
        loadingInterfaces={loadingInterfaces}
        validating={validating}
        deploymentsLoading={deploymentsLoading || newLabDeploying}
        deployDisabled={hasReadinessErrors}
        onFinish={handleDeploy}
      />

      {/* New Local Lab: persistent provisioning status (a toast alone is
          easy to miss, and there's no deployment row to show until the
          agent connects and the auto-fire deploy lands). */}
      {provisioningLab && (
        <Alert
          style={{ marginTop: 12 }}
          type={provisioningLab.state === 'error' ? 'error' : 'info'}
          showIcon
          icon={provisioningLab.state === 'error' ? undefined : <LoadingOutlined spin />}
          closable
          onClose={() => setProvisioningLab(null)}
          message={`Lab "${provisioningLab.name}" — ${provisioningLab.state}`}
          description={
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text style={{ fontSize: 12 }}>
                {provisioningLab.state === 'error'
                  ? provisioningLab.status_detail || 'Provisioning failed.'
                  : 'Deploying automatically once the sensor comes online — this can '
                    + 'take a minute or two.'}
              </Text>
              {typeof provisioningLab.percent === 'number' && provisioningLab.state !== 'error' && (
                <Progress percent={provisioningLab.percent} size="small" status="active" />
              )}
              {provisioningLab.stage && (
                <Text type="secondary" style={{ fontSize: 11 }}>{provisioningLab.stage}</Text>
              )}
            </Space>
          }
        />
      )}

      {/* Cyber Vision provisioning */}
      {cvConfigured && (
        <>
          <Divider style={{ margin: '8px 0', borderColor: '#2a3f54' }} />
          <div>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Title level={5} style={{ color: '#8aa4bc', margin: 0, fontSize: 13 }}>
                Cyber Vision
              </Title>
              <Button
                size="small"
                icon={<ApiOutlined />}
                loading={cvProvisioning}
                onClick={handleProvisionCv}
              >
                Push to Cyber Vision
              </Button>
            </Space>
            {cvProvision && cvProvision.status && cvProvision.status !== 'not_started' && (
              <div style={{ marginTop: 8, fontSize: 12, color: '#8aa4bc' }}>
                <Space size={6} wrap>
                  {cvProvision.status === 'preset_created' && <Tag color="blue">Preset created</Tag>}
                  {cvProvision.status === 'polling' && <Tag color="processing">Discovering devices…</Tag>}
                  {cvProvision.status === 'groups_created' && <Tag color="success">Groups created</Tag>}
                  {cvProvision.status === 'error' && <Tag color="error">Error</Tag>}
                  {cvProvision.preset_label && <span>{cvProvision.preset_label}</span>}
                  {cvProvision.subnet && <Tag>{cvProvision.subnet}</Tag>}
                </Space>
                {cvProvision.status === 'groups_created' && (
                  <div style={{ marginTop: 4 }}>
                    {Object.keys(cvProvision.groups || {}).length} group(s),{' '}
                    {cvProvision.device_count} device(s) assigned
                  </div>
                )}
                {cvProvision.networks && Object.keys(cvProvision.networks).length > 0 && (
                  <Tooltip
                    title={
                      <div style={{ maxHeight: 220, overflowY: 'auto' }}>
                        {Object.entries(cvProvision.networks)
                          .sort(([a], [b]) => a.localeCompare(b))
                          .map(([range, net]) => (
                            <div key={range}>
                              <Tag style={{ marginRight: 4 }}>{range}</Tag>
                              {net.name}
                            </div>
                          ))}
                      </div>
                    }
                  >
                    <div style={{ marginTop: 4, cursor: 'help' }}>
                      {Object.keys(cvProvision.networks).length} network(s) defined
                      {' '}(scenario /16 + zone /24s)
                    </div>
                  </Tooltip>
                )}
                {cvProvision.error && (
                  <div style={{ marginTop: 4, color: '#ff7875' }}>{cvProvision.error}</div>
                )}
              </div>
            )}
          </div>
        </>
      )}

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
        deploymentsLoading={deploymentsLoading || newLabDeploying}
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
