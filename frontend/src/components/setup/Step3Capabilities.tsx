/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React, { useState } from 'react';
import {
  Alert,
  Button,
  Form,
  Input,
  Space,
  Switch,
  Tag,
  Typography,
  message,
} from 'antd';
import { CheckCircleOutlined, ApiOutlined } from '@ant-design/icons';
import type { FormInstance } from 'antd';
import { setupApi } from '../../api/setup';

const { Text } = Typography;

export interface Step3Values {
  ai_enabled: boolean;
  ai_anthropic_api_key?: string;
  cv_enabled: boolean;
  cv_url?: string;
  cv_api_token?: string;
  cv_verify_ssl: boolean;
}

interface Props {
  form: FormInstance<Step3Values>;
  initial?: Partial<Step3Values>;
  liveTrafficSupported: boolean;
}

const Step3Capabilities: React.FC<Props> = ({
  form,
  initial,
  liveTrafficSupported,
}) => {
  const [testingKey, setTestingKey] = useState(false);
  const [keyResult, setKeyResult] = useState<
    { ok: boolean; message: string } | null
  >(null);

  const aiEnabled = Form.useWatch('ai_enabled', form) ?? initial?.ai_enabled ?? false;
  const cvEnabled = Form.useWatch('cv_enabled', form) ?? initial?.cv_enabled ?? false;

  const handleTestKey = async () => {
    const key = form.getFieldValue('ai_anthropic_api_key');
    if (!key) {
      message.warning('Enter a key first.');
      return;
    }
    setTestingKey(true);
    setKeyResult(null);
    try {
      const res = await setupApi.testAIKey(key);
      setKeyResult({
        ok: res.valid,
        message: res.valid ? 'Anthropic accepted the key.' : (res.error ?? 'Key rejected.'),
      });
    } catch {
      setKeyResult({
        ok: false,
        message: 'Test failed. Air-gapped sites can skip — your key will be saved un-validated.',
      });
    } finally {
      setTestingKey(false);
    }
  };

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={{
        ai_enabled: false,
        cv_enabled: false,
        cv_verify_ssl: false,
        ...initial,
      }}
    >
      <Text type="secondary">
        Optional integrations. All three sections can be skipped — you can
        configure these later under Settings.
      </Text>

      {/* Live traffic capability — read-only, derived from build variant. */}
      <div style={{ marginTop: 24, marginBottom: 24 }}>
        <Text strong>Live traffic</Text>{' '}
        {liveTrafficSupported ? (
          <Tag color="success" icon={<CheckCircleOutlined />}>
            Supported
          </Tag>
        ) : (
          <Tag color="default">Not supported (PCAP-only build)</Tag>
        )}
        <div>
          <Text type="secondary">
            {liveTrafficSupported
              ? 'Remote agents can connect to this server for live packet injection.'
              : 'This installation generates PCAPs only. Install the full variant to enable live agents.'}
          </Text>
        </div>
      </div>

      {/* AI provider */}
      <div style={{ marginBottom: 24 }}>
        <Form.Item
          name="ai_enabled"
          label={<Text strong>AI features</Text>}
          valuePropName="checked"
          tooltip="Enables natural-language scenario generation, the AI assistant, and AI scenario review. Requires an Anthropic API key (free to add later)."
        >
          <Switch />
        </Form.Item>

        {aiEnabled && (
          <>
            <Form.Item
              name="ai_anthropic_api_key"
              label="Anthropic API key (optional now)"
              extra="Skip if you'll add this later in Settings. Stored encrypted at rest."
            >
              <Input.Password
                placeholder="sk-ant-..."
                autoComplete="off"
                addonAfter={
                  <Button
                    type="link"
                    size="small"
                    icon={<ApiOutlined />}
                    onClick={handleTestKey}
                    loading={testingKey}
                  >
                    Test key
                  </Button>
                }
              />
            </Form.Item>
            {keyResult && (
              <Alert
                type={keyResult.ok ? 'success' : 'warning'}
                message={keyResult.message}
                style={{ marginBottom: 12 }}
                showIcon
              />
            )}
          </>
        )}
      </div>

      {/* Cyber Vision */}
      <div>
        <Form.Item
          name="cv_enabled"
          label={<Text strong>Cisco Cyber Vision import</Text>}
          valuePropName="checked"
          tooltip="Lets you import devices from a Cyber Vision center. Skip unless you have a CV deployment to point at."
        >
          <Switch />
        </Form.Item>

        {cvEnabled && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Form.Item
              name="cv_url"
              label="Cyber Vision URL"
              tooltip="Base URL of your CV center, e.g. https://cv-center.example.com. No trailing slash."
            >
              <Input placeholder="https://cv.example.com" />
            </Form.Item>
            <Form.Item
              name="cv_api_token"
              label="API token"
              tooltip="API token from CV with read access. Stored encrypted at rest."
            >
              <Input.Password autoComplete="off" />
            </Form.Item>
            <Form.Item
              name="cv_verify_ssl"
              label="Verify TLS certificate"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>
          </Space>
        )}
      </div>
    </Form>
  );
};

export default Step3Capabilities;
