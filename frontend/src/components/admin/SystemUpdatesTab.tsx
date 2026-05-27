/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * System / Updates admin tab — one-button platform self-upgrade.
 *
 * Mirrors the agent update UI. The backend restarts mid-upgrade, so the poll
 * deliberately SWALLOWS errors (treating them as "backend restarting") and
 * keeps going until the shared status file reaches a terminal state.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Popconfirm,
  Progress,
  Result,
  Space,
  Spin,
  Steps,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  CloudUploadOutlined,
  ReloadOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { systemApi, type SystemVersion, type UpgradeStatus } from '../../api/system';
import { extractErrorMessage } from '../../utils/errorUtils';

const { Text, Paragraph } = Typography;

const TERMINAL = ['success', 'failed', 'rolled_back'];
const STEP_TITLES = ['Preparing', 'Backing up', 'Building', 'Migrating', 'Starting', 'Verifying'];

const phaseToStep = (phase: string): number => {
  switch (phase) {
    case 'queued':
    case 'preflight':
      return 0;
    case 'backup':
      return 1;
    case 'checkout':
    case 'building':
      return 2;
    case 'migrating':
      return 3;
    case 'starting':
      return 4;
    case 'verifying':
      return 5;
    case 'success':
      return 6;
    default:
      return 0;
  }
};

const SystemUpdatesTab: React.FC = () => {
  const [version, setVersion] = useState<SystemVersion | null>(null);
  const [loadingVersion, setLoadingVersion] = useState(true);
  const [status, setStatus] = useState<UpgradeStatus | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [backendDown, setBackendDown] = useState(false);
  const pollRef = useRef<number | null>(null);

  const stopPoll = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const loadVersion = useCallback(async () => {
    setLoadingVersion(true);
    try {
      setVersion(await systemApi.getVersion());
    } catch (err) {
      message.error(extractErrorMessage(err, 'Failed to load version info'));
    } finally {
      setLoadingVersion(false);
    }
  }, []);

  const poll = useCallback(async () => {
    try {
      const s = await systemApi.getUpgradeStatus();
      setBackendDown(false);
      setStatus(s);
      if ([...TERMINAL, 'idle'].includes(s.status)) {
        stopPoll();
        if (s.status === 'success') void loadVersion();
      }
    } catch {
      // Backend is bouncing as part of its own upgrade — keep polling.
      setBackendDown(true);
    }
  }, [stopPoll, loadVersion]);

  const startPoll = useCallback(() => {
    stopPoll();
    pollRef.current = window.setInterval(() => void poll(), 3000);
  }, [stopPoll, poll]);

  useEffect(() => {
    void loadVersion();
    // Resume an in-flight upgrade if the operator reloaded the page.
    systemApi
      .getUpgradeStatus()
      .then((s) => {
        setStatus(s);
        if (s.status === 'running') startPoll();
      })
      .catch(() => undefined);
    return stopPoll;
  }, [loadVersion, startPoll, stopPoll]);

  const handleUpgrade = async () => {
    setTriggering(true);
    try {
      const s = await systemApi.triggerUpgrade(version?.latest ?? undefined);
      setStatus(s);
      setBackendDown(false);
      startPoll();
      message.success(`Upgrade to ${version?.latest ?? 'latest'} started`);
    } catch (err) {
      message.error(extractErrorMessage(err, 'Failed to start upgrade'));
    } finally {
      setTriggering(false);
    }
  };

  const handleAck = async () => {
    try {
      await systemApi.clearUpgradeStatus();
    } catch {
      /* non-fatal */
    }
    setStatus(null);
    void loadVersion();
  };

  const running = status?.status === 'running';
  const currentStep = status ? phaseToStep(status.phase) : 0;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card
        title={
          <Space>
            <CloudUploadOutlined /> Platform Version
          </Space>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={loadVersion}
            loading={loadingVersion}
            disabled={running}
          >
            Check for updates
          </Button>
        }
      >
        {loadingVersion && !version ? (
          <Spin />
        ) : version ? (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Installed">
                <Text code>{version.current}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Latest release">
                {version.checked ? (
                  version.latest ? (
                    <Text code>{version.latest}</Text>
                  ) : (
                    <Text type="secondary">none found</Text>
                  )
                ) : (
                  <Text type="secondary">could not check (offline?)</Text>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                {version.update_available ? (
                  <Tag color="processing">Update available</Tag>
                ) : version.checked ? (
                  <Tag color="success">Up to date</Tag>
                ) : (
                  <Tag>Unknown</Tag>
                )}
              </Descriptions.Item>
            </Descriptions>

            <Popconfirm
              title={`Upgrade to ${version.latest ?? 'the latest release'}?`}
              description="The platform will back up, rebuild, and restart. Brief downtime is expected; it auto-rolls back if the new version is unhealthy."
              okText="Upgrade now"
              cancelText="Cancel"
              onConfirm={handleUpgrade}
              disabled={running || !version.update_available}
            >
              <Button
                type="primary"
                icon={<CloudUploadOutlined />}
                loading={triggering}
                disabled={running || !version.update_available}
              >
                {version.update_available
                  ? `Upgrade to ${version.latest}`
                  : 'No update available'}
              </Button>
            </Popconfirm>
          </Space>
        ) : (
          <Text type="secondary">Version info unavailable.</Text>
        )}
      </Card>

      {status && status.status !== 'idle' && (
        <Card
          title={
            <Space>
              <SyncOutlined spin={running} /> Upgrade Progress
            </Space>
          }
        >
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {backendDown && running && (
              <Alert
                type="info"
                showIcon
                message="Backend is restarting as part of the upgrade…"
                description="This is expected — the page will reconnect automatically."
              />
            )}

            {status.status === 'success' && (
              <Result
                status="success"
                title="Upgrade complete"
                subTitle={status.message}
                extra={[
                  status.to_version ? (
                    <Tag color="success" key="v">{status.to_version}</Tag>
                  ) : null,
                  <Button type="primary" key="ack" onClick={handleAck}>
                    Done
                  </Button>,
                ]}
              />
            )}

            {(status.status === 'failed' || status.status === 'rolled_back') && (
              <Result
                status="error"
                title={status.status === 'rolled_back' ? 'Upgrade rolled back' : 'Upgrade failed'}
                subTitle={status.error || status.message}
                extra={
                  <Button key="ack" onClick={handleAck}>
                    Dismiss
                  </Button>
                }
              />
            )}

            {running && (
              <>
                <Steps
                  direction="vertical"
                  size="small"
                  current={currentStep}
                  status={status.phase === 'rolling_back' ? 'error' : 'process'}
                  items={STEP_TITLES.map((title, i) => ({
                    title,
                    icon: i === currentStep ? <SyncOutlined spin /> : undefined,
                  }))}
                />
                <Card size="small">
                  <Text type="secondary">{status.message}</Text>
                </Card>
                <Progress
                  percent={Math.round((currentStep / STEP_TITLES.length) * 100)}
                  status="active"
                  showInfo={false}
                />
                {status.to_version && (
                  <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                    Target: <Text code>{status.to_version}</Text>
                  </Paragraph>
                )}
              </>
            )}
          </Space>
        </Card>
      )}
    </Space>
  );
};

export default SystemUpdatesTab;
