/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Advanced Deployment (multi-sensor topology) tab.
 *
 * Stands up one CV sensor per zone plus a core, with L1-aware per-segment
 * traffic injection so cross-zone flows are seen by multiple sensors — the
 * way a real multi-sensor Cyber Vision deployment observes an OT network.
 * A new deploy target ALONGSIDE the existing single-agent / Local Lab flows,
 * never replacing them.
 */

import React, { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Popconfirm,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  CloudServerOutlined,
  DeploymentUnitOutlined,
  ReloadOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { scenariosApi } from '../../api/scenarios';
import {
  topologyApi,
  type TopologyPreflight,
  type TopologyProvisionResult,
} from '../../api/topology';
import { extractErrorMessage } from '../../utils/errorUtils';

const { Text, Paragraph } = Typography;

const AdvancedDeploymentTab: React.FC = () => {
  const [scenarios, setScenarios] = useState<Array<{ id: string; name: string }>>([]);
  const [scenarioId, setScenarioId] = useState<string | undefined>();
  const [preflight, setPreflight] = useState<TopologyPreflight | null>(null);
  const [preflightError, setPreflightError] = useState<string | null>(null);
  const [members, setMembers] = useState<Array<Record<string, unknown>>>([]);
  const [provisioned, setProvisioned] = useState<TopologyProvisionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [deploying, setDeploying] = useState(false);

  useEffect(() => {
    scenariosApi
      .list({ page_size: 100 })
      .then((r) => setScenarios(r.items.map((s) => ({ id: s.id, name: s.name }))))
      .catch((e) => message.error(extractErrorMessage(e, 'Failed to load scenarios')));
  }, []);

  const loadPreflight = async (id: string) => {
    setPreflight(null);
    setPreflightError(null);
    try {
      setPreflight(await topologyApi.preflight(id));
    } catch (e) {
      setPreflightError(extractErrorMessage(e, 'Topology cannot be derived for this scenario'));
    }
  };

  const loadDeployment = async (id: string) => {
    try {
      const d = await topologyApi.deployment(id);
      setMembers(d.members || []);
    } catch {
      setMembers([]);
    }
  };

  const onSelect = async (id: string) => {
    setScenarioId(id);
    setProvisioned(null);
    setLoading(true);
    await Promise.all([loadPreflight(id), loadDeployment(id)]);
    setLoading(false);
  };

  const onDeploy = async () => {
    if (!scenarioId) return;
    setDeploying(true);
    try {
      const res = await topologyApi.deploy(scenarioId);
      setProvisioned(res);
      message.success(`Provisioning ${res.sensor_count} sensors — watch Local Labs for progress.`);
      await loadDeployment(scenarioId);
    } catch (e) {
      message.error(extractErrorMessage(e, 'Deploy failed'));
    } finally {
      setDeploying(false);
    }
  };

  const onTeardown = async () => {
    if (!scenarioId) return;
    try {
      await topologyApi.teardown(scenarioId);
      message.success('Topology deployment torn down.');
      setProvisioned(null);
      await loadDeployment(scenarioId);
    } catch (e) {
      message.error(extractErrorMessage(e, 'Teardown failed'));
    }
  };

  const deployed = members.length > 0;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Alert
        type="info"
        showIcon
        icon={<DeploymentUnitOutlined />}
        message="Multi-Sensor Topology — Advanced Deployment"
        description={
          <Paragraph style={{ marginBottom: 0 }}>
            Deploys one Cisco IE3500 + Cyber Vision sensor per zone, plus an
            IE9320 core sensor. Traffic is injected L1-aware: any flow that
            crosses a zone&apos;s switch is seen by that zone&apos;s sensor, so
            cross-zone flows appear on multiple sensors — as a real multi-sensor
            CV deployment observes them. This is additive; your existing
            single-agent and Local Lab deploys are unchanged.
          </Paragraph>
        }
      />

      <Card
        title="Scenario"
        extra={
          scenarioId && (
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => onSelect(scenarioId)}
              loading={loading}
            >
              Refresh
            </Button>
          )
        }
      >
        <Select
          showSearch
          placeholder="Select a scenario to deploy as a multi-sensor topology"
          style={{ width: '100%', maxWidth: 520 }}
          value={scenarioId}
          onChange={onSelect}
          optionFilterProp="label"
          options={scenarios.map((s) => ({ value: s.id, label: s.name }))}
        />

        {preflightError && (
          <Alert
            style={{ marginTop: 16 }}
            type="error"
            showIcon
            message="Topology unavailable"
            description={preflightError}
          />
        )}

        {preflight && (
          <div style={{ marginTop: 20 }}>
            <Space size="large" wrap>
              <Statistic
                title="Sensors"
                value={preflight.sensor_count}
                prefix={<CloudServerOutlined />}
                suffix={`(${preflight.switches} zones + core)`}
              />
              <Statistic
                title="Est. RAM"
                value={preflight.ram_estimate_gb}
                suffix="GB"
                valueStyle={preflight.ram_estimate_gb > 8 ? { color: '#faad14' } : undefined}
              />
              <Statistic title="Flow segment plans" value={preflight.flow_plans} />
            </Space>
            {preflight.ram_estimate_gb > 8 && (
              <Alert
                style={{ marginTop: 12 }}
                type="warning"
                showIcon
                icon={<WarningOutlined />}
                message={`This deployment needs ~${preflight.ram_estimate_gb} GB for sensor ring buffers — verify the host has capacity before deploying.`}
              />
            )}
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">SPANs: </Text>
              {preflight.spans.map((s) => (
                <Tag key={s} color={s === 'core' ? 'gold' : 'blue'}>
                  {s}
                </Tag>
              ))}
            </div>
            <div style={{ marginTop: 20 }}>
              <Space>
                <Popconfirm
                  title={`Provision ${preflight.sensor_count} sensors?`}
                  description={`This mints ${preflight.sensor_count} CV sensors (~${preflight.ram_estimate_gb} GB RAM) on this host.`}
                  onConfirm={onDeploy}
                  okText="Deploy"
                  disabled={deployed}
                >
                  <Button type="primary" loading={deploying} disabled={deployed}>
                    Deploy multi-sensor topology
                  </Button>
                </Popconfirm>
                {deployed && (
                  <Popconfirm
                    title="Tear down all sensor labs for this scenario?"
                    onConfirm={onTeardown}
                    okText="Tear down"
                    okButtonProps={{ danger: true }}
                  >
                    <Button danger>Tear down</Button>
                  </Popconfirm>
                )}
              </Space>
            </div>
          </div>
        )}
      </Card>

      {provisioned && (
        <Card title="Agent tokens (shown once)">
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 12 }}
            message="Copy these agent tokens now — they are not shown again."
          />
          <Descriptions bordered size="small" column={1}>
            {provisioned.members.map((m) => (
              <Descriptions.Item key={m.lab_id} label={`${m.span_id} (${m.role})`}>
                <Text code copyable>
                  {m.agent_token}
                </Text>
              </Descriptions.Item>
            ))}
          </Descriptions>
        </Card>
      )}

      <Card title="Deployed sensor labs">
        {deployed ? (
          <Table
            rowKey={(r) => String(r.lab_id)}
            size="small"
            pagination={false}
            dataSource={members}
            columns={[
              { title: 'Lab', dataIndex: 'name' },
              {
                title: 'State',
                dataIndex: 'state',
                render: (s: string) => (
                  <Tag color={s === 'running' ? 'green' : s === 'error' ? 'red' : 'blue'}>{s}</Tag>
                ),
              },
              { title: 'Sensor', dataIndex: 'sensor_serial' },
              { title: 'Inject iface', dataIndex: 'gen_if' },
              {
                title: 'Agent',
                dataIndex: 'agent_status',
                render: (s: string | null) => s || '—',
              },
            ]}
          />
        ) : (
          <Empty description="No topology deployment for this scenario yet" />
        )}
      </Card>
    </Space>
  );
};

export default AdvancedDeploymentTab;
