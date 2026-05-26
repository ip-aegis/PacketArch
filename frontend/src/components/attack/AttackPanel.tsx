/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * AttackPanel - Container for attack simulation in the right side panel.
 *
 * State machine:
 * 1. No playbook selected -> PlaybookLibrary
 * 2. Playbook selected -> Configurator
 * 3. Configured -> Summary (inject now if deployed, or included in next deploy)
 * 4. Active attack -> KillChainTimeline + controls
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Alert, Button, Modal, Space, Spin, Statistic, Tag, Typography, message } from 'antd';
import {
  DeleteOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  FireOutlined,
  LoadingOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { PanelContainer } from '../common';
import { attacksApi } from '../../api/attacks';
import { useAttackStore } from '../../stores/attackStore';
import AttackPlaybookLibrary from './AttackPlaybookLibrary';
import AttackConfigurator from './AttackConfigurator';
import KillChainTimeline from './KillChainTimeline';
import AttackReportPanel from './AttackReportPanel';
import MitreTechniquePanel from './MitreTechniquePanel';
import type { AttackPlaybook, AttackState } from '../../types/attackPlaybook';

const { Text } = Typography;

type InjectionStatus = 'idle' | 'injecting' | 'polling' | 'confirmed' | 'failed';

interface AttackPanelProps {
  scenarioId: string | null;
  deploymentId?: string;
  isDeployed?: boolean;
  deploymentAgentName?: string;
  deploymentStatus?: string;
  attackState?: AttackState | null;
}

const severityColors: Record<string, string> = {
  critical: '#ff4d4f',
  high: '#fa8c16',
  medium: '#faad14',
  low: '#52c41a',
};

/** Deployment context bar shown at the top of every view */
const DeploymentContextBar: React.FC<{
  isDeployed?: boolean;
  agentName?: string;
  status?: string;
}> = ({ isDeployed, agentName, status }) => {
  const dotColor = isDeployed && status === 'running' ? '#52c41a' : '#4a6a8a';
  const label = isDeployed && agentName
    ? `Deployed on ${agentName}`
    : isDeployed
      ? 'Deployment active'
      : 'No active deployment';

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '5px 8px',
        marginBottom: 8,
        background: '#0d1117',
        borderRadius: 4,
        border: `1px solid ${isDeployed ? '#1a3a2a' : '#1a2332'}`,
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: dotColor,
          display: 'inline-block',
          flexShrink: 0,
          animation: isDeployed ? 'pulse-green 2s ease-in-out infinite' : undefined,
        }}
      />
      <Text style={{ color: isDeployed ? '#8cc8a0' : '#4a6a8a', fontSize: 10 }}>
        {label}
      </Text>
    </div>
  );
};

const AttackPanel: React.FC<AttackPanelProps> = ({
  scenarioId,
  deploymentId,
  isDeployed,
  deploymentAgentName,
  deploymentStatus,
  attackState,
}) => {
  const [view, setView] = useState<'library' | 'configure' | 'summary'>('library');
  const [reportModalOpen, setReportModalOpen] = useState(false);
  // Local fallback playbook fetched by ID when `selectedPlaybook` is
  // null (e.g. after a page refresh, or when the user is viewing an
  // attack that was configured in a previous session). Without this
  // the modal couldn't render the MITRE panel because the playbook
  // structure wasn't available.
  const [modalPlaybook, setModalPlaybook] = useState<AttackPlaybook | null>(null);

  const {
    selectedPlaybook,
    playbookConfig,
    injectionStatus: injectionStatusMap,
    injectionError: injectionErrorMap,
    attackReports,
    isFetchingReport,
    selectPlaybook,
    clearSelection,
    injectAndPoll,
    resetInjection,
    fetchAttackReport,
  } = useAttackStore();

  // Open the report modal and (re)fetch the latest report. The live
  // state already includes `report`, but we fetch via the API to pick
  // up the most recent persisted version when the deployment has
  // already ended.
  const handleViewReport = useCallback(() => {
    if (!scenarioId) return;
    setReportModalOpen(true);
    fetchAttackReport(scenarioId);
  }, [scenarioId, fetchAttackReport]);

  const reportEnvelope = scenarioId ? attackReports[scenarioId] : null;
  const reportLoading = scenarioId ? isFetchingReport[scenarioId] : false;
  // Prefer the freshly-fetched report; otherwise fall back to whatever
  // the live state carried (so the modal works immediately even before
  // the dedicated GET /report call resolves).
  const reportForModal =
    reportEnvelope?.report ?? attackState?.report ?? null;
  const playbookForModal = selectedPlaybook ?? modalPlaybook;

  // When the modal opens for an attack we don't already have a
  // playbook for, fetch its details by ID so the degraded view can
  // still show MITRE coverage + planned stages.
  useEffect(() => {
    if (!reportModalOpen) return;
    const playbookId =
      reportForModal?.playbook_id ?? attackState?.playbook_id;
    if (!playbookId) return;
    if (selectedPlaybook?.playbook_id === playbookId) return;
    if (modalPlaybook?.playbook_id === playbookId) return;
    attacksApi
      .getPlaybook(playbookId)
      .then((pb) => setModalPlaybook(pb))
      .catch(() => {
        /* leave modalPlaybook null — degraded view tolerates this */
      });
  }, [reportModalOpen, reportForModal, attackState, selectedPlaybook, modalPlaybook]);

  // Get per-scenario injection state
  const injectionStatus = scenarioId ? (injectionStatusMap[scenarioId] ?? 'idle') : 'idle';
  const injectionError = scenarioId ? injectionErrorMap[scenarioId] : null;

  // Auto-transition to live timeline when injection is confirmed
  useEffect(() => {
    if (injectionStatus === 'confirmed') {
      message.success(`${selectedPlaybook?.name ?? 'Attack'} injected successfully.`);
    }
  }, [injectionStatus, selectedPlaybook]);

  const handleSelectPlaybook = useCallback(async (playbookId: string) => {
    await selectPlaybook(playbookId);
    setView('configure');
  }, [selectPlaybook]);

  const handleApply = useCallback(() => {
    if (!playbookConfig) return;
    setView('summary');
    message.success(`${selectedPlaybook?.name} will be included in the next deployment.`);
  }, [playbookConfig, selectedPlaybook]);

  const handleRemove = useCallback(() => {
    clearSelection();
    setView('library');
  }, [clearSelection]);

  const handleBack = useCallback(() => {
    clearSelection();
    setView('library');
  }, [clearSelection]);

  const handleInjectNow = useCallback(async () => {
    if (!scenarioId) {
      message.warning('No scenario selected');
      return;
    }
    await injectAndPoll(scenarioId);
  }, [scenarioId, injectAndPoll]);

  const handleRetry = useCallback(() => {
    if (scenarioId) {
      resetInjection(scenarioId);
    }
  }, [scenarioId, resetInjection]);

  // If there's an active attack state, show the live timeline
  if (attackState && (attackState.is_active || attackState.is_completed) && scenarioId) {
    return (
      <PanelContainer>
        <DeploymentContextBar
          isDeployed={isDeployed}
          agentName={deploymentAgentName}
          status={deploymentStatus}
        />

        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
          <ThunderboltOutlined style={{ color: '#ff4d4f' }} />
          <Text style={{ color: '#ffa39e', fontSize: 13, fontWeight: 500 }}>
            {attackState.playbook_name}
          </Text>
        </div>

        <KillChainTimeline
          scenarioId={scenarioId}
          isRunning={attackState.is_active}
          attackState={attackState}
        />

        {/* Stage info */}
        <div style={{ marginTop: 12, padding: 8, background: '#0d1117', borderRadius: 6, border: '1px solid #2a3f54' }}>
          <Text style={{ color: '#6a8caf', fontSize: 10, display: 'block', marginBottom: 4 }}>
            Stage {attackState.current_stage_index + 1} of {attackState.total_stages}
          </Text>
          <Text style={{ color: '#e6f1ff', fontSize: 11 }}>
            {attackState.current_stage_name}
          </Text>
          <div style={{ marginTop: 4 }}>
            <Text style={{ color: '#4a6a8a', fontSize: 10 }}>
              {attackState.actions_completed} actions completed ·{' '}
              {attackState.attack_packets_generated} packets generated
            </Text>
          </div>
        </div>

        {/* After-action report — appears live (rolling stats) and on
            completion. The Modal renders the full per-stage breakdown,
            MITRE coverage, IOCs, and a JSON download. */}
        <Button
          type="default"
          block
          icon={<FileTextOutlined />}
          onClick={handleViewReport}
          style={{
            marginTop: 8,
            borderColor: attackState.is_completed ? '#52c41a' : '#2a3f54',
            color: attackState.is_completed ? '#52c41a' : '#5a9fd4',
          }}
        >
          {attackState.is_completed
            ? 'View After-Action Report'
            : 'View Live Report'}
        </Button>

        <Modal
          title={
            <Space>
              <FileTextOutlined />
              <span>Attack After-Action Report</span>
            </Space>
          }
          open={reportModalOpen}
          onCancel={() => setReportModalOpen(false)}
          width={920}
          footer={null}
          styles={{
            header: { background: '#141428', borderBottom: '1px solid #2d2d52' },
            body: { background: '#0e0e1f', padding: 16, maxHeight: '80vh', overflow: 'auto' },
            content: { background: '#0e0e1f' },
          }}
        >
          {reportLoading && !reportForModal ? (
            <div style={{ padding: 60, textAlign: 'center' }}>
              <Spin />
            </div>
          ) : reportForModal && playbookForModal ? (
            <AttackReportPanel
              report={reportForModal}
              playbook={playbookForModal}
              source={reportEnvelope?.source ?? 'live'}
            />
          ) : (
            <DegradedReportView
              attackState={attackState ?? null}
              playbook={playbookForModal}
            />
          )}
        </Modal>
      </PanelContainer>
    );
  }

  // Summary view — playbook applied but not yet deployed
  if (view === 'summary' && selectedPlaybook && playbookConfig) {
    return (
      <PanelContainer>
        <DeploymentContextBar
          isDeployed={isDeployed}
          agentName={deploymentAgentName}
          status={deploymentStatus}
        />

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <Space size={4}>
            <ThunderboltOutlined style={{ color: '#ff4d4f' }} />
            <Text style={{ color: '#ffa39e', fontSize: 12, fontWeight: 500 }}>
              Attack Configured
            </Text>
          </Space>
          <Button
            type="text"
            size="small"
            icon={<DeleteOutlined />}
            onClick={handleRemove}
            style={{ color: '#ff7875', fontSize: 10 }}
          >
            Remove
          </Button>
        </div>

        <div style={{ padding: 10, background: '#0d1117', borderRadius: 6, border: '1px solid #5c2223' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <Text style={{ color: '#e6f1ff', fontSize: 11, fontWeight: 500 }}>
              {selectedPlaybook.name}
            </Text>
            <Tag
              color={severityColors[selectedPlaybook.severity] || '#ff4d4f'}
              style={{ fontSize: 9, margin: 0, lineHeight: '14px', padding: '0 4px' }}
            >
              {selectedPlaybook.severity.toUpperCase()}
            </Tag>
          </div>
          <Text style={{ color: '#6a8caf', fontSize: 10, display: 'block', marginBottom: 6 }}>
            {selectedPlaybook.stages.length} stages ·{' '}
            Intensity: {Math.round((playbookConfig.intensity ?? 1) * 100)}% ·{' '}
            {playbookConfig.start_mode === 'manual' ? 'Manual start' : 'Auto-start on deploy'}
          </Text>

          {isDeployed ? (
            <>
              <Button
                type="primary"
                danger
                block
                size="small"
                icon={<ThunderboltOutlined />}
                loading={injectionStatus === 'injecting' || injectionStatus === 'polling'}
                disabled={injectionStatus === 'polling'}
                onClick={handleInjectNow}
                style={{ marginTop: 4 }}
              >
                {injectionStatus === 'polling'
                  ? 'Confirming with agent...'
                  : 'Inject Into Running Deployment'}
              </Button>

              {/* Polling status bar */}
              {injectionStatus === 'polling' && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    marginTop: 6,
                    padding: '4px 8px',
                    background: '#111a24',
                    borderRadius: 4,
                    border: '1px solid #1a2f44',
                  }}
                >
                  <LoadingOutlined style={{ color: '#5a9fd4', fontSize: 11 }} />
                  <Text style={{ color: '#5a9fd4', fontSize: 10 }}>
                    Waiting for agent confirmation...
                  </Text>
                </div>
              )}

              {/* Injection error */}
              {injectionStatus === 'failed' && (
                <div style={{ marginTop: 6 }}>
                  <Alert
                    type="error"
                    message={injectionError || 'Injection failed'}
                    showIcon
                    style={{ fontSize: 11, padding: '4px 8px' }}
                    action={
                      <Button
                        size="small"
                        icon={<ReloadOutlined />}
                        onClick={handleRetry}
                        style={{ fontSize: 10 }}
                      >
                        Retry
                      </Button>
                    }
                  />
                </div>
              )}
            </>
          ) : (
            <Tag
              color="volcano"
              style={{ fontSize: 9, lineHeight: '16px' }}
            >
              Included in next deployment
            </Tag>
          )}
        </div>

        <Button
          type="default"
          block
          onClick={() => setView('configure')}
          style={{ marginTop: 8, borderColor: '#5c2223', color: '#ff7875' }}
        >
          Edit Configuration
        </Button>
      </PanelContainer>
    );
  }

  // Configure view
  if (view === 'configure' && selectedPlaybook) {
    return (
      <PanelContainer>
        <DeploymentContextBar
          isDeployed={isDeployed}
          agentName={deploymentAgentName}
          status={deploymentStatus}
        />
        <AttackConfigurator
          onBack={handleBack}
          onApply={handleApply}
          isDeployed={isDeployed}
          onInject={handleInjectNow}
          injectionStatus={injectionStatus}
        />
      </PanelContainer>
    );
  }

  // Library view (default)
  return (
    <PanelContainer>
      <DeploymentContextBar
        isDeployed={isDeployed}
        agentName={deploymentAgentName}
        status={deploymentStatus}
      />
      <AttackPlaybookLibrary scenarioId={scenarioId} onSelect={handleSelectPlaybook} />
    </PanelContainer>
  );
};

/**
 * DegradedReportView — fallback rendered inside the report modal when
 * no per-action telemetry is available. Two common causes:
 *
 *   1. The attack ran on an agent older than v1.44.0 (no `report` field
 *      emitted; nothing was persisted into scenario.attack_history).
 *   2. The attack is brand-new and the orchestrator hasn't completed
 *      its first tick yet — agent v1.44+ but the report is empty.
 *
 * We show whatever aggregate data exists (from AttackState counters)
 * plus the planned MITRE coverage of the playbook so the modal still
 * tells the operator something useful.
 */
const DegradedReportView: React.FC<{
  attackState: AttackState | null;
  playbook: AttackPlaybook | null;
}> = ({ attackState, playbook }) => {
  if (!attackState && !playbook) {
    return (
      <div style={{ padding: 30, color: '#8aa4bc' }}>
        No report data available yet. Try again in a few seconds.
      </div>
    );
  }

  const completed = !!attackState?.is_completed;

  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      <Alert
        type="warning"
        showIcon
        icon={<WarningOutlined />}
        message={
          completed
            ? 'No per-action telemetry was captured for this run'
            : 'Per-action telemetry not yet available'
        }
        description={
          <div style={{ fontSize: 12, color: '#cfd6e4' }}>
            <p style={{ margin: 0 }}>
              The running agent didn't emit the action-level report
              (introduced in agent <code>v1.44.0</code>). Aggregate
              counters from the live state are shown below.
            </p>
            <p style={{ margin: '6px 0 0' }}>
              To capture full reports on future runs:{' '}
              <strong>Settings → Traffic Agents → Build Image</strong>,
              then update each online agent.
            </p>
          </div>
        }
      />

      {attackState && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
            gap: 12,
            padding: 12,
            background: '#141428',
            border: '1px solid #2d2d52',
            borderRadius: 6,
          }}
        >
          <Statistic
            title="Playbook"
            value={attackState.playbook_name || attackState.playbook_id || '—'}
            valueStyle={{ color: '#dde2ec', fontSize: 14 }}
          />
          <Statistic
            title="Status"
            value={
              attackState.is_completed
                ? 'Completed'
                : attackState.is_paused
                ? 'Paused'
                : attackState.is_active
                ? 'Running'
                : 'Idle'
            }
            valueStyle={{ color: '#dde2ec', fontSize: 14 }}
          />
          <Statistic
            title="Stages"
            value={`${attackState.stages_completed} / ${attackState.total_stages}`}
            prefix={<ExperimentOutlined />}
            valueStyle={{ color: '#dde2ec', fontSize: 18 }}
          />
          <Statistic
            title="Actions completed"
            value={attackState.actions_completed}
            valueStyle={{ color: '#dde2ec', fontSize: 18 }}
          />
          <Statistic
            title="Packets emitted"
            value={attackState.attack_packets_generated}
            prefix={<FireOutlined style={{ color: '#fa8c16' }} />}
            valueStyle={{ color: '#dde2ec', fontSize: 18 }}
          />
        </div>
      )}

      {playbook ? (
        <MitreTechniquePanel
          playbook={playbook}
          title="MITRE ATT&CK — planned coverage"
        />
      ) : (
        <div style={{ padding: 20, color: '#8aa4bc', fontSize: 12 }}>
          Playbook details unavailable — MITRE coverage can't be rendered.
        </div>
      )}
    </Space>
  );
};

export default AttackPanel;
