/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * LDAP / Active Directory settings tab.
 *
 * Mirrors the Cyber Vision tab: load the current settings, edit via Ant
 * Design Form, test the connection with the in-memory values, and save.
 */

import React, { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Collapse,
  Form,
  Input,
  Space,
  Spin,
  Switch,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd';
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LockOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import {
  ldapApi,
  type LdapSettings,
  type LdapSettingsUpdate,
} from '../../api/ldap';
import { extractErrorMessage } from '../../utils/errorUtils';

const { Text, Paragraph } = Typography;

const AD_PRESET = {
  ldap_user_search_filter: '(&(objectClass=user)(sAMAccountName={username}))',
  ldap_email_attribute: 'mail',
  ldap_display_name_attribute: 'displayName',
};

type FormValues = {
  ldap_enabled: boolean;
  ldap_server_url: string;
  ldap_use_ssl: boolean;
  ldap_start_tls: boolean;
  ldap_verify_ssl: boolean;
  ldap_bind_dn: string;
  ldap_bind_password: string;
  ldap_search_base: string;
  ldap_user_search_filter: string;
  ldap_email_attribute: string;
  ldap_display_name_attribute: string;
};

const LdapTab: React.FC = () => {
  const [form] = Form.useForm<FormValues>();
  const [settings, setSettings] = useState<LdapSettings | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    serverInfo: string | null;
  } | null>(null);

  const loadSettings = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await ldapApi.getSettings();
      setSettings(data);
      form.setFieldsValue({
        ldap_enabled: data.ldap_enabled,
        ldap_server_url: data.ldap_server_url,
        ldap_use_ssl: data.ldap_use_ssl,
        ldap_start_tls: data.ldap_start_tls,
        ldap_verify_ssl: data.ldap_verify_ssl,
        ldap_bind_dn: data.ldap_bind_dn,
        ldap_bind_password: '',
        ldap_search_base: data.ldap_search_base,
        ldap_user_search_filter: data.ldap_user_search_filter,
        ldap_email_attribute: data.ldap_email_attribute,
        ldap_display_name_attribute: data.ldap_display_name_attribute,
      });
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to load LDAP settings'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSave = async (values: FormValues) => {
    setSaving(true);
    setError(null);
    try {
      const payload: LdapSettingsUpdate = {
        ldap_enabled: values.ldap_enabled,
        ldap_server_url: values.ldap_server_url,
        ldap_use_ssl: values.ldap_use_ssl,
        ldap_start_tls: values.ldap_start_tls,
        ldap_verify_ssl: values.ldap_verify_ssl,
        ldap_bind_dn: values.ldap_bind_dn,
        ldap_search_base: values.ldap_search_base,
        ldap_user_search_filter: values.ldap_user_search_filter,
        ldap_email_attribute: values.ldap_email_attribute,
        ldap_display_name_attribute: values.ldap_display_name_attribute,
      };
      if (values.ldap_bind_password) {
        payload.ldap_bind_password = values.ldap_bind_password;
      }
      const updated = await ldapApi.updateSettings(payload);
      setSettings(updated);
      form.setFieldValue('ldap_bind_password', '');
      message.success('LDAP settings saved');
    } catch (err) {
      const msg = extractErrorMessage(err, 'Failed to save LDAP settings');
      setError(msg);
      message.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    const values = form.getFieldsValue();
    if (!values.ldap_server_url) {
      message.warning('Please enter a server URL');
      return;
    }
    if (!values.ldap_bind_dn) {
      message.warning('Please enter a bind DN');
      return;
    }
    if (!values.ldap_bind_password && !settings?.ldap_bind_password_set) {
      message.warning('Please enter a bind password (or save one first)');
      return;
    }

    setTesting(true);
    setTestResult(null);
    try {
      const result = await ldapApi.testConnection({
        ldap_server_url: values.ldap_server_url,
        ldap_use_ssl: values.ldap_use_ssl,
        ldap_start_tls: values.ldap_start_tls,
        ldap_verify_ssl: values.ldap_verify_ssl,
        ldap_bind_dn: values.ldap_bind_dn,
        ldap_bind_password: values.ldap_bind_password || undefined,
        ldap_search_base: values.ldap_search_base,
      });
      setTestResult({
        success: result.success,
        message: result.message,
        serverInfo: result.server_info,
      });
      if (result.success) {
        message.success('Connection successful');
      } else {
        message.error(`Connection failed: ${result.message}`);
      }
    } catch (err) {
      const msg = extractErrorMessage(err, 'Connection test failed');
      setTestResult({ success: false, message: msg, serverInfo: null });
      message.error(msg);
    } finally {
      setTesting(false);
    }
  };

  const handleApplyADPreset = () => {
    form.setFieldsValue(AD_PRESET);
    message.info('Active Directory preset applied (not yet saved)');
  };

  if (loading && !settings) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">Loading LDAP settings...</Text>
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
          onClose={() => setError(null)}
        />
      )}

      {testResult && (
        <Alert
          message={testResult.success ? 'Connection Successful' : 'Connection Failed'}
          description={
            testResult.serverInfo
              ? `${testResult.message} — ${testResult.serverInfo}`
              : testResult.message
          }
          type={testResult.success ? 'success' : 'error'}
          showIcon
          icon={testResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
          closable
          onClose={() => setTestResult(null)}
        />
      )}

      <Card size="small">
        <Space>
          {settings?.ldap_enabled ? (
            <Tag icon={<CheckCircleOutlined />} color="success">
              LDAP enabled
            </Tag>
          ) : (
            <Tag icon={<CloseCircleOutlined />} color="default">
              LDAP disabled
            </Tag>
          )}
          {settings?.ldap_bind_password_set ? (
            <Tag icon={<LockOutlined />} color="blue">
              Bind password configured
            </Tag>
          ) : (
            <Tag color="warning">No bind password</Tag>
          )}
        </Space>
      </Card>

      <Card title="LDAP / Active Directory Configuration" size="small">
        <Form<FormValues>
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={{
            ldap_enabled: false,
            ldap_use_ssl: true,
            ldap_start_tls: false,
            ldap_verify_ssl: true,
            ldap_user_search_filter: AD_PRESET.ldap_user_search_filter,
            ldap_email_attribute: AD_PRESET.ldap_email_attribute,
            ldap_display_name_attribute: AD_PRESET.ldap_display_name_attribute,
          }}
        >
          <Form.Item
            name="ldap_enabled"
            label="Enable LDAP Authentication"
            valuePropName="checked"
            tooltip="When enabled, the login form tries LDAP first and falls back to local accounts."
          >
            <Switch checkedChildren="Yes" unCheckedChildren="No" />
          </Form.Item>

          <Form.Item
            name="ldap_server_url"
            label="Server URL"
            tooltip="e.g. ldaps://dc.acme.com:636 or ldap://dc.acme.com:389"
            rules={[{ required: true, message: 'Please enter the LDAP server URL' }]}
          >
            <Input prefix={<ApiOutlined />} placeholder="ldaps://dc.acme.com:636" />
          </Form.Item>

          <Space size="large" style={{ width: '100%' }}>
            <Form.Item
              name="ldap_use_ssl"
              label="Use SSL (LDAPS)"
              valuePropName="checked"
            >
              <Switch checkedChildren="On" unCheckedChildren="Off" />
            </Form.Item>
            <Form.Item
              name="ldap_start_tls"
              label="Use StartTLS"
              valuePropName="checked"
              tooltip="Upgrade a plain ldap:// connection to TLS."
            >
              <Switch checkedChildren="On" unCheckedChildren="Off" />
            </Form.Item>
            <Form.Item
              name="ldap_verify_ssl"
              label="Verify Cert"
              valuePropName="checked"
              tooltip="Disable only for self-signed labs."
            >
              <Switch checkedChildren="On" unCheckedChildren="Off" />
            </Form.Item>
          </Space>

          <Form.Item
            name="ldap_bind_dn"
            label="Service-Account Bind DN"
            tooltip="DN of the account PacketArch uses to search for users."
            rules={[{ required: true, message: 'Please enter the bind DN' }]}
          >
            <Input placeholder="CN=svc_packetarch,OU=Service Accounts,DC=acme,DC=com" />
          </Form.Item>

          <Form.Item
            name="ldap_bind_password"
            label="Service-Account Bind Password"
            tooltip="Leave empty to keep the existing password."
            extra={
              settings?.ldap_bind_password_set ? (
                <Text type="success">
                  <CheckCircleOutlined /> Password is configured
                </Text>
              ) : (
                <Text type="warning">No password configured</Text>
              )
            }
          >
            <Input.Password placeholder="Enter new password (leave empty to keep existing)" />
          </Form.Item>

          <Form.Item
            name="ldap_search_base"
            label="User Search Base"
            tooltip="e.g. DC=acme,DC=com or OU=Users,DC=acme,DC=com"
            rules={[{ required: true, message: 'Please enter the search base' }]}
          >
            <Input placeholder="DC=acme,DC=com" />
          </Form.Item>

          <Collapse
            ghost
            items={[
              {
                key: 'advanced',
                label: 'Advanced — filter and attribute mapping',
                children: (
                  <>
                    <Form.Item style={{ marginBottom: 8 }}>
                      <Button
                        icon={<ThunderboltOutlined />}
                        onClick={handleApplyADPreset}
                      >
                        Apply Active Directory preset
                      </Button>
                    </Form.Item>
                    <Form.Item
                      name="ldap_user_search_filter"
                      label="User Search Filter"
                      tooltip="The literal {username} is replaced with the escaped login name."
                      rules={[
                        { required: true, message: 'Please enter a search filter' },
                        {
                          validator: (_, value) =>
                            value && value.includes('{username}')
                              ? Promise.resolve()
                              : Promise.reject(
                                  new Error('Filter must contain the {username} placeholder')
                                ),
                        },
                      ]}
                    >
                      <Input placeholder={AD_PRESET.ldap_user_search_filter} />
                    </Form.Item>
                    <Space size="large" style={{ width: '100%' }}>
                      <Form.Item name="ldap_email_attribute" label="Email Attribute">
                        <Input placeholder="mail" style={{ width: 180 }} />
                      </Form.Item>
                      <Form.Item
                        name="ldap_display_name_attribute"
                        label="Display Name Attribute"
                      >
                        <Input placeholder="displayName" style={{ width: 220 }} />
                      </Form.Item>
                    </Space>
                  </>
                ),
              },
            ]}
          />

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={saving}>
                Save Settings
              </Button>
              <Tooltip title="Bind as the service account to validate the current form values">
                <Button
                  onClick={handleTestConnection}
                  loading={testing}
                  icon={<SafetyCertificateOutlined />}
                >
                  Test Connection
                </Button>
              </Tooltip>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card title="How it works" size="small">
        <Paragraph type="secondary" style={{ marginBottom: 8 }}>
          When LDAP is enabled, the login flow tries the directory first; if the
          user is unknown to LDAP or the directory is unreachable, PacketArch
          falls back to local accounts. Local admins can always sign in.
        </Paragraph>
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          LDAP users are created on their first successful login and start as
          non-admin. Promote them in User Management.
        </Paragraph>
      </Card>
    </Space>
  );
};

export default LdapTab;
