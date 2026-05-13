/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * First-run setup wizard. Rendered by SetupGate when the backend reports
 * setup.completed=false. Walks the operator through admin credentials, site
 * identity, optional capabilities, and a final GPL acknowledgment.
 *
 * On submit, POSTs everything to /api/v1/setup/complete in one transaction,
 * receives access + refresh tokens, and drops the new admin straight into
 * the dashboard.
 */

import React, { useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Form,
  Layout,
  Space,
  Steps,
  Typography,
  message,
} from 'antd';
import { useNavigate } from 'react-router-dom';
import {
  setupApi,
  type AdminAccountInput,
  type SiteIdentityInput,
} from '../api/setup';
import { setTokens } from '../api/client';
import { useSetupStatusStore } from '../stores/setupStatusStore';
import { useAuthStore } from '../stores/authStore';
import { extractErrorMessage } from '../utils/errorUtils';
import Step1AdminAccount from '../components/setup/Step1AdminAccount';
import Step2SiteIdentity from '../components/setup/Step2SiteIdentity';
import Step3Capabilities, {
  type Step3Values,
} from '../components/setup/Step3Capabilities';
import Step4Confirm from '../components/setup/Step4Confirm';
import { useSetupStatus } from '../hooks/useSetupStatus';

const { Title, Text } = Typography;

// Marker localStorage key — read once and cleared by AppLayout so the GPL
// acknowledgment modal doesn't re-fire immediately after the wizard records
// the same acceptance server-side.
export const SETUP_ACK_LOCAL_KEY = 'packetarch_setup_ack_recorded';

const SetupWizardPage: React.FC = () => {
  const navigate = useNavigate();
  const markComplete = useSetupStatusStore((s) => s.markComplete);
  const fetchCurrentUser = useAuthStore((s) => s.fetchCurrentUser);
  const { liveTrafficSupported } = useSetupStatus();

  const [current, setCurrent] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [adminForm] = Form.useForm<
    AdminAccountInput & { password_confirm: string }
  >();
  const [siteForm] = Form.useForm<SiteIdentityInput>();
  const [capsForm] = Form.useForm<Step3Values>();

  // Aggregated values for step 4 review + final POST.
  const [admin, setAdmin] = useState<AdminAccountInput | null>(null);
  const [site, setSite] = useState<SiteIdentityInput | null>(null);
  const [capabilities, setCapabilities] = useState<Step3Values | null>(null);
  const [ackAccepted, setAckAccepted] = useState(false);

  const detectedTimezone =
    Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  const detectedHostname =
    typeof window !== 'undefined' ? window.location.hostname : '';

  const stepItems = [
    { title: 'Admin' },
    { title: 'Site' },
    { title: 'Capabilities' },
    { title: 'Confirm' },
  ];

  const handleNext = async () => {
    try {
      if (current === 0) {
        const values = await adminForm.validateFields();
        setAdmin({
          username: values.username,
          password: values.password,
          email: values.email || null,
        });
        setCurrent(1);
      } else if (current === 1) {
        const values = await siteForm.validateFields();
        setSite(values);
        setCurrent(2);
      } else if (current === 2) {
        const values = await capsForm.validateFields();
        setCapabilities(values);
        setCurrent(3);
      }
    } catch {
      // Validation errors are surfaced inline by Form.
    }
  };

  const handleBack = () => {
    if (current > 0) setCurrent(current - 1);
  };

  const handleSubmit = async () => {
    if (!admin || !site || !capabilities) return;
    if (!ackAccepted) {
      message.warning('Please acknowledge the license to continue.');
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await setupApi.complete({
        admin,
        site,
        ai: {
          enabled: capabilities.ai_enabled,
          anthropic_api_key: capabilities.ai_anthropic_api_key || null,
        },
        cyber_vision: {
          enabled: capabilities.cv_enabled,
          url: capabilities.cv_url || null,
          api_token: capabilities.cv_api_token || null,
          verify_ssl: capabilities.cv_verify_ssl,
        },
        accept_acknowledgment: true,
      });
      // Persist tokens + tell auth store to load the newly-created user.
      setTokens(res.access_token, res.refresh_token);
      markComplete();
      // Mark the ack as already recorded so AppLayout's modal doesn't fire.
      try {
        localStorage.setItem(SETUP_ACK_LOCAL_KEY, '1');
      } catch {
        /* Storage unavailable — modal will fire and immediately accept. */
      }
      await fetchCurrentUser();
      message.success('Setup complete — welcome.');
      navigate('/', { replace: true });
    } catch (e: unknown) {
      setSubmitError(
        extractErrorMessage(
          e,
          'Setup failed. Check your inputs and try again.',
        ),
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Layout style={{ minHeight: '100vh', background: '#0d0d1f' }}>
      <Layout.Content
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
        }}
      >
        <Card
          style={{
            width: '100%',
            maxWidth: 720,
            background: '#141428',
            border: '1px solid #2d2d52',
          }}
          styles={{ body: { padding: 32 } }}
        >
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div>
              <Title level={3} style={{ color: '#fff', marginBottom: 4 }}>
                Welcome to PacketArch
              </Title>
              <Text type="secondary">
                A few one-time questions and you'll be in.
              </Text>
            </div>

            <Steps current={current} size="small" items={stepItems} />

            <div style={{ minHeight: 320 }}>
              {current === 0 && (
                <Step1AdminAccount form={adminForm} initial={admin ?? undefined} />
              )}
              {current === 1 && (
                <Step2SiteIdentity
                  form={siteForm}
                  initial={
                    site ?? {
                      name: '',
                      fqdn: detectedHostname,
                      timezone: detectedTimezone,
                    }
                  }
                />
              )}
              {current === 2 && (
                <Step3Capabilities
                  form={capsForm}
                  initial={capabilities ?? undefined}
                  liveTrafficSupported={liveTrafficSupported}
                />
              )}
              {current === 3 && admin && site && capabilities && (
                <Step4Confirm
                  admin={admin}
                  site={site}
                  capabilities={capabilities}
                  acknowledgmentAccepted={ackAccepted}
                  onAcknowledgmentChange={setAckAccepted}
                />
              )}
            </div>

            {submitError && (
              <Alert
                type="error"
                showIcon
                message={submitError}
                closable
                onClose={() => setSubmitError(null)}
              />
            )}

            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Button onClick={handleBack} disabled={current === 0 || submitting}>
                Back
              </Button>
              {current < 3 ? (
                <Button type="primary" onClick={handleNext}>
                  Next
                </Button>
              ) : (
                <Button
                  type="primary"
                  loading={submitting}
                  disabled={!ackAccepted}
                  onClick={handleSubmit}
                >
                  Complete setup
                </Button>
              )}
            </Space>
          </Space>
        </Card>
      </Layout.Content>
    </Layout>
  );
};

export default SetupWizardPage;
