/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Local Sensor Labs tab — app-managed (agent + CV sensor + virtual SPAN) labs
 * provisioned on the PacketArch host itself by the privileged host-agent.
 * Mirrors CmlTab's "Build Lab" UX but on-box and multi-lab.
 */

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  App,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Progress,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  ReloadOutlined,
  PlusOutlined,
  DeleteOutlined,
  CopyOutlined,
  CheckCircleTwoTone,
  CloseCircleTwoTone,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useLocalSensorStore } from '../../stores/localSensorStore';
import type { LocalLabItem } from '../../api/localSensor';

const { Text, Paragraph } = Typography;

const CV_NOT_CONFIGURED_MARKER = "Cyber Vision isn't configured";

const stateColor: Record<string, string> = {
  running: 'success',
  provisioning: 'processing',
  pending: 'default',
  degraded: 'warning',
  error: 'error',
  stopped: 'default',
};

const LocalLabsTab: React.FC = () => {
  const { message, modal } = App.useApp();
  const navigate = useNavigate();
  const {
    hostStatus,
    labs,
    buildResult,
    isLoading,
    isBuilding,
    error,
    fetchHostStatus,
    fetchLabs,
    build,
    teardown,
    clearError,
    clearBuildResult,
  } = useLocalSensorStore();

  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  // Initial load + poll while any lab is mid-provisioning.
  useEffect(() => {
    fetchHostStatus();
    fetchLabs();
  }, [fetchHostStatus, fetchLabs]);

  const anyTransient = labs.some((l) => l.state === 'provisioning' || l.state === 'pending');
  useEffect(() => {
    if (!anyTransient) return;
    const t = setInterval(fetchLabs, 3000);
    return () => clearInterval(t);
  }, [anyTransient, fetchLabs]);

  useEffect(() => {
    if (!error) return;
    if (error.includes(CV_NOT_CONFIGURED_MARKER)) {
      modal.confirm({
        title: 'Cyber Vision is not configured',
        content: error,
        okText: 'Go to Settings',
        onOk: () => navigate('/admin/settings?tab=cyber_vision'),
      });
    } else {
      message.error(error);
    }
    clearError();
  }, [error, message, modal, navigate, clearError]);

  const handleBuild = async () => {
    const values = await form.validateFields();
    const result = await build({
      name: values.name,
      agent_name: values.agent_name || null,
    });
    if (result?.success) {
      setModalOpen(false);
      form.resetFields();
      message.success('Local sensor lab queued — provisioning on the host.');
    }
  };

  const confirmTeardown = (lab: LocalLabItem) => {
    modal.confirm({
      title: `Tear down "${lab.name}"?`,
      content:
        'This stops and removes the agent + CV sensor containers, deletes the ' +
        'virtual SPAN interfaces, and removes the lab and its agent record. This ' +
        'cannot be undone.',
      okText: 'Tear down',
      okButtonProps: { danger: true },
      onOk: async () => {
        const ok = await teardown(lab.lab_id);
        if (ok) message.success(`Lab "${lab.name}" torn down.`);
      },
    });
  };

  const copyToken = (token: string) => {
    navigator.clipboard?.writeText(token);
    message.success('Agent token copied to clipboard.');
  };

  const columns: ColumnsType<LocalLabItem> = [
    {
      title: 'Lab',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, row) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {row.gen_if} → {row.mon_if}
          </Text>
        </Space>
      ),
    },
    {
      title: 'State',
      dataIndex: 'state',
      key: 'state',
      render: (state: string, row) => (
        <Space direction="vertical" size={2} style={{ minWidth: 140 }}>
          <Tag color={stateColor[state] || 'default'}>{state.toUpperCase()}</Tag>
          {state === 'provisioning' && typeof row.percent === 'number' && (
            <Progress percent={row.percent} size="small" status="active" />
          )}
          {row.status_detail && (
            <Text type="secondary" style={{ fontSize: 11 }}>
              {row.status_detail}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Agent',
      key: 'agent',
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Text style={{ fontSize: 13 }}>{row.agent_name || '—'}</Text>
          {row.agent_status && (
            <Tag color={row.agent_status === 'online' ? 'success' : 'default'}>
              {row.agent_status}
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Sensor',
      key: 'sensor',
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Text style={{ fontSize: 13 }}>{row.sensor_serial || '—'}</Text>
          {row.resources && (
            <Space size={4}>
              <Tooltip title="virtual SPAN">
                {row.resources.veth ? <CheckCircleTwoTone twoToneColor="#52c41a" /> : <CloseCircleTwoTone twoToneColor="#ff4d4f" />}
              </Tooltip>
              <Tooltip title="sensor container">
                {row.resources.sensor_running ? <CheckCircleTwoTone twoToneColor="#52c41a" /> : <CloseCircleTwoTone twoToneColor="#ff4d4f" />}
              </Tooltip>
              <Tooltip title="agent container">
                {row.resources.agent_running ? <CheckCircleTwoTone twoToneColor="#52c41a" /> : <CloseCircleTwoTone twoToneColor="#ff4d4f" />}
              </Tooltip>
            </Space>
          )}
        </Space>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      align: 'right',
      render: (_, row) => (
        <Button danger size="small" icon={<DeleteOutlined />} onClick={() => confirmTeardown(row)}>
          Tear down
        </Button>
      ),
    },
  ];

  const unavailable = hostStatus && !hostStatus.available;

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card size="small">
        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
          <Space direction="vertical" size={0}>
            <Text strong>Local Sensor Labs</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Run a traffic agent + Cisco Cyber Vision sensor together on this host,
              wired through an isolated virtual SPAN. No CML lab required.
            </Text>
          </Space>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => { fetchHostStatus(); fetchLabs(); }}>
              Refresh
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              disabled={!!unavailable}
              onClick={() => { clearBuildResult(); setModalOpen(true); }}
            >
              New Local Lab
            </Button>
          </Space>
        </Space>
      </Card>

      {hostStatus && (
        <Alert
          type={hostStatus.available ? 'success' : 'warning'}
          showIcon
          message={hostStatus.available ? 'Host capability available' : 'Host capability unavailable'}
          description={hostStatus.message}
        />
      )}

      {buildResult?.agent_token && (
        <Alert
          type="success"
          showIcon
          closable
          onClose={clearBuildResult}
          message={`Lab "${buildResult.slug}" created — agent token (shown once)`}
          description={
            <Space direction="vertical" style={{ width: '100%' }}>
              <Paragraph code copyable={{ text: buildResult.agent_token }} style={{ marginBottom: 0 }}>
                {buildResult.agent_token}
              </Paragraph>
              <Button size="small" icon={<CopyOutlined />} onClick={() => copyToken(buildResult.agent_token!)}>
                Copy token
              </Button>
            </Space>
          }
        />
      )}

      <Table<LocalLabItem>
        rowKey="lab_id"
        size="small"
        loading={isLoading}
        columns={columns}
        dataSource={labs}
        pagination={false}
        locale={{ emptyText: 'No local labs yet. Click "New Local Lab" to create one.' }}
      />

      <Modal
        title="New Local Sensor Lab"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleBuild}
        okText="Build lab"
        confirmLoading={isBuilding}
        width={640}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Lab name"
            rules={[{ required: true, message: 'Give the lab a name' }]}
          >
            <Input placeholder="e.g. Bakery Sensor Lab" />
          </Form.Item>
          <Form.Item name="agent_name" label="Agent name (optional)">
            <Input placeholder="Defaults to Local-Sensor-<id>" />
          </Form.Item>
          <Alert
            type="info"
            showIcon
            message="Sensor auto-provisioned via Cyber Vision"
            description="Uses the Cyber Vision connection configured under Settings > Cyber Vision to create and enroll the docker sensor automatically. The capture interface is wired automatically."
          />
        </Form>
      </Modal>
    </Space>
  );
};

export default LocalLabsTab;
