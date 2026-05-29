/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Cyber Vision settings tab for admin settings page
 */

import React, { useEffect, useState } from 'react';
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
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SafetyCertificateOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { useCyberVisionStore } from '../../stores/cyberVisionStore';

const { Text } = Typography;

const CyberVisionTab: React.FC = () => {
  const {
    settings,
    connectionStatus,
    isLoading,
    isTesting,
    error,
    fetchSettings,
    fetchStatus,
    updateSettings,
    testConnection,
    clearError,
  } = useCyberVisionStore();

  const [form] = Form.useForm();
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  useEffect(() => {
    fetchSettings();
    fetchStatus();
  }, [fetchSettings, fetchStatus]);

  useEffect(() => {
    if (settings) {
      form.setFieldsValue({
        cyber_vision_url: settings.cyber_vision_url,
        cyber_vision_verify_ssl: settings.cyber_vision_verify_ssl,
      });
    }
  }, [settings, form]);

  const handleSave = async (values: {
    cyber_vision_url: string;
    cyber_vision_api_token?: string;
    cyber_vision_verify_ssl?: boolean;
  }) => {
    try {
      await updateSettings({
        cyber_vision_url: values.cyber_vision_url,
        cyber_vision_api_token: values.cyber_vision_api_token || undefined,
        cyber_vision_verify_ssl: values.cyber_vision_verify_ssl,
      });
      message.success('Cyber Vision settings saved');
      // Clear the API token field after save (it's stored encrypted)
      form.setFieldValue('cyber_vision_api_token', '');
      // Refresh status
      fetchStatus();
    } catch {
      message.error('Failed to save settings');
    }
  };

  const handleTestConnection = async () => {
    const url = form.getFieldValue('cyber_vision_url');
    const token = form.getFieldValue('cyber_vision_api_token');
    const verifySsl = form.getFieldValue('cyber_vision_verify_ssl');

    if (!url) {
      message.warning('Please enter a Cyber Vision URL');
      return;
    }

    // If no new token entered, use existing (test with stored credentials)
    if (!token && !settings?.cyber_vision_api_token_set) {
      message.warning('Please enter an API token');
      return;
    }

    setTestResult(null);

    // If we have a new token, test with that
    if (token) {
      const result = await testConnection({
        url,
        api_token: token,
        verify_ssl: verifySsl || false,
      });
      setTestResult(result);
      if (result.success) {
        message.success('Connection successful!');
      } else {
        message.error(`Connection failed: ${result.message}`);
      }
    } else {
      // Test with stored credentials via status endpoint
      await fetchStatus();
      if (connectionStatus?.connected) {
        setTestResult({ success: true, message: 'Connected using stored credentials' });
        message.success('Connection successful!');
      } else {
        setTestResult({ success: false, message: connectionStatus?.message || 'Connection failed' });
        message.error(`Connection failed: ${connectionStatus?.message}`);
      }
    }
  };

  if (isLoading && !settings) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">Loading Cyber Vision settings...</Text>
        </div>
      </div>
    );
  }

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
              <Tag icon={<CheckCircleOutlined />} color="success">
                Connected
              </Tag>
              {connectionStatus.version && (
                <Text type="secondary">API Version: {connectionStatus.version}</Text>
              )}
            </>
          ) : (
            <>
              <Tag icon={<CloseCircleOutlined />} color="error">
                Not Connected
              </Tag>
              {connectionStatus?.message && (
                <Text type="secondary">{connectionStatus.message}</Text>
              )}
            </>
          )}
        </Space>
      </Card>

      {/* Configuration Form */}
      <Card title="Cyber Vision Configuration" size="small">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            cyber_vision_verify_ssl: false,
          }}
        >
          <Form.Item
            name="cyber_vision_url"
            label="Cyber Vision URL"
            tooltip="The URL of your Cisco Cyber Vision center (e.g., https://10.10.20.115)"
            rules={[{ required: true, message: 'Please enter the Cyber Vision URL' }]}
          >
            <Input
              prefix={<ApiOutlined />}
              placeholder="https://10.10.20.115"
            />
          </Form.Item>

          <Form.Item
            name="cyber_vision_api_token"
            label="API Token"
            tooltip="Your Cyber Vision API token. Leave empty to keep existing token."
            extra={
              settings?.cyber_vision_api_token_set ? (
                <Text type="success">
                  <CheckCircleOutlined /> API token is configured
                </Text>
              ) : (
                <Text type="warning">No API token configured</Text>
              )
            }
          >
            <Input.Password
              placeholder="Enter API token (leave empty to keep existing)"
            />
          </Form.Item>

          <Form.Item
            name="cyber_vision_verify_ssl"
            label="Verify SSL Certificate"
            valuePropName="checked"
            tooltip="Enable SSL certificate verification. Disable for self-signed certificates."
          >
            <Switch checkedChildren="Yes" unCheckedChildren="No" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={isLoading}>
                Save Settings
              </Button>
              <Button
                onClick={handleTestConnection}
                loading={isTesting}
                icon={<SafetyCertificateOutlined />}
              >
                Test Connection
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {/* Info Card */}
      <Card title="About Cyber Vision Integration" size="small">
        <Text type="secondary">
          Cisco Cyber Vision integration allows PacketArch to:
        </Text>
        <ul style={{ marginTop: 8 }}>
          <li>Pull discovered devices from your OT network</li>
          <li>Compare scenario devices against real network inventory</li>
          <li>View vulnerability data detected by Cyber Vision</li>
          <li>Cross-reference generated traffic with actual network visibility</li>
        </ul>
        <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
          To get an API token, log into your Cyber Vision center and navigate to
          Settings &gt; API &gt; Generate Token.
        </Text>
      </Card>
    </Space>
  );
};

export default CyberVisionTab;
