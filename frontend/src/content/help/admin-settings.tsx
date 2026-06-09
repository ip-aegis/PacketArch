/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Admin Settings Help Article
 */

import React from 'react';
import { Typography, Space, Card, Tag, Divider, Alert } from 'antd';
import {
  SettingOutlined,
  RobotOutlined,
  UserOutlined,
  EyeOutlined,
  IdcardOutlined,
  DownloadOutlined,
  FileOutlined,
  CloudUploadOutlined,
  DashboardOutlined,
} from '@ant-design/icons';
import type { HelpArticle } from './index';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, BG_INSET, CARD_STYLE } from '../../constants/theme';

const { Title, Paragraph, Text } = Typography;

const AdminSettingsContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <SettingOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Admin Settings
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          Configure system-wide settings: AI providers and spend tracking, Cisco Cyber
          Vision, LDAP / Active Directory, user accounts, downloads, generated PCAPs,
          and system updates. Admin access required.
        </Paragraph>
      </div>

      <Alert
        type="info"
        showIcon
        message="Administrator Access"
        description="The Settings page is only visible to users with administrator privileges. Traffic agents are managed on the Agents page (sidebar), not here."
        style={CARD_STYLE}
      />

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Settings Tabs
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Tag color="geekblue" icon={<DashboardOutlined />} style={{ marginBottom: 4 }}>
              Overview
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Status dashboard for every subsystem (AI, Cyber Vision, LDAP, agents)
              with deep links into the matching tab.
            </Paragraph>
          </div>

          <div>
            <Tag color="purple" icon={<RobotOutlined />} style={{ marginBottom: 4 }}>
              AI Integrations
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Three sub-tabs: <Text strong style={{ color: '#fff' }}>Provider</Text> (choose
              and configure the AI provider), <Text strong style={{ color: '#fff' }}>Usage</Text>{' '}
              (token consumption per task), and <Text strong style={{ color: '#fff' }}>Costs</Text>{' '}
              (spend breakdown over time).
            </Paragraph>
          </div>

          <div>
            <Tag color="green" style={{ marginBottom: 4 }}>
              System
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              System-level configuration values, version details, and general
              application settings.
            </Paragraph>
          </div>

          <div>
            <Tag color="cyan" icon={<EyeOutlined />} style={{ marginBottom: 4 }}>
              Cyber Vision
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Connect to a Cisco Cyber Vision Center (URL + API token) to enable
              device comparison, matching, and enrichment.
            </Paragraph>
          </div>

          <div>
            <Tag color="volcano" icon={<IdcardOutlined />} style={{ marginBottom: 4 }}>
              LDAP / AD
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Configure LDAP / Active Directory authentication so users can sign in
              with directory credentials.
            </Paragraph>
          </div>

          <div>
            <Tag color="red" icon={<UserOutlined />} style={{ marginBottom: 4 }}>
              User Management
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Create users, grant or revoke admin privileges, and deactivate accounts.
            </Paragraph>
          </div>

          <div>
            <Tag color="blue" icon={<DownloadOutlined />} style={{ marginBottom: 4 }}>
              Downloads
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              The portable scenario authoring kit: LLM prompt, scenario format spec,
              JSON schema, and a fingerprint registry snapshot for authoring
              scenarios outside PacketArch.
            </Paragraph>
          </div>

          <div>
            <Tag color="gold" icon={<FileOutlined />} style={{ marginBottom: 4 }}>
              Generated PCAPs
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Browse, download, and clean up PCAP files produced by generation jobs.
            </Paragraph>
          </div>

          <div>
            <Tag color="magenta" icon={<CloudUploadOutlined />} style={{ marginBottom: 4 }}>
              Updates
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              View the installed version and run system upgrades.
            </Paragraph>
          </div>
        </Space>
      </Card>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <RobotOutlined style={{ marginRight: 8 }} />
          AI Provider Configuration
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          AI powers scenario generation, the Studio assistant, device naming, scenario
          review, and contextual help. Pick one of three providers:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%', marginTop: 12 }}>
          <div>
            <Text strong style={{ color: '#fff' }}>Anthropic (Claude)</Text>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 8 }}>
              Recommended for OT/ICS expertise. Requires an Anthropic API key.
            </Paragraph>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>OpenAI (GPT)</Text>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 8 }}>
              Alternative with broad capabilities. Requires an OpenAI API key.
            </Paragraph>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Cisco CIRCUIT</Text>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 8 }}>
              Cisco's internal AI platform with models from multiple vendors.
              Requires Client ID, Client Secret, and App Key.
            </Paragraph>
          </div>
        </Space>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 8 }}>
          You pick the provider; PacketArch automatically routes each task type
          (chat, scenario generation, naming, review, help) to an appropriate model
          for that provider. The routing table is shown on the Provider tab, and an
          Advanced section allows a manual model override.
        </Paragraph>
        <Alert
          type="warning"
          showIcon
          message="Test Connection"
          description="Use the 'Test Connection' button to verify your credentials work before saving."
          style={{ background: BG_INSET, border: `1px solid ${BORDER_DEFAULT}`, marginTop: 12 }}
        />
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <UserOutlined style={{ marginRight: 8 }} />
          User Management
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ color: '#fff' }}>Create User</Text>
            <Text style={{ color: '#6b6b8a' }}> - Add new user with username and password</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Admin Privileges</Text>
            <Text style={{ color: '#6b6b8a' }}> - Grant access to settings page</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Deactivate</Text>
            <Text style={{ color: '#6b6b8a' }}> - Disable user login without deleting</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>LDAP / AD</Text>
            <Text style={{ color: '#6b6b8a' }}> - Directory users sign in once LDAP is configured</Text>
          </div>
        </Space>
      </Card>
    </Space>
  );
};

export const adminSettingsArticle: HelpArticle = {
  id: 'admin-settings',
  title: 'Admin Settings',
  category: 'administration',
  keywords: [
    'admin', 'settings', 'configuration', 'ai', 'provider', 'model routing',
    'usage', 'costs', 'cyber vision', 'ldap', 'active directory', 'user',
    'management', 'anthropic', 'openai', 'circuit', 'downloads', 'pcap', 'updates'
  ],
  summary: 'Configure AI providers, Cyber Vision, LDAP/AD, users, downloads, generated PCAPs, and updates.',
  content: AdminSettingsContent,
  relatedArticles: ['agents-hub', 'cyber-vision'],
  relatedPages: ['/admin/settings'],
  order: 1,
};
