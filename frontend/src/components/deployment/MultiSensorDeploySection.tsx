/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Multi-sensor topology deploy — the "Advanced" mode of the canvas Deploy
 * panel. Provisions one Cisco IE3500 + CV sensor per zone plus an IE9320 core
 * sensor, then (when all are ready) deploys the scenario to the core lab's
 * agent as the single conductor THROUGH the normal deploy pipeline — so the
 * scenario shows active, live traffic flows, and CV gets its preset + zone
 * groups + org hierarchy, exactly like a normal deploy.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Checkbox,
  Popconfirm,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { CloudServerOutlined, WarningOutlined } from '@ant-design/icons';
import {
  topologyApi,
  type TopologyPreflight,
  type TopologyDeployment,
} from '../../api/topology';
import { deploymentsApi } from '../../api/deployments';
import { extractErrorMessage } from '../../utils/errorUtils';

const { Text, Paragraph } = Typography;

interface Props {
  scenarioId: string;
  cvConfigured?: boolean;
}

const phaseTag = (phase?: string | null) => {
  const map: Record<string, { color: string; label: string }> = {
    active: { color: 'green', label: 'Active — injecting' },
    deploying: { color: 'blue', label: 'Deploying conductor…' },
    provisioning: { color: 'gold', label: 'Provisioning sensors…' },
    none: { color: 'default', label: 'Not deployed' },
  };
  const m = map[phase || 'none'] || map.none;
  return <Tag color={m.color}>{m.label}</Tag>;
};

const MultiSensorDeploySection: React.FC<Props> = ({ scenarioId, cvConfigured }) => {
  const [preflight, setPreflight] = useState<TopologyPreflight | null>(null);
  const [preflightError, setPreflightError] = useState<string | null>(null);
  const [deployment, setDeployment] = useState<TopologyDeployment | null>(null);
  const [provisionCv, setProvisionCv] = useState<boolean>(!!cvConfigured);
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<number | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      setDeployment(await topologyApi.deployment(scenarioId));
    } catch {
      /* leave as-is */
    }
  }, [scenarioId]);

  const loadPreflight = useCallback(async () => {
    setPreflightError(null);
    try {
      setPreflight(await topologyApi.preflight(scenarioId));
    } catch (e) {
      setPreflightError(extractErrorMessage(e, 'Topology cannot be derived for this scenario'));
    }
  }, [scenarioId]);

  useEffect(() => {
    loadPreflight();
    loadStatus();
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [loadPreflight, loadStatus]);

  // Poll while a deployment is in flight (provisioning/deploying).
  const deployed = (deployment?.sensor_count ?? 0) > 0;
  const phase = deployment?.phase;
  useEffect(() => {
    const inFlight = deployed && phase !== 'active';
    if (inFlight && !pollRef.current) {
      pollRef.current = window.setInterval(loadStatus, 5000);
    } else if (!inFlight && pollRef.current) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, [deployed, phase, loadStatus]);

  const onDeploy = async () => {
    setBusy(true);
    try {
      const res = await topologyApi.deploy(scenarioId, provisionCv);
      message.success(
        `Provisioning ${res.sensor_count} sensors — the conductor deploys automatically when they're ready.`,
      );
      await loadStatus();
    } catch (e) {
      message.error(extractErrorMessage(e, 'Deploy failed'));
    } finally {
      setBusy(false);
    }
  };

  const onTeardown = async () => {
    setBusy(true);
    try {
      // Unified teardown: tears down the labs AND deletes the Cyber Vision
      // preset/groups/networks/org-hierarchy (topologyApi.teardown alone does
      // not clean the CV objects).
      await deploymentsApi.teardownScenario(scenarioId);
      message.success('Multi-sensor deployment torn down and Cyber Vision cleaned up.');
      await loadStatus();
    } catch (e) {
      message.error(extractErrorMessage(e, 'Teardown failed'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Paragraph type="secondary" style={{ marginBottom: 0, fontSize: 12 }}>
        Deploys one Cisco IE3500 + CV sensor per zone plus an IE9320 core sensor.
        Cross-zone flows are injected so multiple sensors see them — as a real
        multi-sensor Cyber Vision deployment would. Auto-runs the normal CV
        provisioning (preset, zone groups, org hierarchy).
      </Paragraph>

      {preflightError && (
        <Alert type="error" showIcon message="Topology unavailable" description={preflightError} />
      )}

      {!deployed && preflight && (
        <>
          <Space size="large" wrap>
            <Statistic
              title="Sensors"
              value={preflight.sensor_count}
              prefix={<CloudServerOutlined />}
              suffix={`(${preflight.switches} zones + core)`}
            />
            <Statistic title="Est. RAM" value={preflight.ram_estimate_gb} suffix="GB" />
          </Space>
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>SPANs: </Text>
            {preflight.spans.map((s) => (
              <Tag key={s} color={s === 'core' ? 'gold' : 'blue'}>{s}</Tag>
            ))}
          </div>
          {preflight.ram_estimate_gb > 8 && (
            <Alert
              type="warning"
              showIcon
              icon={<WarningOutlined />}
              message={`Needs ~${preflight.ram_estimate_gb} GB for sensor ring buffers — verify host capacity.`}
            />
          )}
          <Checkbox
            checked={provisionCv}
            disabled={!cvConfigured}
            onChange={(e) => setProvisionCv(e.target.checked)}
          >
            Provision Cyber Vision {cvConfigured ? '' : '(configure CV in Settings first)'}
          </Checkbox>
          <Popconfirm
            title={`Provision ${preflight.sensor_count} sensors?`}
            description={`Mints ${preflight.sensor_count} CV sensors (~${preflight.ram_estimate_gb} GB RAM) and deploys the conductor when ready.`}
            onConfirm={onDeploy}
            okText="Deploy"
          >
            <Button type="primary" block loading={busy}>
              Deploy multi-sensor topology
            </Button>
          </Popconfirm>
        </>
      )}

      {deployed && (
        <>
          <Space>
            <Text strong>Status:</Text>
            {phaseTag(phase)}
            {phase !== 'active' && <Spin size="small" />}
          </Space>
          <Table
            rowKey={(r) => String(r.lab_id)}
            size="small"
            pagination={false}
            dataSource={deployment?.members || []}
            columns={[
              { title: 'Sensor lab', dataIndex: 'name' },
              {
                title: 'State',
                dataIndex: 'state',
                render: (s: string) => (
                  <Tag color={s === 'running' ? 'green' : s === 'error' ? 'red' : 'blue'}>{s}</Tag>
                ),
              },
              { title: 'Inject iface', dataIndex: 'gen_if' },
            ]}
          />
          <Popconfirm
            title="Tear down all sensor labs for this scenario?"
            description="Stops the conductor, removes the deployment, and deletes all sensor labs."
            onConfirm={onTeardown}
            okText="Tear down"
            okButtonProps={{ danger: true }}
          >
            <Button danger block loading={busy}>Tear down multi-sensor deployment</Button>
          </Popconfirm>
        </>
      )}
    </Space>
  );
};

export default MultiSensorDeploySection;
