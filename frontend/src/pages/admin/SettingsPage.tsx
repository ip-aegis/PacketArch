/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Admin settings page component
 */

import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
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
  Radio,
  Select,
  Collapse,
  Tag,
} from 'antd';
import { settingsApi } from '../../api/settings';
import {
  SettingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  TeamOutlined,
  RobotOutlined,
  EyeOutlined,
  DownloadOutlined,
  FileOutlined,
  FileTextOutlined,
  IdcardOutlined,
  DashboardOutlined,
  DollarOutlined,
  BarChartOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import UserManagementTab from '../../components/admin/UserManagementTab';
import CyberVisionTab from '../../components/admin/CyberVisionTab';
import LdapTab from '../../components/admin/LdapTab';
import DownloadsTab from '../../components/admin/DownloadsTab';
import GeneratedPcapsTab from '../../components/admin/GeneratedPcapsTab';
import SiteConfigOverviewTab from '../../components/admin/SiteConfigOverviewTab';
import AICostsTab from '../../components/admin/AICostsTab';
import AITokenUsageTab from '../../components/admin/AITokenUsageTab';
import SystemUpdatesTab from '../../components/admin/SystemUpdatesTab';
import ReleaseNotesTab from '../../components/admin/ReleaseNotesTab';
import { useSettingsStore } from '../../stores/settingsStore';
import type { SystemSetting, SettingsResponse } from '../../types';
import ContextualHelpIcon from '../../components/help/ContextualHelpIcon';

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
    } catch {
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
  settings: SettingsResponse | null;
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
  // Task → model routing for the active provider, fetched from the
  // backend so the UI never falls out of sync with the router table.
  const [routing, setRouting] = useState<{ task: string; label: string; model: string }[]>([]);
  const [routingLoading, setRoutingLoading] = useState(false);
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
      // Refresh routing so the table updates immediately.
      void fetchRouting();
    } catch {
      message.error('Failed to update provider');
    } finally {
      setSaving(false);
    }
  };

  const fetchRouting = async () => {
    setRoutingLoading(true);
    try {
      const data = await settingsApi.getAIRouting();
      setRouting(data.routing);
    } catch {
      // Non-fatal — UI just hides the routing card on error.
      setRouting([]);
    } finally {
      setRoutingLoading(false);
    }
  };

  useEffect(() => {
    void fetchRouting();
    // Re-fetch whenever the active provider changes via handleProviderChange.
    // Initial mount + handleProviderChange both call fetchRouting, so this
    // effect only needs to run once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    } catch {
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
    } catch {
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
    } catch {
      message.error('Failed to update model');
    } finally {
      setSaving(false);
    }
  };

  // Ordered by recommended default → fastest/cheapest. Opus 4.7 is the
  // best fit for scenario generation + deep tool use; Sonnet 4.6 is a
  // strong cost-conscious alternative; Haiku is fastest / cheapest.
  const anthropicModels = [
    { value: 'claude-opus-4-8', label: 'Claude Opus 4.8 (Latest · most capable)' },
    { value: 'claude-sonnet-5', label: 'Claude Sonnet 5 (balanced · lower cost)' },
    { value: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5 (fastest)' },
    { value: 'claude-opus-4-7', label: 'Claude Opus 4.7' },
    { value: 'claude-opus-4-6', label: 'Claude Opus 4.6' },
    { value: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6 (legacy)' },
    { value: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet 4.5 (legacy)' },
    { value: 'claude-opus-4-5-20251101', label: 'Claude Opus 4.5 (legacy)' },
  ];

  const openaiModels = [
    { value: 'gpt-5.6-sol', label: 'GPT-5.6 Sol (Latest flagship · frontier)' },
    { value: 'gpt-5.6-terra', label: 'GPT-5.6 Terra (balanced · lower cost)' },
    { value: 'gpt-5.6-luna', label: 'GPT-5.6 Luna (fastest · cheapest)' },
    { value: 'gpt-5.5', label: 'GPT-5.5 (legacy flagship)' },
    { value: 'gpt-5.5-pro', label: 'GPT-5.5 Pro (highest-stakes reasoning)' },
    { value: 'gpt-5.4', label: 'GPT-5.4 (legacy)' },
    { value: 'gpt-5.4-mini', label: 'GPT-5.4 Mini (legacy)' },
    { value: 'gpt-5.4-nano', label: 'GPT-5.4 Nano (legacy)' },
    { value: 'o3', label: 'o3 (reasoning)' },
    { value: 'o4-mini', label: 'o4-mini (fast reasoning)' },
    { value: 'gpt-5', label: 'GPT-5 (legacy)' },
    { value: 'gpt-5-mini', label: 'GPT-5 Mini (legacy)' },
    { value: 'gpt-5-nano', label: 'GPT-5 Nano (legacy)' },
    { value: 'gpt-4.1', label: 'GPT-4.1 (legacy)' },
    { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini (legacy)' },
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
    { value: 'gpt-4.1', label: 'GPT-4.1 (deprecated — removed Mar 2026)' },
    { value: 'gpt-4.1-mini', label: 'GPT-4.1 Mini (deprecated — removed Mar 2026)' },
    { value: 'gpt-4o', label: 'GPT-4o' },
    { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
    { value: 'o4-mini', label: 'o4-mini (reasoning)' },
    { value: 'o3', label: 'o3 (reasoning)' },
    { value: 'o3-mini', label: 'o3-mini (reasoning)' },
    // Anthropic-family
    { value: 'claude-opus-4-8', label: 'Claude Opus 4.8' },
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
          Pick a provider — PacketArch automatically chooses the best model from
          that provider for each AI task (chat, scenario generation, device
          naming, etc.). See the routing table below for the per-task picks.
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
                <Text type="secondary">- Cisco CIRCUIT AI platform</Text>
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

      {/* AI Model Routing — PacketArch picks the best model per task
          automatically. The user only chooses a provider; the table
          below shows what each AI feature will run. Manual override
          stays available in the Advanced section for power users. */}
      <Card title="AI Model Routing" size="small">
        <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          PacketArch automatically picks the best model from{' '}
          <strong>{providerLabel(selectedProvider)}</strong> for each AI task —
          flagship models for complex reasoning (chat, scenario generation,
          review) and smaller/faster tiers for short structured output (device
          naming, descriptions). You don&apos;t need to pick a model.
        </Text>
        {routingLoading ? (
          <Spin size="small" />
        ) : routing.length > 0 ? (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr auto',
              rowGap: 6,
              columnGap: 12,
            }}
          >
            {routing.map((r) => (
              <React.Fragment key={r.task}>
                <Text style={{ fontSize: 13 }}>{r.label}</Text>
                <Tag style={{ margin: 0, fontFamily: 'monospace' }}>
                  {r.model}
                </Tag>
              </React.Fragment>
            ))}
          </div>
        ) : (
          <Text type="secondary">
            Routing table unavailable. The provider may not be configured yet.
          </Text>
        )}

        <Collapse
          ghost
          style={{ marginTop: 16 }}
          items={[
            {
              key: 'advanced',
              label: (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Advanced: manual model override
                </Text>
              ),
              children: (
                <>
                  <Text type="secondary" style={{ display: 'block', marginBottom: 12, fontSize: 12 }}>
                    Pin a single model for every AI task on this provider.
                    Only takes effect for call sites that haven&apos;t been
                    migrated to the task router — most callers ignore this.
                    Leave the default unless you need to A/B test a model.
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
                      Save Override
                    </Button>
                  </Space.Compact>
                </>
              ),
            },
          ]}
        />
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
  const navigate = useNavigate();
  const {
    settings,
    isLoading,
    error,
    fetchSettings,
    updateSetting,
    testConnection,
    clearError,
  } = useSettingsStore();

  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionResult, setConnectionResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);
  // Controlled active tab so the Overview card's "Configure →" buttons can
  // deep-link into other tabs.
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<string>(
    searchParams.get('tab') || 'overview',
  );

  // Sync tab changes back to the URL so deep links survive reloads.
  useEffect(() => {
    const urlTab = searchParams.get('tab');
    if (urlTab && urlTab !== activeTab) {
      setActiveTab(urlTab);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const handleTabChange = (key: string) => {
    setActiveTab(key);
    setSearchParams({ tab: key }, { replace: true });
  };

  // The Overview cards deep-link using backend subsystem keys, some of which no
  // longer map 1:1 to a settings tab (AI is now consolidated; agents live on
  // their own page). Remap those before switching tabs.
  const handleSelectSubsystem = (key: string) => {
    if (key === 'ai_provider') return handleTabChange('ai');
    if (key === 'agents') return navigate('/agents');
    handleTabChange(key);
  };

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
      children: <SiteConfigOverviewTab onSelectTab={handleSelectSubsystem} />,
    },
    {
      key: 'ai',
      label: (
        <span>
          <RobotOutlined /> AI Integrations
        </span>
      ),
      children: (
        <Tabs
          defaultActiveKey="provider"
          items={[
            {
              key: 'provider',
              label: (
                <span>
                  <RobotOutlined /> Provider
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
              key: 'usage',
              label: (
                <span>
                  <BarChartOutlined /> Usage
                </span>
              ),
              children: <AITokenUsageTab />,
            },
            {
              key: 'costs',
              label: (
                <span>
                  <DollarOutlined /> Costs
                </span>
              ),
              children: <AICostsTab />,
            },
          ]}
        />
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
      key: 'release-notes',
      label: (
        <span>
          <FileTextOutlined /> Release Notes
        </span>
      ),
      children: <ReleaseNotesTab />,
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
      key: 'updates',
      label: (
        <span>
          <CloudUploadOutlined /> Updates
        </span>
      ),
      children: <SystemUpdatesTab />,
    },
  ];

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div>
          <Title level={2}>
            System Settings
            <ContextualHelpIcon articleId="admin-settings" tooltip="System settings help" />
          </Title>
          <Text type="secondary">
            Configure AI integrations, authentication, and system parameters.
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
            items={tabItems}
            activeKey={activeTab}
            onChange={handleTabChange}
            destroyInactiveTabPane
          />
        </Card>
      </Space>
    </div>
  );
};

export default SettingsPage;
