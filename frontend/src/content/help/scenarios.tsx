/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Scenarios Help Article
 */

import React from 'react';
import { Typography, Space, Card, Table, Tag, Divider, Alert } from 'antd';
import {
  FolderOutlined,
  PlusOutlined,
  CopyOutlined,
  DeleteOutlined,
  ExportOutlined,
  ImportOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, CARD_STYLE } from '../../constants/theme';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const ScenariosContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <FolderOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Scenario Management
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          Scenarios are the core building blocks of PacketArch. Each scenario defines a complete
          OT network environment including devices, protocols, communication flows, and traffic patterns.
        </Paragraph>
      </div>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Creating Scenarios
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ color: '#fff' }}>
              <PlusOutlined style={{ marginRight: 8 }} />
              From Template (Recommended)
            </Text>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0, marginTop: 4 }}>
              Select an industry vertical (Manufacturing, Water, Energy, Oil & Gas) and choose
              a pre-built template. Templates include realistic device configurations, protocols,
              and traffic patterns for common industrial scenarios.
            </Paragraph>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>
              <EditOutlined style={{ marginRight: 8 }} />
              Blank Scenario
            </Text>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0, marginTop: 4 }}>
              Start with an empty canvas and add devices manually. Best for custom scenarios
              or when learning how the system works.
            </Paragraph>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>
              <ImportOutlined style={{ marginRight: 8 }} />
              Import from JSON
            </Text>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0, marginTop: 4 }}>
              Import a previously exported scenario. IP addresses are automatically remapped
              to avoid conflicts with existing scenarios.
            </Paragraph>
          </div>
        </Space>
      </Card>

      <Alert
        type="info"
        showIcon
        message="Automatic IP Allocation"
        description="Each scenario automatically receives a unique /16 IP range (10.X.0.0/16). This prevents IP conflicts between scenarios and simplifies network management."
        style={CARD_STYLE}
      />

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Scenario Actions
        </Title>
        <Table
          size="small"
          pagination={false}
          dataSource={[
            { action: 'Edit', icon: <EditOutlined />, desc: 'Open in Scenario Studio canvas editor' },
            { action: 'Duplicate', icon: <CopyOutlined />, desc: 'Create a copy with new IP range allocation' },
            { action: 'Export', icon: <ExportOutlined />, desc: 'Download as JSON file for backup or sharing' },
            { action: 'Delete', icon: <DeleteOutlined />, desc: 'Remove scenario and release IP allocation' },
          ]}
          columns={[
            {
              title: 'Action',
              dataIndex: 'action',
              render: (text, record) => (
                <Space>
                  {record.icon}
                  <Text style={{ color: '#fff' }}>{text}</Text>
                </Space>
              ),
            },
            {
              title: 'Description',
              dataIndex: 'desc',
              render: (text) => <Text style={{ color: TEXT_PARAGRAPH }}>{text}</Text>,
            },
          ]}
          style={{ background: 'transparent' }}
          rowKey="action"
        />
      </Card>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Scenario Properties
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ color: '#fff' }}>Name</Text>
            <Text style={{ color: '#6b6b8a' }}> - Descriptive name for identification</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Description</Text>
            <Text style={{ color: '#6b6b8a' }}> - Optional details about the scenario purpose</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Industry Vertical</Text>
            <Text style={{ color: '#6b6b8a' }}> - Manufacturing, Water, Energy, or Oil & Gas</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Duration</Text>
            <Text style={{ color: '#6b6b8a' }}> - Total time for traffic generation (seconds)</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>IP Range</Text>
            <Text style={{ color: '#6b6b8a' }}> - Auto-assigned /16 network range</Text>
          </div>
        </Space>
      </div>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Industry Verticals
        </Title>
        <Space wrap>
          <Tag color="blue">Manufacturing</Tag>
          <Tag color="cyan">Water/Wastewater</Tag>
          <Tag color="orange">Energy/Power</Tag>
          <Tag color="purple">Oil & Gas</Tag>
        </Space>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 12 }}>
          Each vertical has specific device types, protocols, and traffic patterns that
          reflect real-world industrial environments.
        </Paragraph>
      </div>
    </Space>
  );
};

export const scenariosArticle: HelpArticle = {
  id: 'scenarios',
  title: 'Scenario Management',
  category: 'scenarios',
  keywords: [
    'scenario', 'create', 'edit', 'delete', 'duplicate', 'export', 'import',
    'manage', 'list', 'vertical', 'industry', 'template'
  ],
  summary: 'Create, manage, and organize OT traffic scenarios for different industrial environments.',
  content: ScenariosContent,
  relatedArticles: ['scenario-studio', 'templates', 'ip-management'],
  relatedPages: ['/scenarios'],
  order: 1,
};
