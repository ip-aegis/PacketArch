/**
 * Admin Settings Help Article
 */

import React from 'react';
import { Typography, Space, Card, Tag, Divider, Alert } from 'antd';
import {
  SettingOutlined,
  KeyOutlined,
  RobotOutlined,
  CloudServerOutlined,
  UserOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const AdminSettingsContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <SettingOutlined style={{ marginRight: 8, color: '#049FD9' }} />
          Admin Settings
        </Title>
        <Paragraph style={{ color: '#8aa4bc', fontSize: 15 }}>
          Configure system-wide settings including AI providers, Docker hosts, user
          management, and default configurations. Admin access required.
        </Paragraph>
      </div>

      <Alert
        type="info"
        showIcon
        message="Administrator Access"
        description="The Settings page is only visible to users with administrator privileges."
        style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}
      />

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Settings Tabs
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Tag color="blue" icon={<KeyOutlined />} style={{ marginBottom: 4 }}>
              API Tokens
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Manage API tokens for programmatic access to PacketArch. Create, view,
              and revoke tokens.
            </Paragraph>
          </div>

          <div>
            <Tag color="purple" icon={<RobotOutlined />} style={{ marginBottom: 4 }}>
              AI Provider
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Configure the AI provider for natural language scenario generation.
              Choose between Anthropic (Claude) or OpenAI (GPT). Enter API keys
              and select models.
            </Paragraph>
          </div>

          <div>
            <Tag color="cyan" style={{ marginBottom: 4 }}>
              Network Defaults
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Set default network configuration values for new scenarios, including
              default IP ranges and subnet masks.
            </Paragraph>
          </div>

          <div>
            <Tag color="green" style={{ marginBottom: 4 }}>
              System
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              View system information, version details, and general application settings.
            </Paragraph>
          </div>

          <div>
            <Tag color="orange" icon={<CloudServerOutlined />} style={{ marginBottom: 4 }}>
              Docker Hosts
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Configure remote Docker hosts for traffic generation. Add, edit, and
              test connectivity to Docker endpoints.
            </Paragraph>
          </div>

          <div>
            <Tag color="red" icon={<UserOutlined />} style={{ marginBottom: 4 }}>
              Users
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Manage user accounts. Create new users, set admin privileges,
              and deactivate accounts.
            </Paragraph>
          </div>

          <div>
            <Tag color="gold" icon={<DatabaseOutlined />} style={{ marginBottom: 4 }}>
              Seed Data
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Initialize or reset database with default data including device profiles,
              vendor fingerprints, and CVE entries.
            </Paragraph>
          </div>
        </Space>
      </Card>

      <Divider style={{ borderColor: '#2a3f54' }} />

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <RobotOutlined style={{ marginRight: 8 }} />
          AI Provider Configuration
        </Title>
        <Paragraph style={{ color: '#8aa4bc' }}>
          The AI assistant uses natural language processing to help create scenarios.
          Configure your preferred provider:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%', marginTop: 12 }}>
          <div>
            <Text strong style={{ color: '#fff' }}>Anthropic (Claude)</Text>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 8 }}>
              Recommended. Supports Claude 3.5 Sonnet, Claude 3 Opus, and other models.
              Enter your Anthropic API key.
            </Paragraph>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>OpenAI (GPT)</Text>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 8 }}>
              Alternative option. Supports GPT-4, GPT-4 Turbo, and GPT-3.5 Turbo.
              Enter your OpenAI API key.
            </Paragraph>
          </div>
        </Space>
        <Alert
          type="warning"
          showIcon
          message="Test Connection"
          description="Use the 'Test Connection' button to verify your API key works before saving."
          style={{ background: '#152330', border: '1px solid #2a3f54', marginTop: 12 }}
        />
      </Card>

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <CloudServerOutlined style={{ marginRight: 8 }} />
          Docker Host Configuration
        </Title>
        <Paragraph style={{ color: '#8aa4bc' }}>
          Docker hosts are remote machines that run the traffic generator containers.
          Configure each host with:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%', marginTop: 12 }}>
          <div>
            <Text strong style={{ color: '#fff' }}>Name</Text>
            <Text style={{ color: '#6b6b8a' }}> - Friendly identifier for the host</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Host Address</Text>
            <Text style={{ color: '#6b6b8a' }}> - IP address or hostname</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Port</Text>
            <Text style={{ color: '#6b6b8a' }}> - Docker API port (default: 2375 or 2376 for TLS)</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>TLS Enabled</Text>
            <Text style={{ color: '#6b6b8a' }}> - Enable for secure connections</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Certificates</Text>
            <Text style={{ color: '#6b6b8a' }}> - CA cert, client cert, client key (if TLS enabled)</Text>
          </div>
        </Space>
      </Card>

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
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
    'admin', 'settings', 'configuration', 'api', 'token', 'ai', 'provider',
    'docker', 'host', 'user', 'management', 'anthropic', 'openai'
  ],
  summary: 'Configure system settings including AI providers, Docker hosts, and user management.',
  content: AdminSettingsContent,
  relatedArticles: ['deployments'],
  relatedPages: ['/admin/settings'],
  order: 1,
};
