/**
 * Docker Hosts management tab for admin settings
 */

import React, { useEffect, useState } from 'react';
import {
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Switch,
  message,
  Tag,
  Tooltip,
  Popconfirm,
  Alert,
  Typography,
  Card,
  Descriptions,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useDockerHostsStore } from '../../stores/dockerHostsStore';
import type { DockerHost, DockerHostCreate, DockerHostTestResult } from '../../types/docker';

const { Text } = Typography;
const { TextArea } = Input;

const DockerHostsTab: React.FC = () => {
  const {
    hosts,
    isLoading,
    error,
    fetchHosts,
    createHost,
    updateHost,
    deleteHost,
    testConnection,
    clearError,
  } = useDockerHostsStore();

  const [modalVisible, setModalVisible] = useState(false);
  const [editingHost, setEditingHost] = useState<DockerHost | null>(null);
  const [testingHostId, setTestingHostId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<DockerHostTestResult | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchHosts();
  }, [fetchHosts]);

  const handleCreate = () => {
    setEditingHost(null);
    form.resetFields();
    form.setFieldsValue({
      tls_enabled: true,
      is_active: true,
    });
    setModalVisible(true);
  };

  const handleEdit = (host: DockerHost) => {
    setEditingHost(host);
    form.setFieldsValue({
      name: host.name,
      description: host.description,
      docker_api_url: host.docker_api_url,
      tls_enabled: host.tls_enabled,
      default_interface: host.default_interface,
      is_active: host.is_active,
      // Don't populate certificates - they're secret
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteHost(id);
      message.success('Docker host deleted');
    } catch {
      message.error('Failed to delete Docker host');
    }
  };

  const handleTest = async (id: string) => {
    setTestingHostId(id);
    setTestResult(null);
    try {
      const result = await testConnection(id);
      setTestResult(result);
      if (result.success) {
        message.success('Connection successful');
      } else {
        message.error(`Connection failed: ${result.message}`);
      }
    } finally {
      setTestingHostId(null);
    }
  };

  const handleSubmit = async (values: DockerHostCreate) => {
    try {
      if (editingHost) {
        await updateHost(editingHost.id, values);
        message.success('Docker host updated');
      } else {
        await createHost(values);
        message.success('Docker host created');
      }
      setModalVisible(false);
      form.resetFields();
    } catch {
      message.error(editingHost ? 'Failed to update' : 'Failed to create');
    }
  };

  const columns: ColumnsType<DockerHost> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: DockerHost) => (
        <Space>
          <Text strong>{name}</Text>
          {record.tls_enabled && (
            <Tooltip title="TLS Enabled">
              <SafetyCertificateOutlined style={{ color: '#52c41a' }} />
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: 'Docker API URL',
      dataIndex: 'docker_api_url',
      key: 'docker_api_url',
      render: (url: string) => (
        <Text code style={{ fontSize: 12 }}>
          {url}
        </Text>
      ),
    },
    {
      title: 'Default Interface',
      dataIndex: 'default_interface',
      key: 'default_interface',
      render: (iface: string | null) =>
        iface ? <Tag>{iface}</Tag> : <Text type="secondary">Not set</Text>,
    },
    {
      title: 'Status',
      key: 'status',
      render: (_: unknown, record: DockerHost) => (
        <Space>
          {record.is_active ? (
            <Tag color="green">Active</Tag>
          ) : (
            <Tag color="default">Inactive</Tag>
          )}
          {record.has_certificates && (
            <Tooltip title="Has TLS certificates">
              <Tag color="blue">Certs</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: 'Last Connected',
      dataIndex: 'last_connected_at',
      key: 'last_connected_at',
      render: (date: string | null) =>
        date ? (
          <Text type="secondary">{new Date(date).toLocaleString()}</Text>
        ) : (
          <Text type="secondary">Never</Text>
        ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_: unknown, record: DockerHost) => (
        <Space size="small">
          <Tooltip title="Test Connection">
            <Button
              type="text"
              icon={
                testingHostId === record.id ? (
                  <LoadingOutlined spin />
                ) : (
                  <ApiOutlined />
                )
              }
              onClick={() => handleTest(record.id)}
              disabled={testingHostId !== null}
            />
          </Tooltip>
          <Tooltip title="Edit">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Delete Docker host?"
            description="This will not affect any running deployments."
            onConfirm={() => handleDelete(record.id)}
            okText="Delete"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="Delete">
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {error && (
        <Alert
          message="Error"
          description={error}
          type="error"
          showIcon
          closable
          onClose={clearError}
        />
      )}

      {testResult && (
        <Card size="small">
          <Descriptions
            title={
              <Space>
                {testResult.success ? (
                  <CheckCircleOutlined style={{ color: '#52c41a' }} />
                ) : (
                  <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                )}
                Connection Test Result
              </Space>
            }
            size="small"
            column={2}
          >
            <Descriptions.Item label="Status">
              {testResult.success ? (
                <Tag color="green">Connected</Tag>
              ) : (
                <Tag color="red">Failed</Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Message">{testResult.message}</Descriptions.Item>
            {testResult.docker_version && (
              <Descriptions.Item label="Docker Version">
                {testResult.docker_version}
              </Descriptions.Item>
            )}
            {testResult.api_version && (
              <Descriptions.Item label="API Version">
                {testResult.api_version}
              </Descriptions.Item>
            )}
            {testResult.latency_ms && (
              <Descriptions.Item label="Latency">
                {testResult.latency_ms}ms
              </Descriptions.Item>
            )}
          </Descriptions>
          <Button
            size="small"
            onClick={() => setTestResult(null)}
            style={{ marginTop: 8 }}
          >
            Dismiss
          </Button>
        </Card>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text type="secondary">
          Configure remote Docker hosts for traffic generator deployment.
        </Text>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          Add Docker Host
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={hosts}
        rowKey="id"
        loading={isLoading}
        pagination={false}
        locale={{
          emptyText: 'No Docker hosts configured. Add one to get started.',
        }}
      />

      <Modal
        title={editingHost ? 'Edit Docker Host' : 'Add Docker Host'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            tls_enabled: true,
            is_active: true,
          }}
        >
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: 'Please enter a name' }]}
          >
            <Input placeholder="Production Docker Host" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <Input placeholder="Optional description" />
          </Form.Item>

          <Form.Item
            name="docker_api_url"
            label="Docker API URL"
            rules={[{ required: true, message: 'Please enter the Docker API URL' }]}
            extra="e.g., tcp://192.168.1.100:2376"
          >
            <Input placeholder="tcp://hostname:2376" />
          </Form.Item>

          <Form.Item name="default_interface" label="Default Network Interface">
            <Input placeholder="eth0" />
          </Form.Item>

          <Form.Item
            name="tls_enabled"
            label="TLS Enabled"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) =>
              prevValues.tls_enabled !== currentValues.tls_enabled
            }
          >
            {({ getFieldValue }) =>
              getFieldValue('tls_enabled') && (
                <>
                  <Form.Item
                    name="ca_cert"
                    label="CA Certificate"
                    extra={editingHost ? 'Leave empty to keep existing certificate' : undefined}
                  >
                    <TextArea
                      rows={4}
                      placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
                    />
                  </Form.Item>

                  <Form.Item
                    name="client_cert"
                    label="Client Certificate"
                    extra={editingHost ? 'Leave empty to keep existing certificate' : undefined}
                  >
                    <TextArea
                      rows={4}
                      placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
                    />
                  </Form.Item>

                  <Form.Item
                    name="client_key"
                    label="Client Key"
                    extra={editingHost ? 'Leave empty to keep existing key' : undefined}
                  >
                    <TextArea
                      rows={4}
                      placeholder="-----BEGIN RSA PRIVATE KEY-----&#10;...&#10;-----END RSA PRIVATE KEY-----"
                    />
                  </Form.Item>
                </>
              )
            }
          </Form.Item>

          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setModalVisible(false)}>Cancel</Button>
              <Button type="primary" htmlType="submit" loading={isLoading}>
                {editingHost ? 'Update' : 'Create'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
};

export default DockerHostsTab;
