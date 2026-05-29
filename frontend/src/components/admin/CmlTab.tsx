/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Cisco Modeling Labs (CML) settings + agent auto-deploy tab.
 */

import React, { useEffect, useMemo, useState } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Switch,
  Space,
  Alert,
  Typography,
  Spin,
  message,
  Tag,
  Select,
  InputNumber,
  Table,
  Popconfirm,
  Divider,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SafetyCertificateOutlined,
  ApiOutlined,
  CloudServerOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { useCmlStore } from '../../stores/cmlStore';
import type { CMLDeploymentItem } from '../../api/cml';

const { Text, Paragraph } = Typography;

const CmlTab: React.FC = () => {
  const {
    settings,
    connectionStatus,
    labs,
    labNodes,
    deployments,
    deployResult,
    isLoading,
    isTesting,
    isLoadingLabs,
    isLoadingNodes,
    isDeploying,
    error,
    fetchSettings,
    fetchStatus,
    updateSettings,
    testConnection,
    fetchLabs,
    fetchLabNodes,
    deploy,
    undeploy,
    buildResult,
    isBuilding,
    buildLab,
    teardownLab,
    fetchDeployments,
    clearError,
    clearDeployResult,
    clearBuildResult,
  } = useCmlStore();

  const [form] = Form.useForm();
  const [deployForm] = Form.useForm();
  const [buildForm] = Form.useForm();
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // Deploy form local state
  const [selectedLab, setSelectedLab] = useState<string | undefined>(undefined);
  const [dropIn, setDropIn] = useState(true);
  const [startNode, setStartNode] = useState(false);
  const [targetNode, setTargetNode] = useState<string | undefined>(undefined);

  // Build-lab form local state
  const [buildStartLab, setBuildStartLab] = useState(false);
  const [tokenClaims, setTokenClaims] = useState<{ serialNumber?: string; centerHost?: string; captureMode?: string } | null>(null);

  useEffect(() => {
    fetchSettings();
    fetchStatus();
    fetchDeployments();
  }, [fetchSettings, fetchStatus, fetchDeployments]);

  useEffect(() => {
    if (settings) {
      form.setFieldsValue({
        cml_url: settings.cml_url,
        cml_username: settings.cml_username,
        cml_verify_ssl: settings.cml_verify_ssl,
        cml_packetarch_server_url: settings.cml_packetarch_server_url,
      });
    }
  }, [settings, form]);

  // Load labs once connected
  useEffect(() => {
    if (connectionStatus?.connected) {
      fetchLabs();
    }
  }, [connectionStatus?.connected, fetchLabs]);

  const handleSave = async (values: Record<string, unknown>) => {
    try {
      await updateSettings({
        cml_url: values.cml_url as string,
        cml_username: values.cml_username as string,
        cml_password: (values.cml_password as string) || undefined,
        cml_verify_ssl: values.cml_verify_ssl as boolean,
        cml_packetarch_server_url: (values.cml_packetarch_server_url as string) || '',
      });
      message.success('CML settings saved');
      form.setFieldValue('cml_password', '');
      fetchStatus();
    } catch {
      message.error('Failed to save settings');
    }
  };

  const handleTestConnection = async () => {
    const url = form.getFieldValue('cml_url');
    const username = form.getFieldValue('cml_username');
    const password = form.getFieldValue('cml_password');
    const verifySsl = form.getFieldValue('cml_verify_ssl');

    if (!url || !username) {
      message.warning('Please enter the CML URL and username');
      return;
    }
    setTestResult(null);

    if (password) {
      const result = await testConnection({ url, username, password, verify_ssl: verifySsl || false });
      setTestResult(result);
      if (result.success) {
        message.success('Connection successful!');
      } else {
        message.error(`Connection failed: ${result.message}`);
      }
    } else {
      await fetchStatus();
      if (connectionStatus?.connected) {
        setTestResult({ success: true, message: 'Connected using stored credentials' });
        message.success('Connection successful!');
      } else {
        setTestResult({ success: false, message: connectionStatus?.message || 'Connection failed' });
        message.error(`Connection failed: ${connectionStatus?.message ?? ''}`);
      }
    }
  };

  const handleLabChange = (labId: string) => {
    setSelectedLab(labId);
    setTargetNode(undefined);
    deployForm.setFieldsValue({ target_node_id: undefined, slot: undefined });
    fetchLabNodes(labId);
    const lab = labs.find((l) => l.id === labId);
    if (lab && !deployForm.getFieldValue('agent_name')) {
      const slug = lab.title.replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-+|-+$/g, '');
      deployForm.setFieldValue('agent_name', `PacketAgent-CML-${slug}`);
    }
  };

  // Selectable data-attach targets (exclude infrastructure nodes)
  const attachableNodes = useMemo(
    () => labNodes.filter((n) => !n.is_infrastructure),
    [labNodes]
  );
  const targetPorts = useMemo(
    () => attachableNodes.find((n) => n.id === targetNode)?.interfaces ?? [],
    [attachableNodes, targetNode]
  );

  const handleDeploy = async (values: Record<string, unknown>) => {
    if (!selectedLab) {
      message.warning('Select a lab first');
      return;
    }
    const dataAttachment =
      !dropIn && values.target_node_id !== undefined && values.slot !== undefined
        ? { target_node_id: values.target_node_id as string, slot: values.slot as number }
        : null;

    if (!dropIn && !dataAttachment) {
      message.warning('Choose a target node and port, or enable "Just drop it into the lab"');
      return;
    }

    const result = await deploy({
      lab_id: selectedLab,
      agent_name: values.agent_name as string,
      data_attachment: dataAttachment,
      start_node: startNode,
      cpus: (values.cpus as number) ?? 2,
      ram_mb: (values.ram_mb as number) ?? 3072,
    });
    if (result?.success) {
      message.success('Agent node deployed');
    }
  };

  // Extract the PROVISIONING_TOKEN from the pasted compose and decode its JWT payload for preview.
  const decodeCompose = (compose: string) => {
    try {
      const token = compose.match(/PROVISIONING_TOKEN\s*[=:]\s*(\S+)/)?.[1];
      if (!token) { setTokenClaims(null); return; }
      const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      const json = JSON.parse(atob(b64 + '='.repeat((4 - (b64.length % 4)) % 4)));
      setTokenClaims({ serialNumber: json.serialNumber, centerHost: json.centerHost, captureMode: json.captureMode });
    } catch {
      setTokenClaims(null);
    }
  };

  const handleBuildLab = async (values: Record<string, unknown>) => {
    const result = await buildLab({
      lab_name: values.lab_name as string,
      agent_name: values.build_agent_name as string,
      sensor_compose: (values.sensor_compose as string).trim(),
      start_lab: buildStartLab,
      sensor_cpus: (values.sensor_cpus as number) ?? 2,
      sensor_ram_mb: (values.sensor_ram_mb as number) ?? 4096,
    });
    if (result?.success) {
      message.success('Lab built');
    }
  };

  const deploymentColumns = [
    { title: 'Agent', dataIndex: 'agent_name', key: 'agent_name' },
    {
      title: 'Status',
      key: 'status',
      render: (_: unknown, r: CMLDeploymentItem) =>
        r.status === 'online' ? (
          <Tag icon={<CheckCircleOutlined />} color="success">online</Tag>
        ) : !r.is_active ? (
          <Tag color="default">deactivated</Tag>
        ) : (
          <Tag color="warning">offline (pending first connect)</Tag>
        ),
    },
    { title: 'CML Node', dataIndex: 'cml_node_label', key: 'cml_node_label', render: (v: string | null) => v || '—' },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, r: CMLDeploymentItem) => (
        <Popconfirm
          title="Undeploy this agent?"
          description="Removes the CML node and deactivates the agent record."
          okText="Undeploy"
          okButtonProps={{ danger: true }}
          onConfirm={async () => {
            const ok = await undeploy({ agent_id: r.agent_id, remove_cml_node: true, deactivate_agent: true });
            if (ok) {
              message.success('Undeployed');
            } else {
              message.error('Undeploy failed');
            }
          }}
        >
          <Button danger size="small">Undeploy</Button>
        </Popconfirm>
      ),
    },
  ];

  if (isLoading && !settings) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">Loading CML settings...</Text>
        </div>
      </div>
    );
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {error && (
        <Alert message="Error" description={error} type="error" showIcon closable onClose={clearError} />
      )}

      {testResult && (
        <Alert
          message={testResult.success ? 'Connection Successful' : 'Connection Failed'}
          description={testResult.message}
          type={testResult.success ? 'success' : 'error'}
          showIcon
          icon={testResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
          closable
          onClose={() => setTestResult(null)}
        />
      )}

      {/* Connection Status */}
      <Card title="Connection Status" size="small">
        <Space>
          {connectionStatus?.connected ? (
            <>
              <Tag icon={<CheckCircleOutlined />} color="success">Connected</Tag>
              {connectionStatus.version && <Text type="secondary">CML Version: {connectionStatus.version}</Text>}
            </>
          ) : (
            <>
              <Tag icon={<CloseCircleOutlined />} color="error">Not Connected</Tag>
              {connectionStatus?.message && <Text type="secondary">{connectionStatus.message}</Text>}
            </>
          )}
        </Space>
      </Card>

      {/* Configuration Form */}
      <Card title="Cisco Modeling Labs Configuration" size="small">
        <Form form={form} layout="vertical" onFinish={handleSave} initialValues={{ cml_verify_ssl: false }}>
          <Form.Item
            name="cml_url"
            label="CML URL"
            tooltip="The URL of your CML controller (e.g., https://10.10.20.230)"
            rules={[{ required: true, message: 'Please enter the CML URL' }]}
          >
            <Input prefix={<ApiOutlined />} placeholder="https://10.10.20.230" />
          </Form.Item>

          <Form.Item
            name="cml_username"
            label="Username"
            rules={[{ required: true, message: 'Please enter the CML username' }]}
          >
            <Input placeholder="admin" autoComplete="off" />
          </Form.Item>

          <Form.Item
            name="cml_password"
            label="Password"
            tooltip="CML password. Leave empty to keep the existing password."
            extra={
              settings?.cml_password_set ? (
                <Text type="success"><CheckCircleOutlined /> Password is configured</Text>
              ) : (
                <Text type="warning">No password configured</Text>
              )
            }
          >
            <Input.Password placeholder="Enter password (leave empty to keep existing)" autoComplete="new-password" />
          </Form.Item>

          <Form.Item
            name="cml_packetarch_server_url"
            label="Agent phone-home URL"
            tooltip="URL the deployed agent connects back to — must be reachable from inside the CML lab. Leave blank to use the site FQDN."
          >
            <Input prefix={<CloudServerOutlined />} placeholder="https://<packetarch-server> (blank = site FQDN)" />
          </Form.Item>

          <Form.Item
            name="cml_verify_ssl"
            label="Verify SSL Certificate"
            valuePropName="checked"
            tooltip="Enable SSL certificate verification. Disable for self-signed certificates."
          >
            <Switch checkedChildren="Yes" unCheckedChildren="No" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={isLoading}>Save Settings</Button>
              <Button onClick={handleTestConnection} loading={isTesting} icon={<SafetyCertificateOutlined />}>
                Test Connection
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {/* Deploy Agent */}
      <Card title="Deploy Agent into a Lab" size="small">
        {!connectionStatus?.connected ? (
          <Text type="secondary">Connect to CML above to enable agent deployment.</Text>
        ) : (
          <Form form={deployForm} layout="vertical" onFinish={handleDeploy} initialValues={{ cpus: 2, ram_mb: 3072 }}>
            <Form.Item label="Lab" required>
              <Select
                placeholder="Select a lab"
                loading={isLoadingLabs}
                value={selectedLab}
                onChange={handleLabChange}
                options={labs.map((l) => ({
                  value: l.id,
                  label: `${l.title} — ${l.state} (${l.node_count} nodes)`,
                }))}
              />
            </Form.Item>

            <Form.Item
              name="agent_name"
              label="Agent name"
              rules={[{ required: true, message: 'Enter an agent name' }]}
            >
              <Input prefix={<RocketOutlined />} placeholder="PacketAgent-CML-..." />
            </Form.Item>

            <Form.Item
              label="Just drop it into the lab"
              tooltip="On: add the node with NO links — wire the management and data interfaces yourself in CML. Off: auto-wire management egress and attach the data interface to a node/port you choose."
            >
              <Switch checked={dropIn} onChange={setDropIn} checkedChildren="Yes" unCheckedChildren="No" />
            </Form.Item>

            {!dropIn && (
              <>
                <Form.Item
                  name="target_node_id"
                  label="Attach data interface (ens3) to node"
                  rules={[{ required: !dropIn, message: 'Select a target node' }]}
                >
                  <Select
                    placeholder="Select a lab node"
                    loading={isLoadingNodes}
                    onChange={(v) => {
                      setTargetNode(v);
                      deployForm.setFieldValue('slot', undefined);
                    }}
                    options={attachableNodes.map((n) => ({
                      value: n.id,
                      label: `${n.label} (${n.node_definition})`,
                    }))}
                  />
                </Form.Item>

                <Form.Item
                  name="slot"
                  label="Target port"
                  rules={[{ required: !dropIn, message: 'Select a port' }]}
                >
                  <Select
                    placeholder="Select a port"
                    disabled={!targetNode}
                    options={targetPorts.map((p) => ({
                      value: p.slot ?? 0,
                      label: `${p.label}${p.is_connected ? ' (connected)' : ''}`,
                      disabled: p.is_connected,
                    }))}
                  />
                </Form.Item>
              </>
            )}

            <Space size="large">
              <Form.Item name="cpus" label="vCPUs"><InputNumber min={1} max={8} /></Form.Item>
              <Form.Item name="ram_mb" label="RAM (MB)"><InputNumber min={1024} max={16384} step={512} /></Form.Item>
              <Form.Item
                label="Start node after deploy"
                tooltip="Off (default): the node is created stopped — boot it yourself in CML. On: boot it immediately so it installs and phones home."
              >
                <Switch checked={startNode} onChange={setStartNode} checkedChildren="Yes" unCheckedChildren="No" />
              </Form.Item>
            </Space>

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={isDeploying} icon={<RocketOutlined />}>
                Deploy Agent
              </Button>
            </Form.Item>
          </Form>
        )}

        {deployResult?.success && (
          <Alert
            style={{ marginTop: 12 }}
            type="success"
            showIcon
            closable
            onClose={clearDeployResult}
            message={`Deployed node "${deployResult.node_label}"`}
            description={
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Text>{deployResult.message}</Text>
                {deployResult.agent_token && (
                  <Paragraph copyable={{ text: deployResult.agent_token }} style={{ marginBottom: 0 }}>
                    <Text strong>Agent token (shown once):</Text> <Text code>{deployResult.agent_token}</Text>
                  </Paragraph>
                )}
                <Text type="secondary">
                  {deployResult.started
                    ? 'The node is booting and installing the agent via cloud-init. It will appear under Settings → Traffic Agents once it phones home (typically 2–4 minutes). It needs outbound internet on first boot to install Docker — if it never connects, check the node console in CML.'
                    : 'The node was created but NOT started. Boot it in CML when ready — on first boot it installs the agent and phones home (needs outbound internet to install Docker), then appears under Settings → Traffic Agents.'}
                </Text>
                {!deployResult.mgmt_wired && !deployResult.data_wired && (
                  <Text type="secondary">No links were created — wire the management (ens2) and data (ens3) interfaces in CML.</Text>
                )}
                {deployResult.warnings?.map((w, i) => (
                  <Text key={i} type="warning">⚠ {w}</Text>
                ))}
              </Space>
            }
          />
        )}
      </Card>

      {/* Build self-contained lab */}
      <Card title="Build Lab (Agent + SPAN switch + CV Sensor)" size="small">
        {!connectionStatus?.connected ? (
          <Text type="secondary">Connect to CML above to enable the lab builder.</Text>
        ) : (
          <Form
            form={buildForm}
            layout="vertical"
            onFinish={handleBuildLab}
            initialValues={{ sensor_cpus: 2, sensor_ram_mb: 4096 }}
          >
            <Text type="secondary">
              Creates a brand-new CML lab: a PacketArch agent + an IOSvL2 switch with a SPAN session +
              a Cisco Cyber Vision sensor host. The agent's traffic is mirrored to the sensor, which
              enrolls into your CV Center and reports it.
            </Text>
            <Form.Item
              name="lab_name"
              label="Lab name"
              style={{ marginTop: 12 }}
              rules={[{ required: true, message: 'Enter a lab name' }]}
            >
              <Input placeholder="e.g. OT Monitoring Demo" />
            </Form.Item>

            <Form.Item
              name="build_agent_name"
              label="Agent name"
              rules={[{ required: true, message: 'Enter an agent name' }]}
            >
              <Input prefix={<RocketOutlined />} placeholder="PacketAgent-..." />
            </Form.Item>

            <Form.Item
              name="sensor_compose"
              label="CV sensor docker-compose YAML"
              tooltip="Paste the full docker-compose CV generates when you deploy a docker sensor (Sensors → deploy). PacketArch reads the serial, registry, and provisioning token from it. Each token is single-use for one serial — generate a fresh one per lab."
              rules={[{ required: true, message: 'Paste the CV docker-compose YAML' }]}
            >
              <Input.TextArea
                rows={8}
                placeholder={'services:\n  ccv-sensor-1:\n    image: 10.10.20.115:443/sensor\n    environment:\n      - SERIAL_NUMBER=...\n      - PROVISIONING_TOKEN=eyJ...'}
                onChange={(e) => decodeCompose(e.target.value)}
              />
            </Form.Item>

            {tokenClaims && (
              <Alert
                type="info"
                showIcon
                style={{ marginBottom: 12 }}
                message="Token decoded"
                description={
                  <Space size="large" wrap>
                    <Text>Serial: <Text code>{tokenClaims.serialNumber || '—'}</Text></Text>
                    <Text>Center: <Text code>{tokenClaims.centerHost || '—'}</Text></Text>
                    <Text>Capture: <Text code>{tokenClaims.captureMode || '—'}</Text></Text>
                  </Space>
                }
              />
            )}

            <Space size="large">
              <Form.Item name="sensor_cpus" label="Sensor vCPUs"><InputNumber min={1} max={8} /></Form.Item>
              <Form.Item name="sensor_ram_mb" label="Sensor RAM (MB)"><InputNumber min={1024} max={16384} step={512} /></Form.Item>
              <Form.Item
                label="Start lab after build"
                tooltip="Off (default): the lab is created stopped — start it in CML when ready. On: start it immediately so the agent + sensor install and enroll."
              >
                <Switch checked={buildStartLab} onChange={setBuildStartLab} checkedChildren="Yes" unCheckedChildren="No" />
              </Form.Item>
            </Space>

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={isBuilding} icon={<CloudServerOutlined />}>
                Build Lab
              </Button>
            </Form.Item>
          </Form>
        )}

        {buildResult?.success && (
          <Alert
            style={{ marginTop: 12 }}
            type="success"
            showIcon
            closable
            onClose={clearBuildResult}
            message="Lab built"
            description={
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Text>{buildResult.message}</Text>
                <Text type="secondary">
                  Created: agent + IOSvL2 SPAN switch + CV sensor (serial <Text code>{buildResult.sensor_serial}</Text>),
                  plus external connector + management switch.
                </Text>
                {buildResult.agent_token && (
                  <Paragraph copyable={{ text: buildResult.agent_token }} style={{ marginBottom: 0 }}>
                    <Text strong>Agent token (shown once):</Text> <Text code>{buildResult.agent_token}</Text>
                  </Paragraph>
                )}
                <Text type="secondary">
                  On first boot the agent installs + phones home, and the sensor pulls its image from the
                  CV Center registry and ZTP-enrolls. Both need outbound reach to the Center / internet.
                </Text>
                {buildResult.warnings?.map((w, i) => (
                  <Text key={i} type="warning">⚠ {w}</Text>
                ))}
                {buildResult.lab_id && (
                  <Popconfirm
                    title="Tear down this lab?"
                    description="Stops, wipes, and deletes the entire lab (agent, switch, sensor)."
                    okText="Teardown"
                    okButtonProps={{ danger: true }}
                    onConfirm={async () => {
                      const ok = await teardownLab({ lab_id: buildResult.lab_id!, agent_id: buildResult.agent_id });
                      if (ok) { message.success('Lab torn down'); clearBuildResult(); }
                      else { message.error('Teardown failed'); }
                    }}
                  >
                    <Button danger size="small" style={{ marginTop: 8 }}>Teardown lab</Button>
                  </Popconfirm>
                )}
              </Space>
            }
          />
        )}
      </Card>

      {/* Deployments */}
      <Card
        title="CML Deployments"
        size="small"
        extra={<Button size="small" onClick={fetchDeployments}>Refresh</Button>}
      >
        <Table
          rowKey="agent_id"
          size="small"
          dataSource={deployments}
          columns={deploymentColumns}
          pagination={false}
          locale={{ emptyText: 'No CML-deployed agents yet' }}
        />
      </Card>

      <Divider />

      {/* Info Card */}
      <Card title="About CML Integration" size="small">
        <Text type="secondary">Cisco Modeling Labs integration lets PacketArch:</Text>
        <ul style={{ marginTop: 8 }}>
          <li>Connect to a CML controller and browse its labs</li>
          <li>Auto-deploy a fully configured remote traffic agent into a lab (zero-touch via cloud-init)</li>
          <li>Wire the agent's data interface into a lab segment, or just drop it in to wire later</li>
          <li>Tear down deployed agents and their CML nodes</li>
        </ul>
        <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
          Deployed nodes are stock Ubuntu 24.04 cloud nodes. The agent installs itself on first boot,
          which requires outbound internet (to install Docker) and reachability to the PacketArch
          phone-home URL.
        </Text>
      </Card>
    </Space>
  );
};

export default CmlTab;
