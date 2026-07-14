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
  MarkerType,
} from '@xyflow/react';
import type { Node, Edge, Connection, NodeProps } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Alert, App, Button, Card, Checkbox, Divider, Form, Input, Segmented, Select, Space, Tag, Typography } from 'antd';
import { PlusOutlined, RocketOutlined, DeleteOutlined } from '@ant-design/icons';
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

const PROTO_LABEL: Record<string, string> = {
  modbus: 'Modbus TCP', opcua: 'OPC UA', bacnet: 'BACnet/IP', iec104: 'IEC-104',
};

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
  const { message, modal } = App.useApp();
  const {
    status, templates, processModels, presets, isDeploying, error, cmlStatus,
    fetchStatus, fetchTemplates, fetchProcessModels, fetchPresets, author, deployCml, fetchCmlStatus, clearError,
  } = useMimicStore();
  const { labs, fetchLabs } = useLocalSensorStore();
  const [nodes, setNodes, onNodesChange] = useNodesState<PersonaNodeT>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [labSlug, setLabSlug] = React.useState<string | undefined>(undefined);
  const [cellName, setCellName] = React.useState('Authored Cell');
  const [scenarioKey, setScenarioKey] = React.useState<string | undefined>(undefined);
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

  const selectedTemplate = useMemo(
    () => templates.find((t) => t.id === templateId), [templates, templateId]);
  const isClientRole = selectedTemplate?.role_class === 'client';

  // Server protocols the selected device is CERTIFIED to emulate for this deploy
  // target — identity-backed + runtime-supported. Client-role devices get none.
  const protocolOptions = useMemo(() => {
    if (!selectedTemplate || selectedTemplate.role_class === 'client') return [];
    return (selectedTemplate.server_protocols?.[target] ?? [])
      .map((p) => ({ value: p, label: PROTO_LABEL[p] || p }));
  }, [selectedTemplate, target]);

  const onFormChange = (changed: Record<string, unknown>) => {
    // Reset dependent fields so a stale device/protocol can't outlive its parent.
    if ('role' in changed) form.setFieldsValue({ template_id: undefined, protocol: undefined });
    else if ('template_id' in changed) form.setFieldsValue({ protocol: undefined });
  };

  useEffect(() => {
    fetchStatus();
    fetchTemplates();
    fetchProcessModels();
    fetchPresets();
    fetchLabs();
    fetchCmlStatus();
  }, [fetchStatus, fetchTemplates, fetchProcessModels, fetchPresets, fetchLabs, fetchCmlStatus]);

  // Drop an example scenario's devices + poll edges onto the canvas, ready to edit
  // and deploy (on-box or off-box).
  const loadScenario = (key: string) => {
    const preset = presets.find((p) => p.key === key);
    if (!preset) return;
    const build = () => {
      const cols = 3;
      const newNodes: PersonaNodeT[] = preset.personas.map((p, i) => {
        const tpl = templates.find((t) => t.id === p.template_id);
        const proto = (p.protocols?.[0] as { protocol?: string } | undefined)?.protocol ?? null;
        return {
          id: p.device_id,
          type: 'persona',
          position: { x: 70 + (i % cols) * 240, y: 60 + Math.floor(i / cols) * 170 },
          data: {
            name: p.name,
            templateId: p.template_id,
            vendor: tpl?.vendor || '',
            role: tpl?.device_type || '',
            protocol: proto,
            processModelId: p.process_model_id ?? null,
          },
        };
      });
      const newEdges: Edge[] = preset.personas.flatMap((p) =>
        (p.clients || [])
          .filter((c) => c.target_device)
          .map((c) => ({
            id: `e-${p.device_id}-${c.target_device}`,
            source: p.device_id,
            target: c.target_device as string,
            animated: true,
            label: `${PROTO_LABEL[c.protocol] || c.protocol} poll`,
            labelStyle: { fill: '#ddd', fontSize: 10 },
            labelBgStyle: { fill: '#1f1f1f', fillOpacity: 0.85 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#1677ff' },
            style: { stroke: '#1677ff' },
          })),
      );
      setNodes(newNodes);
      setEdges(newEdges);
      setCellName(preset.name.replace(/^Scenario:\s*/, ''));
      setScenarioKey(preset.key);
      message.success(`Loaded "${preset.name}" — ${newNodes.length} device(s). Edit, then Deploy.`);
    };
    if (nodes.length > 0) {
      modal.confirm({
        title: 'Replace the canvas?',
        content: `Loading "${preset.name}" clears the current ${nodes.length} device(s).`,
        okText: 'Load scenario',
        onOk: build,
      });
    } else {
      build();
    }
  };

  useEffect(() => {
    if (!error) return;
    message.error(error);
    clearError();
  }, [error, message, clearError]);

  // A connector = a POLL relationship: the source device polls the target's server.
  const onConnect = useCallback(
    (c: Connection) => {
      const targetNode = nodes.find((n) => n.id === c.target);
      const proto = targetNode?.data.protocol;
      if (!proto) {
        message.warning('A connector is a poll — draw it TO a device that runs a server (has a protocol).');
        return;
      }
      setEdges((eds) => addEdge({
        ...c,
        animated: true,
        label: `${PROTO_LABEL[proto] || proto} poll`,
        labelStyle: { fill: '#ddd', fontSize: 10 },
        labelBgStyle: { fill: '#1f1f1f', fillOpacity: 0.85 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#1677ff' },
        style: { stroke: '#1677ff' },
      }, eds));
    },
    [nodes, setEdges, message],
  );

  // Delete the selected device(s) / connector(s) (and any edge orphaned by a
  // removed device). Backspace/Delete keys also work via the canvas.
  const deleteSelected = useCallback(() => {
    const selNodes = new Set(nodes.filter((n) => n.selected).map((n) => n.id));
    const selEdges = new Set(edges.filter((e) => e.selected).map((e) => e.id));
    if (!selNodes.size && !selEdges.size) {
      message.info('Select a device or connector on the canvas first (click it), then delete.');
      return;
    }
    setNodes((ns) => ns.filter((n) => !selNodes.has(n.id)));
    setEdges((es) => es.filter(
      (e) => !selEdges.has(e.id) && !selNodes.has(e.source) && !selNodes.has(e.target)));
  }, [nodes, edges, setNodes, setEdges, message]);

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
        deleteKeyCode={['Backspace', 'Delete']}
        fitView
      >
        <Background />
        <Controls />
        <Panel position="top-left">
          <Card size="small" title="Build cell" style={{ width: 290 }}>
            <Select
              style={{ width: '100%' }}
              placeholder="⚡ Load an example scenario…"
              value={scenarioKey}
              onChange={loadScenario}
              options={presets.map((p) => ({ value: p.key, label: p.name }))}
            />
            <Divider style={{ margin: '10px 0' }}>or add a device</Divider>
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
              {selectedTemplate && (
                <div style={{ marginTop: -8, marginBottom: 8 }}>
                  {isClientRole ? (
                    <Tag color="purple">Client persona — this role polls its peers (no server)</Tag>
                  ) : protocolOptions.length ? (
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      ✓ Certified server: {protocolOptions.map((o) => o.label).join(', ')} ({target === 'offbox' ? 'off-box' : 'on-box'})
                    </Text>
                  ) : (
                    <Tag color="orange">Not certified as a server {target === 'offbox' ? 'off-box' : 'on-box'} — use as a client</Tag>
                  )}
                </div>
              )}
              <Form.Item name="protocol" tooltip="Blank = a client-only device (an HMI that polls its peers)">
                <Select
                  allowClear
                  disabled={!templateId || isClientRole || protocolOptions.length === 0}
                  placeholder={isClientRole ? 'Client-only (this role polls)' : (templateId ? 'Server protocol (blank = client)' : 'Pick a device first')}
                  options={protocolOptions}
                />
              </Form.Item>
              <Form.Item name="process_model_id" tooltip="Adds live, drifting process values — without one the device answers its identity but reads flat">
                <Select
                  allowClear
                  placeholder="Process model (for live values)"
                  options={processModels.map((m) => ({ value: m, label: m }))}
                />
              </Form.Item>
              <Button block icon={<PlusOutlined />} onClick={addDevice}>
                Add to canvas
              </Button>
            </Form>
            <Divider style={{ margin: '10px 0' }} />
            <Button block danger icon={<DeleteOutlined />} onClick={deleteSelected}>
              Delete selected
            </Button>
            <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 6 }}>
              <b>Connectors = poll relationships.</b> Drag from a device&apos;s right handle to
              another device&apos;s left handle to make the first <i>poll</i> the second (e.g.
              an HMI → a PLC). The edge is labelled with the poll protocol. Select any device or
              connector and press <b>Delete</b> / <b>Backspace</b> (or the button above) to remove it.
            </Text>
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
