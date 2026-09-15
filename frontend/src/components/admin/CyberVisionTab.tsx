/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Settings > Cyber Vision: the Cyber Vision Centers this server talks to.
 *
 * One row per center, each with its own URL, SSL setting and both API tokens
 * (classic /api/3.0 and the separate new-UI /cvapi/v1 token store). One center
 * is the default: anything that doesn't name a center uses it. Local labs and
 * provisioned scenarios stay on the center they were created on.
 */

import React, { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Switch,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  SafetyCertificateOutlined,
  StarOutlined,
} from '@ant-design/icons';
import { useCyberVisionStore } from '../../stores/cyberVisionStore';
import { cyberVisionApi, type CVCenter, type CVConnectionStatus } from '../../api/cyberVision';
import { extractErrorMessage } from '../../utils/errorUtils';

const { Text } = Typography;

interface CenterFormValues {
  name?: string;
  url: string;
  api_token?: string;
  new_ui_token?: string;
  ui_username?: string;
  ui_password?: string;
  verify_ssl?: boolean;
  is_default?: boolean;
}

const CyberVisionTab: React.FC = () => {
  const {
    centers,
    centersLoaded,
    fetchCenters,
    createCenter,
    updateCenter,
    makeDefaultCenter,
    deleteCenter,
    testConnection,
    isTesting,
  } = useCyberVisionStore();

  const [form] = Form.useForm<CenterFormValues>();
  const [editing, setEditing] = useState<CVCenter | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [statuses, setStatuses] = useState<Record<string, CVConnectionStatus | 'checking'>>({});
  const [formTest, setFormTest] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    fetchCenters();
  }, [fetchCenters]);

  const checkStatus = async (center: CVCenter) => {
    setStatuses((prev) => ({ ...prev, [center.id]: 'checking' }));
    try {
      const status = await cyberVisionApi.getCenterStatus(center.id);
      setStatuses((prev) => ({ ...prev, [center.id]: status }));
    } catch (error: unknown) {
      setStatuses((prev) => ({
        ...prev,
        [center.id]: {
          connected: false,
          message: extractErrorMessage(error, 'Connection check failed'),
          version: null,
          center_name: null,
        },
      }));
    }
  };

  // Check every center once the list loads.
  useEffect(() => {
    centers.forEach((c) => {
      if (!statuses[c.id]) checkStatus(c);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [centers]);

  const openAdd = () => {
    setEditing(null);
    setFormTest(null);
    form.resetFields();
    form.setFieldsValue({ verify_ssl: false, is_default: centers.length === 0 });
    setModalOpen(true);
  };

  const openEdit = (center: CVCenter) => {
    setEditing(center);
    setFormTest(null);
    form.resetFields();
    form.setFieldsValue({
      name: center.name,
      url: center.url,
      verify_ssl: center.verify_ssl,
      // Secrets are deliberately left blank, but the UI username is returned
      // by the API, so prefill it — otherwise saving an edit would clear it.
      ui_username: center.ui_username ?? undefined,
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) {
        await updateCenter(editing.id, {
          name: values.name || undefined,
          url: values.url,
          api_token: values.api_token || undefined,
          new_ui_token: values.new_ui_token || undefined,
          ui_username: values.ui_username ?? undefined,
          ui_password: values.ui_password || undefined,
          verify_ssl: values.verify_ssl,
        });
        message.success(`Saved ${values.name || editing.name}`);
        setStatuses((prev) => {
          const next = { ...prev };
          delete next[editing.id];
          return next;
        });
      } else {
        const created = await createCenter({
          name: values.name || undefined,
          url: values.url,
          api_token: values.api_token ?? '',
          new_ui_token: values.new_ui_token || undefined,
          ui_username: values.ui_username || undefined,
          ui_password: values.ui_password || undefined,
          verify_ssl: values.verify_ssl ?? false,
          is_default: values.is_default ?? false,
        });
        message.success(`Added ${created.name}`);
      }
      setModalOpen(false);
    } catch (error: unknown) {
      message.error(extractErrorMessage(error, 'Failed to save the Cyber Vision Center'));
    } finally {
      setSaving(false);
    }
  };

  const handleFormTest = async () => {
    const { url, api_token, verify_ssl } = form.getFieldsValue();
    if (!url) {
      message.warning('Enter the Cyber Vision URL first');
      return;
    }
    if (!api_token) {
      if (editing) {
        // No new token typed: test the stored credentials.
        const status = await cyberVisionApi.getCenterStatus(editing.id).catch(() => null);
        if (status) setStatuses((prev) => ({ ...prev, [editing.id]: status }));
        setFormTest({
          success: Boolean(status?.connected),
          message: status?.message || 'Connection check failed',
        });
      } else {
        message.warning('Enter an API token first');
      }
      return;
    }
    setFormTest(await testConnection({ url, api_token, verify_ssl: verify_ssl ?? false }));
  };

  const handleMakeDefault = async (center: CVCenter) => {
    try {
      await makeDefaultCenter(center.id);
      message.success(`${center.name} is now the default Cyber Vision Center`);
    } catch (error: unknown) {
      message.error(extractErrorMessage(error, 'Failed to change the default center'));
    }
  };

  const handleDelete = async (center: CVCenter) => {
    try {
      await deleteCenter(center.id);
      message.success(`Removed ${center.name}`);
    } catch (error: unknown) {
      message.error(extractErrorMessage(error, 'Failed to remove the Cyber Vision Center'));
    }
  };

  const renderStatus = (center: CVCenter) => {
    const status = statuses[center.id];
    if (!status || status === 'checking') return <Tag>Checking…</Tag>;
    return status.connected ? (
      <Tooltip title={status.version ? `API version ${status.version}` : status.message}>
        <Tag icon={<CheckCircleOutlined />} color="success">Connected</Tag>
      </Tooltip>
    ) : (
      <Tooltip title={status.message}>
        <Tag icon={<CloseCircleOutlined />} color="error">Not connected</Tag>
      </Tooltip>
    );
  };

  const columns: ColumnsType<CVCenter> = [
    {
      title: 'Center',
      key: 'name',
      render: (_, c) => (
        <Space direction="vertical" size={0}>
          <Space size={6}>
            <Text strong>{c.name}</Text>
            {c.is_default && <Tag color="blue">Default</Tag>}
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>{c.url}</Text>
        </Space>
      ),
    },
    { title: 'Status', key: 'status', width: 140, render: (_, c) => renderStatus(c) },
    {
      title: 'Credentials',
      key: 'tokens',
      width: 220,
      render: (_, c) => (
        <Space size={4} wrap>
          <Tag color={c.api_token_set ? 'green' : 'red'}>Classic API</Tag>
          <Tooltip title="Optional. Enables the Organization Hierarchy sync.">
            <Tag color={c.new_ui_token_set ? 'green' : 'default'}>New UI API</Tag>
          </Tooltip>
          <Tooltip
            title={
              c.ui_username && c.ui_password_set
                ? `UI login as ${c.ui_username}. Networks are created through the new UI so they appear on the communications map.`
                : 'Not set. On Cyber Vision 5.6 networks created without a UI login do not appear on the communications map.'
            }
          >
            <Tag color={c.ui_username && c.ui_password_set ? 'green' : 'orange'}>UI login</Tag>
          </Tooltip>
        </Space>
      ),
    },
    {
      title: 'In use',
      key: 'usage',
      width: 150,
      render: (_, c) => (
        <Text type="secondary">
          {c.local_labs} lab{c.local_labs === 1 ? '' : 's'}, {c.scenarios} scenario
          {c.scenarios === 1 ? '' : 's'}
        </Text>
      ),
    },
    {
      title: '',
      key: 'actions',
      width: 170,
      render: (_, c) => {
        const inUse = c.local_labs + c.scenarios > 0;
        const deleteBlocked = inUse
          ? 'Tear down the local labs and scenarios on this center first'
          : c.is_default && centers.length > 1
            ? 'Make another center the default first'
            : null;
        return (
          <Space size={0}>
            <Tooltip title="Test connection">
              <Button type="text" icon={<SafetyCertificateOutlined />} onClick={() => checkStatus(c)} />
            </Tooltip>
            <Tooltip title="Edit">
              <Button type="text" icon={<EditOutlined />} onClick={() => openEdit(c)} />
            </Tooltip>
            {!c.is_default && (
              <Tooltip title="Make default">
                <Button type="text" icon={<StarOutlined />} onClick={() => handleMakeDefault(c)} />
              </Tooltip>
            )}
            {deleteBlocked ? (
              <Tooltip title={deleteBlocked}>
                <Button type="text" danger icon={<DeleteOutlined />} disabled />
              </Tooltip>
            ) : (
              <Popconfirm
                title={`Remove ${c.name}?`}
                description="PacketArch will stop using this center. Nothing is deleted on the center itself."
                okText="Remove"
                okButtonProps={{ danger: true }}
                onConfirm={() => handleDelete(c)}
              >
                <Tooltip title="Remove">
                  <Button type="text" danger icon={<DeleteOutlined />} />
                </Tooltip>
              </Popconfirm>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card
        title="Cyber Vision Centers"
        size="small"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>
            Add center
          </Button>
        }
      >
        {centersLoaded && centers.length === 0 ? (
          <Alert
            type="info"
            showIcon
            message="No Cyber Vision Center configured"
            description="Add one to compare scenarios against what Cyber Vision sees, provision presets and groups at deploy time, and build local sensor labs."
          />
        ) : (
          <Table
            rowKey="id"
            size="small"
            loading={!centersLoaded}
            columns={columns}
            dataSource={centers}
            pagination={false}
          />
        )}
        {centers.length > 1 && (
          <Text type="secondary" style={{ display: 'block', marginTop: 12 }}>
            The default center is used whenever you don&apos;t pick one. Local labs and
            provisioned scenarios stay on the center they were created on.
          </Text>
        )}
      </Card>

      <Card title="About Cyber Vision Integration" size="small">
        <Text type="secondary">Cisco Cyber Vision integration allows PacketArch to:</Text>
        <ul style={{ marginTop: 8 }}>
          <li>Pull discovered devices from your OT network</li>
          <li>Compare scenario devices against real network inventory</li>
          <li>View vulnerability data detected by Cyber Vision</li>
          <li>Provision presets, zone groups and networks when a scenario deploys</li>
        </ul>
        <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
          To get an API token, log into your Cyber Vision center and navigate to
          Settings &gt; API &gt; Generate Token. The New UI API token is separate: create it
          from the new UI&apos;s Configuration &gt; API page.
        </Text>
      </Card>

      <Modal
        open={modalOpen}
        title={editing ? `Edit ${editing.name}` : 'Add Cyber Vision Center'}
        onCancel={() => setModalOpen(false)}
        onOk={handleSave}
        okText={editing ? 'Save' : 'Add center'}
        confirmLoading={saving}
        forceRender
      >
        {formTest && (
          <Alert
            style={{ marginBottom: 16 }}
            type={formTest.success ? 'success' : 'error'}
            showIcon
            message={formTest.success ? 'Connection successful' : 'Connection failed'}
            description={formTest.message}
          />
        )}
        {editing && editing.local_labs + editing.scenarios > 0 && (
          <Alert
            style={{ marginBottom: 16 }}
            type="info"
            showIcon
            message="This center is in use, so its URL can't change"
            description="Local labs and provisioned scenarios live on it. To move to a new address, add it as a separate center."
          />
        )}
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Name" tooltip="Shown in pickers. Defaults to the URL's host.">
            <Input placeholder="e.g. Plant A Center" maxLength={100} />
          </Form.Item>
          <Form.Item
            name="url"
            label="Cyber Vision URL"
            rules={[{ required: true, message: 'Enter the Cyber Vision URL' }]}
          >
            <Input
              prefix={<ApiOutlined />}
              placeholder="https://10.10.20.115"
              disabled={Boolean(editing && editing.local_labs + editing.scenarios > 0)}
            />
          </Form.Item>
          <Form.Item
            name="api_token"
            label="API Token"
            rules={editing ? [] : [{ required: true, message: 'Enter the API token' }]}
            extra={
              editing?.api_token_set ? (
                <Text type="success"><CheckCircleOutlined /> Configured. Leave empty to keep it.</Text>
              ) : undefined
            }
          >
            <Input.Password placeholder={editing ? 'Leave empty to keep the existing token' : 'Classic API token'} />
          </Form.Item>
          <Form.Item
            name="new_ui_token"
            label="New UI API Token"
            tooltip="Optional. Cyber Vision's new UI has its own API with a separate token store. Enables mirroring scenario zones into the Organization Hierarchy."
            extra={
              editing?.new_ui_token_set ? (
                <Text type="success"><CheckCircleOutlined /> Configured. Leave empty to keep it.</Text>
              ) : (
                <Text type="secondary">Optional. Organization Hierarchy sync is skipped without it.</Text>
              )
            }
          >
            <Input.Password placeholder="Optional" />
          </Form.Item>
          <Form.Item
            name="ui_username"
            label="UI Username"
            tooltip="Cyber Vision 5.6 only registers a network correctly when it is created through the new UI, and that needs a real UI login rather than an API token. Without it, networks are created on the classic API and will not appear on the communications map."
            extra={
              <Text type="secondary">
                Needed on CV 5.6+ for networks to appear on the communications map.
              </Text>
            }
          >
            <Input placeholder="Optional" autoComplete="off" />
          </Form.Item>
          <Form.Item
            name="ui_password"
            label="UI Password"
            extra={
              editing?.ui_password_set ? (
                <Text type="success"><CheckCircleOutlined /> Configured. Leave empty to keep it.</Text>
              ) : (
                <Text type="secondary">Required alongside the UI username; one without the other is ignored.</Text>
              )
            }
          >
            <Input.Password placeholder="Optional" autoComplete="new-password" />
          </Form.Item>
          <Space size="large">
            <Form.Item name="verify_ssl" label="Verify SSL certificate" valuePropName="checked">
              <Switch checkedChildren="Yes" unCheckedChildren="No" />
            </Form.Item>
            {!editing && centers.length > 0 && (
              <Form.Item name="is_default" label="Make default" valuePropName="checked">
                <Switch />
              </Form.Item>
            )}
          </Space>
          <Button icon={<SafetyCertificateOutlined />} loading={isTesting} onClick={handleFormTest}>
            Test connection
          </Button>
        </Form>
      </Modal>
    </Space>
  );
};

export default CyberVisionTab;
