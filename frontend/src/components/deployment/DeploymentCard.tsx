/**
 * DeploymentCard - Shows status, progress, and controls for a single deployment
 */

import React, { useEffect, useState } from 'react';
import {
  Typography,
  Tag,
  Progress,
  Card,
  Tooltip,
  Button,
} from 'antd';
import {
  StopOutlined,
  DeleteOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  RocketOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { UnifiedDeployment } from '../../types/docker';
import { formatElapsedTime } from '../../utils/dateUtils';
import PhaseTimeline from './PhaseTimeline';

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

          {/* Phase timeline for agent deployments */}
          {isAgent && deployment.status === 'running' && (
            <PhaseTimeline
              scenarioId={deployment.scenario_id}
              isRunning={deployment.status === 'running'}
            />
          )}
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

export default DeploymentCard;
