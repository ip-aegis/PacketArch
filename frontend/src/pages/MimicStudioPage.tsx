/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Mimic Studio — visual authoring canvas for device-emulation cells.
 *
 * Nodes are device personas (template + server protocol + process model); edges
 * are poll relationships (an HMI polling a PLC). Deploy sends the authored graph
 * to POST /mimic/cells/author, which scaffolds each device's data model from its
 * process model and resolves the edges into client bindings.
 */

import React, { useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  Panel,
  addEdge,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
} from '@xyflow/react';
import type { Node, Edge, Connection, NodeProps } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Alert, App, Button, Card, Checkbox, Form, Input, Segmented, Select, Space, Tag, Typography } from 'antd';
import { PlusOutlined, RocketOutlined } from '@ant-design/icons';
import { useMimicStore } from '../stores/mimicStore';
import { useLocalSensorStore } from '../stores/localSensorStore';

const { Title, Text } = Typography;

interface PersonaData extends Record<string, unknown> {
  name: string;
  templateId: string;
  vendor: string;
  role: string; // device_type, e.g. "plc" | "hmi"
  protocol: string | null; // null = client-only (an HMI)
  processModelId: string | null;
}
type PersonaNodeT = Node<PersonaData, 'persona'>;

const protoColor: Record<string, string> = {
  modbus: 'blue',
  opcua: 'geekblue',
  bacnet: 'green',
  iec104: 'volcano',
};

// Acronyms that should stay upper-case in a friendly role label.
const ROLE_ACRONYMS = new Set([
  'plc', 'hmi', 'rtu', 'dcs', 'io', 'ups', 'pdu', 'agv', 'cnc', 'bms', 'hvac',
  'vav', 'ahu', 'crac', 'ied', 'scada', 'rfid',
]);

function friendlyRole(deviceType: string): string {
  return deviceType
    .split('_')
    .map((w) => (ROLE_ACRONYMS.has(w) ? w.toUpperCase() : w.charAt(0).toUpperCase() + w.slice(1)))
    .join(' ');
}

// Map a template's backend protocol names to the protocols the Mimic runtime can
// emulate as a SERVER (enforces the "only protocols the fingerprint supports" rule).
const PROTO_BACKEND_TO_STUDIO: Record<string, string> = {
  modbus_tcp: 'modbus',
  opc_ua: 'opcua',
  bacnet: 'bacnet',
  bacnet_ip: 'bacnet',
  iec104: 'iec104',
};
const PROTO_LABEL: Record<string, string> = {
  modbus: 'Modbus TCP', opcua: 'OPC UA', bacnet: 'BACnet/IP', iec104: 'IEC-104',
};

function emulableProtocols(protocols: string[]): string[] {
  const out: string[] = [];
  for (const p of protocols) {
    const s = PROTO_BACKEND_TO_STUDIO[p];
    if (s && !out.includes(s)) out.push(s);
  }
  return out;
}

const PersonaNode: React.FC<NodeProps<PersonaNodeT>> = ({ data, selected }) => (
  <div
    style={{
      border: selected ? '2px solid #1677ff' : '1px solid #555',
      borderRadius: 8,
      padding: '8px 12px',
      background: '#1f1f1f',
      minWidth: 160,
    }}
  >
    <Handle type="target" position={Position.Left} />
    <div style={{ fontWeight: 600, color: '#fff' }}>{data.name}</div>
    <div style={{ fontSize: 11, color: '#aaa', marginBottom: 4 }}>
      {data.role ? `${friendlyRole(data.role)} · ` : ''}{data.vendor}
    </div>
    <Space size={4}>
      {data.protocol ? (
        <Tag color={protoColor[data.protocol] || 'default'} style={{ margin: 0 }}>
          {data.protocol}
        </Tag>
      ) : (
        <Tag style={{ margin: 0 }}>client</Tag>
      )}
      {data.processModelId && <Tag style={{ margin: 0 }}>process</Tag>}
    </Space>
    <Handle type="source" position={Position.Right} />
  </div>
);

const nodeTypes = { persona: PersonaNode };

function newKey(): string {
  return `d${Date.now().toString(36)}${Math.floor(Math.random() * 1000)}`;
}

const StudioInner: React.FC = () => {
  const { message } = App.useApp();
  const {
    status, templates, processModels, isDeploying, error, cmlStatus,
    fetchStatus, fetchTemplates, fetchProcessModels, author, deployCml, fetchCmlStatus, clearError,
  } = useMimicStore();
  const { labs, fetchLabs } = useLocalSensorStore();
  const [nodes, setNodes, onNodesChange] = useNodesState<PersonaNodeT>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [labSlug, setLabSlug] = React.useState<string | undefined>(undefined);
  const [cellName, setCellName] = React.useState('Authored Cell');
  const [target, setTarget] = React.useState<'onbox' | 'offbox'>('onbox');
  const [withSensor, setWithSensor] = React.useState(false);
  const [form] = Form.useForm();
  const role = Form.useWatch('role', form) as string | undefined;
  const templateId = Form.useWatch('template_id', form) as string | undefined;

  // Roles (device_type) present in the catalog, sorted by frequency so the common
  // ones (PLC, Protection Relay, HMI, …) surface first.
  const roleOptions = useMemo(() => {
    const counts = new Map<string, number>();
    templates.forEach((t) => counts.set(t.device_type, (counts.get(t.device_type) || 0) + 1));
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([dt, n]) => ({ value: dt, label: `${friendlyRole(dt)} (${n})` }));
  }, [templates]);

  // Devices that fill the selected role.
  const deviceOptions = useMemo(
    () => templates
      .filter((t) => t.device_type === role)
      .map((t) => ({ value: t.id, label: `${t.vendor} ${t.model_name}` }))
      .sort((a, b) => a.label.localeCompare(b.label)),
    [templates, role],
  );

  // Server protocols the selected device actually supports (blank = client-only).
  const protocolOptions = useMemo(() => {
    const tpl = templates.find((t) => t.id === templateId);
    return tpl ? emulableProtocols(tpl.protocols).map((p) => ({ value: p, label: PROTO_LABEL[p] || p })) : [];
  }, [templates, templateId]);

  const onFormChange = (changed: Record<string, unknown>) => {
    // Reset dependent fields so a stale device/protocol can't outlive its parent.
    if ('role' in changed) form.setFieldsValue({ template_id: undefined, protocol: undefined });
    else if ('template_id' in changed) form.setFieldsValue({ protocol: undefined });
  };

  useEffect(() => {
    fetchStatus();
    fetchTemplates();
    fetchProcessModels();
    fetchLabs();
    fetchCmlStatus();
  }, [fetchStatus, fetchTemplates, fetchProcessModels, fetchLabs, fetchCmlStatus]);

  useEffect(() => {
    if (!error) return;
    message.error(error);
    clearError();
  }, [error, message, clearError]);

  const onConnect = useCallback(
    (c: Connection) => setEdges((eds) => addEdge({ ...c, animated: true }, eds)),
    [setEdges],
  );

  const addDevice = async () => {
    const v = await form.validateFields();
    const tpl = templates.find((t) => t.id === v.template_id);
    const node: PersonaNodeT = {
      id: newKey(),
      type: 'persona',
      position: { x: 120 + Math.random() * 320, y: 100 + Math.random() * 220 },
      data: {
        name: v.name,
        templateId: v.template_id,
        vendor: tpl?.vendor || '',
        role: tpl?.device_type || v.role || '',
        protocol: v.protocol || null,
        processModelId: v.process_model_id || null,
      },
    };
    setNodes((n) => [...n, node]);
    form.resetFields();
  };

  const deployCell = async () => {
    if (nodes.length === 0) {
      message.warning('Add at least one device to the canvas.');
      return;
    }
    const devices = nodes.map((n) => ({
      key: n.id,
      name: n.data.name,
      template_id: n.data.templateId,
      protocol: n.data.protocol,
      process_model_id: n.data.processModelId,
    }));
    const relationships = edges.map((e) => ({ source: e.source, target: e.target }));
    if (target === 'offbox') {
      const res = await deployCml({ cell_name: cellName, devices, relationships, with_sensor: withSensor });
      if (res) {
        message.success(
          `Off-box lab "${res.lab_title}" launching — ${res.personas.length} persona node(s)` +
          (res.sensor_serial ? ` + CV sensor "${res.sensor_serial}"` : '') + '. Nodes take a few minutes to boot.',
        );
      }
      return;
    }
    if (!labSlug) {
      message.warning('Pick a target lab.');
      return;
    }
    const res = await author({ lab_slug: labSlug, cell_name: cellName, devices, relationships });
    if (res) message.success(`Cell "${cellName}" deployed — ${res.containers.length} device(s) provisioning.`);
  };

  const offbox = target === 'offbox';
  const deployDisabled = offbox ? !cmlStatus?.cml_connected : !status?.host_agent_available;

  return (
    <div style={{ height: 'calc(100vh - 160px)', width: '100%', border: '1px solid #303030', borderRadius: 8 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
      >
        <Background />
        <Controls />
        <Panel position="top-left">
          <Card size="small" title="Add device" style={{ width: 290 }}>
            <Form form={form} layout="vertical" size="small" onValuesChange={onFormChange}>
              <Form.Item name="name" rules={[{ required: true, message: 'Name the device' }]}>
                <Input placeholder="Device name, e.g. Reactor_PLC" />
              </Form.Item>
              <Form.Item name="role" rules={[{ required: true, message: 'Pick a role' }]}>
                <Select
                  showSearch
                  placeholder="Role (PLC, HMI, RTU, …)"
                  options={roleOptions}
                  filterOption={(input, option) =>
                    String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Form.Item>
              <Form.Item name="template_id" rules={[{ required: true, message: 'Pick a device' }]}>
                <Select
                  showSearch
                  disabled={!role}
                  placeholder={role ? `Device (${deviceOptions.length})` : 'Pick a role first'}
                  options={deviceOptions}
                  filterOption={(input, option) =>
                    String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                />
              </Form.Item>
              <Form.Item name="protocol" tooltip="Blank = a client-only device (an HMI that polls its peers)">
                <Select
                  allowClear
                  disabled={!templateId}
                  placeholder={templateId ? 'Server protocol (blank = client)' : 'Pick a device first'}
                  options={protocolOptions}
                  notFoundContent="This device supports no emulable server protocol — use it as a client."
                />
              </Form.Item>
              <Form.Item name="process_model_id">
                <Select
                  allowClear
                  placeholder="Process model"
                  options={processModels.map((m) => ({ value: m, label: m }))}
                />
              </Form.Item>
              <Button block icon={<PlusOutlined />} onClick={addDevice}>
                Add to canvas
              </Button>
            </Form>
          </Card>
        </Panel>
        <Panel position="top-right">
          <Card size="small" title="Deploy" style={{ width: 290 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Segmented
                block
                value={target}
                onChange={(v) => setTarget(v as 'onbox' | 'offbox')}
                options={[
                  { label: 'On-box', value: 'onbox' },
                  { label: 'Off-box (CML)', value: 'offbox' },
                ]}
              />
              {offbox ? (
                <>
                  {!cmlStatus?.cml_connected && (
                    <Alert
                      type="warning"
                      showIcon
                      message="CML not reachable"
                      description="Configure + connect CML (Agents → CML) to deploy off-box."
                    />
                  )}
                  <Checkbox
                    checked={withSensor}
                    disabled={!cmlStatus?.cv_configured}
                    onChange={(e) => setWithSensor(e.target.checked)}
                  >
                    With CV sensor (IOSvL2 SPAN)
                    {!cmlStatus?.cv_configured && (
                      <Text type="secondary" style={{ fontSize: 11 }}> — Cyber Vision not configured</Text>
                    )}
                  </Checkbox>
                </>
              ) : (
                <Select
                  placeholder="Target Local Lab"
                  style={{ width: '100%' }}
                  value={labSlug}
                  onChange={setLabSlug}
                  options={labs.map((l) => ({ value: l.slug, label: `${l.name} (${l.slug})` }))}
                />
              )}
              <Input placeholder="Cell name" value={cellName} onChange={(e) => setCellName(e.target.value)} />
              <Button
                type="primary"
                block
                icon={<RocketOutlined />}
                loading={isDeploying}
                disabled={deployDisabled}
                onClick={deployCell}
              >
                {offbox ? 'Deploy Off-box' : 'Deploy Cell'}
              </Button>
              <Text type="secondary" style={{ fontSize: 11 }}>
                {offbox
                  ? 'Each persona becomes its own bare CML node running the slim native runtime. With the CV sensor, an IOSvL2 SPAN mirrors the OT segment to an auto-provisioned Cyber Vision sensor.'
                  : 'Nodes are devices. Draw an edge from an HMI (no protocol) to a PLC to make it poll. Data models are scaffolded from each device’s process model. Select a node and press Delete to remove it.'}
              </Text>
            </Space>
          </Card>
        </Panel>
      </ReactFlow>
    </div>
  );
};

const MimicStudioPage: React.FC = () => (
  <Space direction="vertical" size="middle" style={{ width: '100%' }}>
    <div>
      <Title level={3} style={{ marginBottom: 4 }}>Mimic Studio</Title>
      <Text type="secondary">
        Author a cell of device personas visually, then deploy it onto a Local Lab&apos;s SPAN.
      </Text>
    </div>
    <ReactFlowProvider>
      <StudioInner />
    </ReactFlowProvider>
  </Space>
);

export default MimicStudioPage;
