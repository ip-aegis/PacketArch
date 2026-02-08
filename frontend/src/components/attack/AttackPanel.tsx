/**
 * AttackPanel - Container for attack simulation in the right side panel.
 *
 * State machine:
 * 1. No playbook selected → PlaybookLibrary
 * 2. Playbook selected → Configurator
 * 3. Configured → Summary (included in next deployment)
 * 4. Active attack → KillChainTimeline + controls
 */

import React, { useState, useCallback } from 'react';
import { Button, Space, Tag, Typography, notification } from 'antd';
import { DeleteOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { PanelContainer } from '../common';
import { useAttackStore } from '../../stores/attackStore';
import AttackPlaybookLibrary from './AttackPlaybookLibrary';
import AttackConfigurator from './AttackConfigurator';
import KillChainTimeline from './KillChainTimeline';

const { Text } = Typography;

interface AttackPanelProps {
  scenarioId: string | null;
}

const severityColors: Record<string, string> = {
  critical: '#ff4d4f',
  high: '#fa8c16',
  medium: '#faad14',
  low: '#52c41a',
};

const AttackPanel: React.FC<AttackPanelProps> = ({ scenarioId }) => {
  const [view, setView] = useState<'library' | 'configure' | 'summary'>('library');

  const {
    selectedPlaybook,
    playbookConfig,
    attackState,
    selectPlaybook,
    clearSelection,
  } = useAttackStore();

  const handleSelectPlaybook = useCallback(async (playbookId: string) => {
    await selectPlaybook(playbookId);
    setView('configure');
  }, [selectPlaybook]);

  const handleApply = useCallback(() => {
    if (!playbookConfig) return;
    // Config is stored in the attack store, DeploymentPanel will include it
    setView('summary');
    notification.success({
      message: 'Attack playbook applied',
      description: `${selectedPlaybook?.name} will be included in the next deployment.`,
      duration: 3,
    });
  }, [playbookConfig, selectedPlaybook]);

  const handleRemove = useCallback(() => {
    clearSelection();
    setView('library');
  }, [clearSelection]);

  const handleBack = useCallback(() => {
    clearSelection();
    setView('library');
  }, [clearSelection]);

  // If there's an active attack state, show the live timeline
  if (attackState && (attackState.is_active || attackState.is_completed) && scenarioId) {
    return (
      <PanelContainer>
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
          <Tag
            color="volcano"
            style={{ fontSize: 9, lineHeight: '16px' }}
          >
            Included in next deployment
          </Tag>
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
        <AttackConfigurator onBack={handleBack} onApply={handleApply} />
      </PanelContainer>
    );
  }

  // Library view (default)
  return (
    <PanelContainer>
      <AttackPlaybookLibrary scenarioId={scenarioId} onSelect={handleSelectPlaybook} />
    </PanelContainer>
  );
};

export default AttackPanel;
