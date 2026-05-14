/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Admin settings page component
 */

import React, { useEffect, useState } from 'react';
import {
  Typography,
  Card,
  Tabs,
  Input,
  Button,
  Space,
  Alert,
  message,
  Spin,
  Popconfirm,
  Radio,
  Select,
} from 'antd';
import {
  KeyOutlined,
  GlobalOutlined,
  SettingOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  TeamOutlined,
  RobotOutlined,
  EyeOutlined,
  RocketOutlined,
  DownloadOutlined,
  FileOutlined,
  IdcardOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import UserManagementTab from '../../components/admin/UserManagementTab';
import CyberVisionTab from '../../components/admin/CyberVisionTab';
import LdapTab from '../../components/admin/LdapTab';
import AgentsTab from '../../components/admin/AgentsTab';
import DownloadsTab from '../../components/admin/DownloadsTab';
import GeneratedPcapsTab from '../../components/admin/GeneratedPcapsTab';
import SiteConfigOverviewTab from '../../components/admin/SiteConfigOverviewTab';
import { useSettingsStore } from '../../stores/settingsStore';
import { useFeatures } from '../../hooks/useFeatures';
import type { SystemSetting } from '../../types';

const { Title, Text } = Typography;

// Helper component for displaying/editing a setting
const SettingItem: React.FC<{
  setting: SystemSetting;
  onSave: (key: string, value: string | null) => Promise<void>;
  isSecret?: boolean;
}> = ({ setting, onSave, isSecret }) => {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(setting.value || '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(setting.key, value || null);
      message.success(`${setting.key} updated successfully`);
      setEditing(false);
    } catch (error) {
      message.error('Failed to update setting');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setValue(setting.value || '');
    setEditing(false);
  };

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ marginBottom: 4 }}>
        <Text strong>{setting.key}</Text>
      </div>
      {setting.description && (
        <div style={{ marginBottom: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {setting.description}
          </Text>
        </div>
      )}
      {editing ? (
        <Space.Compact style={{ width: '100%' }}>
          <Input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            type={isSecret ? 'password' : 'text'}
            placeholder={isSecret ? 'Enter new value...' : 'Enter value...'}
            style={{ flex: 1 }}
          />
          <Button type="primary" onClick={handleSave} loading={saving}>
            Save
          </Button>
          <Button onClick={handleCancel}>Cancel</Button>
        </Space.Compact>
      ) : (
        <Space.Compact style={{ width: '100%' }}>
          <Input
            value={setting.value || ''}
            readOnly
            type={isSecret ? 'password' : 'text'}
            style={{ flex: 1 }}
          />
          <Button onClick={() => setEditing(true)}>Edit</Button>
        </Space.Compact>
      )}
    </div>
  );
};

// AI Provider Tab Component
const AIProviderTab: React.FC<{
  settings: any;
  updateSetting: (key: string, value: string | null) => Promise<void>;
  testConnection: () => Promise<void>;
  testingConnection: boolean;
  connectionResult: { success: boolean; message: string } | null;
  setConnectionResult: (result: { success: boolean; message: string } | null) => void;
}> = ({
  settings,
  updateSetting,
  testConnection,
  testingConnection,
  connectionResult,
  setConnectionResult,
}) => {
  const [selectedProvider, setSelectedProvider] = useState<string>('anthropic');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('');
  const [saving, setSaving] = useState(false);
  // CIRCUIT-specific config — three rows instead of one API key
  const [circuitClientId, setCircuitClientId] = useState('');
  const [circuitClientSecret, setCircuitClientSecret] = useState('');
  const [circuitAppKey, setCircuitAppKey] = useState('');

  const providerLabel = (p: string): string =>
    p === 'anthropic' ? 'Anthropic (Claude)' : p === 'openai' ? 'OpenAI (GPT)' : p === 'circuit' ? 'Cisco CIRCUIT' : p;

  // Get current provider from settings
  useEffect(() => {
    if (settings) {
      const allSettings = [
        ...(settings.api_tokens || []),
        ...(settings.network || []),
        ...(settings.system || []),
      ];

      const providerSetting = allSettings.find((s: SystemSetting) => s.key === 'ai_provider');
      if (providerSetting?.value) {
        setSelectedProvider(providerSetting.value);
      }

      // Get current model
      const anthropicModel = allSettings.find((s: SystemSetting) => s.key === 'anthropic_model');
      const openaiModel = allSettings.find((s: SystemSetting) => s.key === 'openai_model');
      const circuitModel = allSettings.find((s: SystemSetting) => s.key === 'circuit_model');

      if (selectedProvider === 'anthropic' && anthropicModel?.value) {
        setModel(anthropicModel.value);
      } else if (selectedProvider === 'openai' && openaiModel?.value) {
        setModel(openaiModel.value);
      } else if (selectedProvider === 'circuit' && circuitModel?.value) {
        setModel(circuitModel.value);
      }

      // Pre-populate non-secret CIRCUIT fields so admins see what's currently
      // saved. client_secret stays write-only (encrypted at rest).
      const circuitId = allSettings.find((s: SystemSetting) => s.key === 'circuit_client_id');
      const circuitApp = allSettings.find((s: SystemSetting) => s.key === 'circuit_app_key');
      if (circuitId?.value) setCircuitClientId(circuitId.value);
      if (circuitApp?.value) setCircuitAppKey(circuitApp.value);
    }
  }, [settings, selectedProvider]);

  const handleProviderChange = async (provider: string) => {
    setSelectedProvider(provider);
    setSaving(true);
    try {
      await updateSetting('ai_provider', provider);
      message.success(`AI Provider changed to ${providerLabel(provider)}`);
    } catch (error) {
      message.error('Failed to update provider');
    } finally {
      setSaving(false);
    }
  };

  const handleApiKeySave = async () => {
    if (!apiKey.trim()) {
      message.warning('Please enter an API key');
      return;
    }

    setSaving(true);
    try {
      const keyName = selectedProvider === 'anthropic' ? 'anthropic_api_key' : 'openai_api_key';
      await updateSetting(keyName, apiKey);
      message.success('API key updated successfully');
      setApiKey('');
    } catch (error) {
      message.error('Failed to update API key');
    } finally {
      setSaving(false);
    }
  };

  const handleCircuitCredentialsSave = async () => {
    if (!circuitClientId.trim() || !circuitAppKey.trim()) {
      message.warning('Client ID and App Key are required');
      return;
    }
    setSaving(true);
    try {
      await updateSetting('circuit_client_id', circuitClientId.trim());
      await updateSetting('circuit_app_key', circuitAppKey.trim());
      // Only persist client_secret if the field is non-empty — leave the
      // existing encrypted value untouched if the user is just updating
      // the non-secret fields.
      if (circuitClientSecret.trim()) {
        await updateSetting('circuit_client_secret', circuitClientSecret.trim());
        setCircuitClientSecret('');
      }
      message.success('CIRCUIT credentials updated');
    } catch (error) {
      message.error('Failed to update CIRCUIT credentials');
    } finally {
      setSaving(false);
    }
  };

  const handleModelSave = async () => {
    if (!model.trim()) {
      message.warning('Please select a model');
      return;
    }

    setSaving(true);
    try {
      const modelKey =
        selectedProvider === 'anthropic' ? 'anthropic_model'
        : selectedProvider === 'circuit' ? 'circuit_model'
        : 'openai_model';
      await updateSetting(modelKey, model);
      message.success('Model updated successfully');
    } catch (error) {
      message.error('Failed to update model');
    } finally {
      setSaving(false);
    }
  };

  // Ordered by recommended default → fastest/cheapest. Opus 4.7 is the
  // best fit for scenario generation + deep tool use; Sonnet 4.6 is a
  // strong cost-conscious alternative; Haiku is fastest / cheapest.
  const anthropicModels = [
    { value: 'claude-opus-4-7', label: 'Claude Opus 4.7 (Latest · most capable)' },
    { value: 'claude-opus-4-6', label: 'Claude Opus 4.6' },
    { value: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6 (balanced · lower cost)' },
    { value: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet 4.5' },
    { value: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5 (fastest)' },
    { value: 'claude-opus-4-5-20251101', label: 'Claude Opus 4.5' },
  ];

  const openaiModels = [
    { value: 'o3', label: 'o3 (Reasoning)' },
    { value: 'gpt-4.1', label: 'GPT-4.1' },
    { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini' },
    { value: 'o4-mini', label: 'o4-mini (Fast Reasoning)' },
  ];

  // Cisco CIRCUIT exposes the full Azure OpenAI surface plus
  // Anthropic, Google, and open-weight models — but each appkey is
  // entitled to a specific subset that depends on how it was
  // provisioned. The CIRCUIT gateway has no /models or /entitlements
  // self-introspection endpoint, so the only reliable way to know
  // what your appkey can call is to probe one model at a time. The
  // list below is the full deployed catalog (extracted from
  // chat-ai.cisco.com/openapi.json on 2026-05-14); models your
  // appkey isn't entitled to return HTTP 401 from the gateway. Use
  // the "Test AI Connection" button after switching models to verify
  // entitlement.
  const circuitModels = [
    // OpenAI-family
    { value: 'gpt-5-nano', label: 'GPT-5 Nano' },
    { value: 'gpt-5-mini', label: 'GPT-5 Mini' },
    { value: 'gpt-5-chat', label: 'GPT-5 Chat' },
    { value: 'gpt-5', label: 'GPT-5' },
    { value: 'gpt-4.1', label: 'GPT-4.1' },
    { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini' },
    { value: 'gpt-4o', label: 'GPT-4o' },
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
    { value: 'o4-mini', label: 'o4-mini (reasoning)' },
    { value: 'o3', label: 'o3 (reasoning)' },
    { value: 'o3-mini', label: 'o3-mini (reasoning)' },
    // Anthropic-family
    { value: 'claude-opus-4-7', label: 'Claude Opus 4.7' },
    { value: 'claude-opus-4-6', label: 'Claude Opus 4.6' },
    { value: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6' },
    { value: 'claude-haiku-4-5', label: 'Claude Haiku 4.5' },
    // Google Gemini
    { value: 'gemini-3.1-pro', label: 'Gemini 3.1 Pro' },
    { value: 'gemini-3.1-flash-lite', label: 'Gemini 3.1 Flash Lite' },
    { value: 'gemini-3-pro', label: 'Gemini 3 Pro' },
    { value: 'gemini-3-flash', label: 'Gemini 3 Flash' },
    { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
    { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash' },
    // Open-weight / Cisco-specific
    { value: 'llama-3-70b', label: 'Llama 3 70B' },
    { value: 'llama-3-8b', label: 'Llama 3 8B' },
    { value: 'gemma-4-26b-a4b-it-maas', label: 'Gemma 4 26B' },
    { value: 'cisco-deep-network', label: 'Cisco Deep Network' },
  ];

  const modelsForProvider =
    selectedProvider === 'anthropic' ? anthropicModels
    : selectedProvider === 'circuit' ? circuitModels
    : openaiModels;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {connectionResult && (
        <Alert
          message={connectionResult.success ? 'Connection Successful' : 'Connection Failed'}
          description={connectionResult.message}
          type={connectionResult.success ? 'success' : 'error'}
          showIcon
          icon={connectionResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
          closable
          onClose={() => setConnectionResult(null)}
        />
      )}

      {/* Provider Selection */}
      <Card title="AI Provider Selection" size="small">
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          Select which AI provider to use for the assistant. Both providers support function calling
          for scenario modifications.
        </Text>
        <Radio.Group
          value={selectedProvider}
          onChange={(e) => handleProviderChange(e.target.value)}
          disabled={saving}
        >
          <Space direction="vertical">
            <Radio value="anthropic">
              <Space>
                <strong>Anthropic (Claude)</strong>
                <Text type="secondary">- Recommended for OT/ICS expertise</Text>
              </Space>
            </Radio>
            <Radio value="openai">
              <Space>
                <strong>OpenAI (GPT)</strong>
                <Text type="secondary">- Alternative with broad capabilities</Text>
              </Space>
            </Radio>
            <Radio value="circuit">
              <Space>
                <strong>Cisco CIRCUIT</strong>
                <Text type="secondary">- Cisco internal gateway (chat-ai.cisco.com); requires Cisco VPN + appkey</Text>
              </Space>
            </Radio>
          </Space>
        </Radio.Group>
      </Card>

      {/* Credentials — shape depends on provider. Anthropic / OpenAI share
          a single API-key field; CIRCUIT has three (client_id, secret,
          appkey) because it uses OAuth2 client_credentials. */}
      {selectedProvider !== 'circuit' ? (
        <Card
          title={`${providerLabel(selectedProvider)} API Key`}
          size="small"
        >
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            {selectedProvider === 'anthropic'
              ? 'Enter your Anthropic API key. Get one at console.anthropic.com'
              : 'Enter your OpenAI API key. Get one at platform.openai.com'}
          </Text>
          <Space.Compact style={{ width: '100%' }}>
            <Input
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              type="password"
              placeholder={`Enter ${providerLabel(selectedProvider)} API key...`}
              style={{ flex: 1 }}
            />
            <Button type="primary" onClick={handleApiKeySave} loading={saving}>
              Save Key
            </Button>
          </Space.Compact>
        </Card>
      ) : (
        <Card title="Cisco CIRCUIT Credentials" size="small">
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            CIRCUIT uses OAuth2 client_credentials. Get the Okta client_id /
            client_secret and an appkey (egai-…) from the CIRCUIT API portal.
            Backend reads <code>CIRCUIT_CLIENT_ID</code> /{' '}
            <code>CIRCUIT_CLIENT_SECRET</code> / <code>CIRCUIT_APP_KEY</code>{' '}
            env vars first; these fields are the fallback.
          </Text>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input
              addonBefore="Client ID"
              value={circuitClientId}
              onChange={(e) => setCircuitClientId(e.target.value)}
              placeholder="0oa..."
            />
            <Input
              addonBefore="Client Secret"
              value={circuitClientSecret}
              onChange={(e) => setCircuitClientSecret(e.target.value)}
              type="password"
              placeholder="leave blank to keep existing"
            />
            <Input
              addonBefore="App Key"
              value={circuitAppKey}
              onChange={(e) => setCircuitAppKey(e.target.value)}
              placeholder="egai-prd-..."
            />
            <Button type="primary" onClick={handleCircuitCredentialsSave} loading={saving}>
              Save CIRCUIT Credentials
            </Button>
          </Space>
        </Card>
      )}

      {/* Model Selection */}
      <Card title="Model Selection" size="small">
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          Select which model to use for AI responses. More capable models provide better results
          but may have higher costs.
        </Text>
        <Space.Compact style={{ width: '100%' }}>
          <Select
            value={model}
            onChange={setModel}
            style={{ flex: 1 }}
            placeholder="Select a model..."
            options={modelsForProvider}
          />
          <Button type="primary" onClick={handleModelSave} loading={saving}>
            Save Model
          </Button>
        </Space.Compact>
      </Card>

      {/* Test Connection */}
      <Card title="Test Connection" size="small">
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          Test the AI API connection to verify your configuration is working.
        </Text>
        <Button
          type="default"
          onClick={testConnection}
          loading={testingConnection}
          icon={<CheckCircleOutlined />}
        >
          Test AI Connection
        </Button>
      </Card>
    </Space>
  );
};

const SettingsPage: React.FC = () => {
  const {
    settings,
    isLoading,
    error,
    fetchSettings,
    updateSetting,
    seedSettings,
    testConnection,
    clearError,
  } = useSettingsStore();
  const { liveTrafficEnabled } = useFeatures();

  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionResult, setConnectionResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);
  // Controlled active tab so the Overview card's "Configure →" buttons can
  // deep-link into other tabs.
  const [activeTab, setActiveTab] = useState<string>('overview');

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setConnectionResult(null);
    try {
      const result = await testConnection();
      setConnectionResult(result);
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSeedSettings = async () => {
    try {
      const result = await seedSettings();
      message.success(`Created ${result.created} settings, skipped ${result.skipped} existing`);
    } catch (error) {
      message.error('Failed to seed settings');
    }
  };

  if (isLoading && !settings) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">Loading settings...</Text>
        </div>
      </div>
    );
  }

  const tabItems = [
    {
      key: 'overview',
      label: (
        <span>
          <DashboardOutlined /> Overview
        </span>
      ),
      children: <SiteConfigOverviewTab onSelectTab={setActiveTab} />,
    },
    {
      key: 'api_tokens',
      label: (
        <span>
          <KeyOutlined /> API Tokens
        </span>
      ),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {connectionResult && (
            <Alert
              message={connectionResult.success ? 'Connection Successful' : 'Connection Failed'}
              description={connectionResult.message}
              type={connectionResult.success ? 'success' : 'error'}
              showIcon
              icon={
                connectionResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />
              }
              closable
              onClose={() => setConnectionResult(null)}
            />
          )}

          {settings?.api_tokens.map((setting) => (
            <SettingItem
              key={setting.key}
              setting={setting}
              onSave={updateSetting}
              isSecret
            />
          ))}

          <Button
            type="default"
            onClick={handleTestConnection}
            loading={testingConnection}
            icon={<CheckCircleOutlined />}
          >
            Test API Connection
          </Button>
        </Space>
      ),
    },
    {
      key: 'ai_provider',
      label: (
        <span>
          <RobotOutlined /> AI Provider
        </span>
      ),
      children: (
        <AIProviderTab
          settings={settings}
          updateSetting={updateSetting}
          testConnection={handleTestConnection}
          testingConnection={testingConnection}
          connectionResult={connectionResult}
          setConnectionResult={setConnectionResult}
        />
      ),
    },
    {
      key: 'network',
      label: (
        <span>
          <GlobalOutlined /> Network Defaults
        </span>
      ),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {settings?.network.map((setting) => (
            <SettingItem key={setting.key} setting={setting} onSave={updateSetting} />
          ))}
        </Space>
      ),
    },
    {
      key: 'system',
      label: (
        <span>
          <SettingOutlined /> System
        </span>
      ),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {settings?.system.map((setting) => (
            <SettingItem key={setting.key} setting={setting} onSave={updateSetting} />
          ))}
        </Space>
      ),
    },
    {
      key: 'agents',
      label: (
        <span>
          <RocketOutlined /> Traffic Agents
        </span>
      ),
      children: <AgentsTab />,
    },
    {
      key: 'cyber_vision',
      label: (
        <span>
          <EyeOutlined /> Cyber Vision
        </span>
      ),
      children: <CyberVisionTab />,
    },
    {
      key: 'ldap',
      label: (
        <span>
          <IdcardOutlined /> LDAP / AD
        </span>
      ),
      children: <LdapTab />,
    },
    {
      key: 'users',
      label: (
        <span>
          <TeamOutlined /> User Management
        </span>
      ),
      children: <UserManagementTab />,
    },
    {
      key: 'downloads',
      label: (
        <span>
          <DownloadOutlined /> Downloads
        </span>
      ),
      children: <DownloadsTab />,
    },
    {
      key: 'pcaps',
      label: (
        <span>
          <FileOutlined /> Generated PCAPs
        </span>
      ),
      children: <GeneratedPcapsTab />,
    },
    {
      key: 'seed',
      label: (
        <span>
          <DatabaseOutlined /> Seed Data
        </span>
      ),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Card title="Initialize Default Settings">
            <Text type="secondary">
              Seed the database with default system settings. This will create any
              missing settings without overwriting existing values.
            </Text>
            <div style={{ marginTop: 16 }}>
              <Button type="primary" onClick={handleSeedSettings} icon={<DatabaseOutlined />}>
                Seed Default Settings
              </Button>
            </div>
          </Card>

          <Card title="Reset to Defaults">
            <Text type="secondary">
              Reset all settings to their default values. This action cannot be undone.
            </Text>
            <div style={{ marginTop: 16 }}>
              <Popconfirm
                title="Reset all settings?"
                description="This will overwrite all current settings with default values."
                onConfirm={() => message.info('Reset functionality not yet implemented')}
                okText="Yes, Reset"
                cancelText="Cancel"
                okButtonProps={{ danger: true }}
              >
                <Button danger>Reset All Settings</Button>
              </Popconfirm>
            </div>
          </Card>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Title level={2}>System Settings</Title>
          <Text type="secondary">
            Configure API tokens, network defaults, and system parameters.
          </Text>
        </div>

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

        <Card>
          <Tabs
            items={tabItems.filter((t) => liveTrafficEnabled || t.key !== 'agents')}
            activeKey={activeTab}
            onChange={setActiveTab}
            destroyInactiveTabPane
          />
        </Card>
      </Space>
    </div>
  );
};

export default SettingsPage;
