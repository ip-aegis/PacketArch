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
import { Alert, Button, Space, Tag, Typography, message } from 'antd';
import {
  DeleteOutlined,
  LoadingOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { PanelContainer } from '../common';
import { useAttackStore } from '../../stores/attackStore';
import AttackPlaybookLibrary from './AttackPlaybookLibrary';
import AttackConfigurator from './AttackConfigurator';
import KillChainTimeline from './KillChainTimeline';
import type { AttackState } from '../../types/attackPlaybook';

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

  const {
    selectedPlaybook,
    playbookConfig,
    injectionStatus: injectionStatusMap,
    injectionError: injectionErrorMap,
    selectPlaybook,
    clearSelection,
    injectAndPoll,
    resetInjection,
  } = useAttackStore();

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

export default AttackPanel;
