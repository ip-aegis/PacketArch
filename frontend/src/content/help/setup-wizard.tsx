/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Setup Wizard Help Article
 */

import React from 'react';
import { Typography, Space, Card, Alert, Steps } from 'antd';
import {
  RocketOutlined,
  UserOutlined,
  EnvironmentOutlined,
  ApiOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { TEXT_PARAGRAPH, ACCENT_BLUE, CARD_STYLE } from '../../constants/theme';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const SetupWizardContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <RocketOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          First-Run Setup Wizard
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          The setup wizard runs once on a fresh PacketArch install, before any user accounts exist.
          It gates the entire application until you create the first admin account and configure
          site identity. Existing installs auto-graduate past the wizard on backend boot.
        </Paragraph>
      </div>

      <Alert
        type="warning"
        showIcon
        message="One-shot, security-sensitive"
        description="Whoever lands on /setup first claims the admin account. On a publicly reachable install, complete setup immediately after deployment."
        style={CARD_STYLE}
      />

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          The 4 Steps
        </Title>
        <Steps
          direction="vertical"
          current={-1}
          items={[
            {
              title: <Text style={{ color: '#fff' }}>1. Admin Account</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Create the first user — username, email, password. This account is marked admin and used to manage all other settings.</Text>,
              icon: <UserOutlined />,
            },
            {
              title: <Text style={{ color: '#fff' }}>2. Site Identity</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Set the site name (appears in the top bar), the FQDN (used in URLs and emails), and the default timezone for scheduling and logs.</Text>,
              icon: <EnvironmentOutlined />,
            },
            {
              title: <Text style={{ color: '#fff' }}>3. Capabilities</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Optionally wire up AI (Claude/CIRCUIT API key) and Cisco Cyber Vision (URL + token). Both can be skipped now and configured later under Settings.</Text>,
              icon: <ApiOutlined />,
            },
            {
              title: <Text style={{ color: '#fff' }}>4. Confirm</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Review and accept the GPL-3.0 license acknowledgment. Completion flips setup.completed=true and unlocks the rest of the app.</Text>,
              icon: <CheckCircleOutlined />,
            },
          ]}
        />
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Re-running the Wizard
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          If the initial setup was compromised or you need to start over (loss of admin password
          with no recovery, etc.), an operator with database access can reset it:
        </Paragraph>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontFamily: 'monospace', fontSize: 12 }}>
          docker compose exec postgres psql -U packetarch -d packetarch -c \<br />
          &nbsp;&nbsp;"DELETE FROM users; UPDATE system_settings SET value='false' WHERE key='setup.completed';"<br />
          docker compose restart backend
        </Paragraph>
      </Card>

      <Alert
        type="info"
        showIcon
        message="What the wizard locks until done"
        description="Until setup.completed flips to true, every API except /api/v1/setup/*, /api/v1/about, and /health returns 503. The frontend redirects all routes to /setup."
        style={CARD_STYLE}
      />
    </Space>
  );
};

export const setupWizardArticle: HelpArticle = {
  id: 'setup-wizard',
  title: 'First-Run Setup Wizard',
  category: 'getting-started',
  keywords: [
    'setup', 'wizard', 'first run', 'install', 'admin', 'account', 'site',
    'fqdn', 'capabilities', 'license', 'eula', 'reset'
  ],
  summary: 'The 4-step onboarding flow that runs once per install to create the admin account and configure site identity.',
  content: SetupWizardContent,
  relatedArticles: ['getting-started', 'admin-settings'],
  relatedPages: [],
  order: 2,
};
