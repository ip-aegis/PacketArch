/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * DeploymentCard - Shows status, progress, and controls for a single deployment
 */

import React, { useState, useCallback } from 'react';
import {
  Typography,
  Tag,
  Card,
  Tooltip,
  Button,
  Modal,
  Spin,
  App,
} from 'antd';
import {
  StopOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  QuestionCircleOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import type { UnifiedDeployment } from '../../types/docker';
import { formatElapsedTime } from '../../utils/dateUtils';
import { extractErrorMessage } from '../../utils/errorUtils';
import aiApi from '../../api/ai';
import { useFeatures } from '../../hooks/useFeatures';
import PhaseTimeline from './PhaseTimeline';
import { ScenarioModeBadges } from '../common';

const { Text } = Typography;

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

const DeploymentCard: React.FC<{
  deployment: UnifiedDeployment;
  onStop: (deployment: UnifiedDeployment) => void;
  onRemove: (id: string) => void;
}> = ({ deployment, onStop, onRemove }) => {
  const { message } = App.useApp();
  const { aiEnabled } = useFeatures();
  const config =
    statusConfig[deployment.status] || statusConfig.pending;
  const isRunning = ['running', 'starting', 'stopping'].includes(
    deployment.status,
  );
  const isPerpetual = (deployment.run_mode ?? 'timed') === 'perpetual';
  const targetName = deployment.agent_name;

  const [explainOpen, setExplainOpen] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState<string | null>(null);

  const handleExplainError = useCallback(async () => {
    if (!deployment.error_message) return;
    setExplainOpen(true);
    setExplaining(true);
    setExplanation(null);
    try {
      const result = await aiApi.helpChat(
        `Explain this deployment error and tell me how to fix it:\n\n${deployment.error_message}`,
        'deployment_error'
      );
      setExplanation(result);
    } catch (error: unknown) {
      message.error(extractErrorMessage(error, 'Failed to get explanation'));
      setExplainOpen(false);
    } finally {
      setExplaining(false);
    }
  }, [deployment.error_message, message]);

  return (
    <>
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
              {isPerpetual && (
                <Tag color="purple" style={{ margin: 0 }}>
                  Perpetual
                </Tag>
              )}
              {deployment.attack && (
                <Tag
                  color={deployment.attack.is_active ? 'red' : 'orange'}
                  icon={<ThunderboltOutlined />}
                  style={{ margin: 0 }}
                >
                  {deployment.attack.is_active
                    ? deployment.attack.current_stage_name || 'Attack Active'
                    : 'Attack Configured'}
                </Tag>
              )}
              <ScenarioModeBadges
                modes={{
                  cleanDemoMode: deployment.scenario_modes?.clean_demo_mode,
                  broadcastTrafficEnabled: deployment.scenario_modes?.broadcast_traffic_enabled,
                  cellIsolationMode: deployment.scenario_modes?.cell_isolation_mode,
                }}
              />
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
              <div style={{ marginTop: 4, display: 'flex', alignItems: 'flex-start', gap: 4 }}>
                <Text type="danger" style={{ fontSize: 11, flex: 1 }}>
                  {deployment.error_message}
                </Text>
                {aiEnabled && (
                  <Tooltip title="Explain this error with AI">
                    <Button
                      type="text"
                      size="small"
                      icon={<QuestionCircleOutlined />}
                      onClick={handleExplainError}
                      style={{ color: '#6a8caf', flexShrink: 0, padding: '0 4px', height: 'auto' }}
                    />
                  </Tooltip>
                )}
              </div>
            )}

            {deployment.status === 'running' && (
              <div style={{ marginTop: 8 }}>
                <Text style={{ color: '#6a8caf', fontSize: 11 }}>
                  Running for{' '}
                  {formatElapsedTime(deployment.started_at)}
                </Text>
              </div>
            )}

            {/* Phase timeline */}
            {deployment.status === 'running' && (
              <PhaseTimeline
                scenarioId={deployment.scenario_id}
                isRunning={deployment.status === 'running'}
              />
            )}
          </div>

          <div
            style={{ display: 'flex', gap: 2, marginLeft: 8 }}
          >
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

      {/* Error explanation modal */}
      <Modal
        title={
          <span>
            <RobotOutlined style={{ marginRight: 8 }} />
            Error Explanation
          </span>
        }
        open={explainOpen}
        onCancel={() => setExplainOpen(false)}
        footer={null}
        width={560}
        styles={{
          header: { background: '#141428', borderBottom: '1px solid #2d2d52' },
          body: { background: '#1a1a2e', padding: 20 },
          content: { background: '#141428' },
        }}
      >
        <div
          style={{
            background: '#2a1a1a',
            borderRadius: 6,
            padding: '8px 12px',
            marginBottom: 16,
            border: '1px solid #4a2a2a',
          }}
        >
          <Text style={{ color: '#6b6b8a', fontSize: 11, display: 'block', marginBottom: 4 }}>
            Error
          </Text>
          <Text type="danger" style={{ fontSize: 12 }}>
            {deployment.error_message}
          </Text>
        </div>

        {explaining ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
            <div style={{ marginTop: 8 }}>
              <Text style={{ color: '#6b6b8a', fontSize: 12 }}>Analyzing error...</Text>
            </div>
          </div>
        ) : explanation ? (
          <div
            style={{
              background: '#1e2a3a',
              borderRadius: 6,
              padding: '12px 16px',
              border: '1px solid #2d4a5e',
              borderLeft: '3px solid #1890ff',
            }}
          >
            <Text style={{ color: '#b8c9dc', fontSize: 13, whiteSpace: 'pre-wrap' }}>
              {explanation}
            </Text>
          </div>
        ) : null}
      </Modal>
    </>
  );
};

export default DeploymentCard;
