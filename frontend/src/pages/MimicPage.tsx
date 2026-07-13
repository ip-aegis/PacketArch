/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React, { useEffect, useState } from 'react';
import { App, Alert, Button, Card, Form, Input, Modal, Select, Space, Table, Tag, Tooltip, Typography } from 'antd';
import { ReloadOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useMimicStore } from '../stores/mimicStore';
import { useLocalSensorStore } from '../stores/localSensorStore';
import type { MimicCell, MimicPersona } from '../api/mimic';

const { Title, Text, Paragraph } = Typography;

const stateColor: Record<string, string> = {
  running: 'green',
  degraded: 'orange',
  error: 'red',
  stopped: 'default',
  pending: 'processing',
  provisioning: 'processing',
  unknown: 'default',
};

// Uniquify a preset's personas per deployment so the same preset can run in
// multiple cells; rewrite client target_device references to the new ids.
function uniquify(personas: MimicPersona[]): MimicPersona[] {
  const suffix = Math.random().toString(36).slice(2, 7);
  const idMap: Record<string, string> = {};
  personas.forEach((p) => {
    idMap[p.device_id] = `${p.device_id}-${suffix}`;
  });
  return personas.map((p) => ({
    ...p,
    device_id: idMap[p.device_id],
    scenario_id: `${p.scenario_id}-${suffix}`,
    name: `${p.name}_${suffix}`,
    clients: (p.clients || []).map((c) => ({
      ...c,
      target_device: c.target_device && idMap[c.target_device] ? idMap[c.target_device] : c.target_device,
    })),
  }));
}

const MimicPage: React.FC = () => {
  const { message, modal } = App.useApp();
  const {
    status, cells, presets, isLoading, isDeploying, error,
    fetchStatus, fetchCells, fetchPresets, deploy, teardown, clearError,
  } = useMimicStore();
  const { labs, fetchLabs } = useLocalSensorStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchStatus();
    fetchCells();
    fetchPresets();
    fetchLabs();
  }, [fetchStatus, fetchCells, fetchPresets, fetchLabs]);

  const anyTransient = cells.some((c) => c.state === 'provisioning' || c.state === 'pending' || c.state === 'degraded');
  useEffect(() => {
    if (!anyTransient) return;
    const t = setInterval(fetchCells, 3000);
    return () => clearInterval(t);
  }, [anyTransient, fetchCells]);

  useEffect(() => {
    if (!error) return;
    message.error(error);
    clearError();
  }, [error, message, clearError]);

  const handleDeploy = async () => {
    const values = await form.validateFields();
    const preset = presets.find((p) => p.key === values.preset);
    if (!preset) return;
    const result = await deploy({
      lab_slug: values.lab_slug,
      cell_name: values.cell_name,
      personas: uniquify(preset.personas),
    });
    if (result) {
      setModalOpen(false);
      form.resetFields();
      message.success(`Cell "${values.cell_name}" queued — ${result.containers.length} device(s) provisioning.`);
    }
  };

  const confirmTeardown = (cell: MimicCell) => {
    modal.confirm({
      title: `Tear down "${cell.name}"?`,
      content: 'Stops the personas and removes the hub-bridge. The underlying lab and CV sensor are left untouched.',
      okText: 'Tear down',
      okButtonProps: { danger: true },
      onOk: async () => {
        const ok = await teardown(cell.cell_slug);
        if (ok) message.success(`Cell "${cell.name}" torn down.`);
      },
    });
  };

  const columns: ColumnsType<MimicCell> = [
    { title: 'Cell', dataIndex: 'name', key: 'name', render: (name: string, row) => (
      <Space direction="vertical" size={0}>
        <Text strong>{name}</Text>
        <Text type="secondary" style={{ fontSize: 12 }}>{row.cell_slug}</Text>
      </Space>
    ) },
    { title: 'Lab', dataIndex: 'lab_slug', key: 'lab_slug', render: (s: string | null) => s || '—' },
    { title: 'Devices', dataIndex: 'devices', key: 'devices', render: (devices: string[]) => (
      <Tooltip title={devices.join('\n')}>
        <Tag>{devices.length}</Tag>
      </Tooltip>
    ) },
    { title: 'State', dataIndex: 'state', key: 'state', render: (state: string, row) => (
      <Tooltip title={row.message}>
        <Tag color={stateColor[state] || 'default'}>{state}</Tag>
      </Tooltip>
    ) },
    { title: '', key: 'actions', align: 'right', render: (_v, row) => (
      <Button size="small" danger icon={<DeleteOutlined />} onClick={() => confirmTeardown(row)}>
        Tear down
      </Button>
    ) },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={3} style={{ marginBottom: 4 }}>Mimic — Device Emulation</Title>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          Deploy interactive device personas — real bound protocol servers that answer as
          industrial devices, with live process values — onto a Local Lab&apos;s SPAN, where
          the lab&apos;s Cyber Vision sensor classifies them.
        </Paragraph>
      </div>

      {status && !status.host_agent_available && (
        <Alert type="warning" showIcon message="Host-agent unavailable" description={status.message} />
      )}

      <Card
        title="Cells"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={fetchCells}>Refresh</Button>
            <Button
              type="primary" icon={<PlusOutlined />}
              onClick={() => setModalOpen(true)}
              disabled={!status?.host_agent_available}
            >
              Deploy Cell
            </Button>
          </Space>
        }
      >
        <Table<MimicCell>
          rowKey="cell_slug" size="small" loading={isLoading}
          columns={columns} dataSource={cells} pagination={false}
          locale={{ emptyText: 'No Mimic cells running. Click "Deploy Cell" to add one.' }}
        />
      </Card>

      <Modal
        title="Deploy Mimic Cell" open={modalOpen}
        onCancel={() => setModalOpen(false)} onOk={handleDeploy}
        okText="Deploy" confirmLoading={isDeploying} width={640}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="lab_slug" label="Local Lab" rules={[{ required: true, message: 'Pick a lab to attach to' }]}>
            <Select
              placeholder="Select an existing Local Lab"
              options={labs.map((l) => ({ value: l.slug, label: `${l.name} (${l.slug}) — ${l.state}` }))}
            />
          </Form.Item>
          <Form.Item name="cell_name" label="Cell name" rules={[{ required: true, message: 'Name the cell' }]}>
            <Input placeholder="e.g. Line 1 Emulation" />
          </Form.Item>
          <Form.Item name="preset" label="Device preset" rules={[{ required: true, message: 'Choose a preset' }]}>
            <Select
              placeholder="Choose a device / cell preset"
              optionLabelProp="label"
              options={presets.map((p) => ({
                value: p.key,
                label: p.name,
                title: p.description,
              }))}
            />
          </Form.Item>
          <Text type="secondary">
            Presets deploy proven device configurations. Full per-device authoring is the Mimic Studio canvas.
          </Text>
        </Form>
      </Modal>
    </Space>
  );
};

export default MimicPage;
