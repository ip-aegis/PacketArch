/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Deployments Help Article
 */

import React from 'react';
import { Typography, Space, Card, Table, Tag, Divider, Alert } from 'antd';
import {
  CloudServerOutlined,
  PauseCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import type { HelpArticle } from './index';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, BG_INSET, CARD_STYLE } from '../../constants/theme';

const { Title, Paragraph, Text } = Typography;

const DeploymentsContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <CloudServerOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Deployments
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          Deploy your scenarios to generate traffic. Choose between generating PCAP files
          for offline analysis or injecting live traffic onto a network interface.
        </Paragraph>
      </div>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Deployment Modes
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Tag color="blue" style={{ marginBottom: 4 }}>
              <ClockCircleOutlined /> Timed
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Run for a specific duration (from scenario settings). Automatically stops
              when the duration is reached. Best for generating specific capture files.
            </Paragraph>
          </div>
          <div>
            <Tag color="green" style={{ marginBottom: 4 }}>
              <SyncOutlined /> Perpetual
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Run continuously until manually stopped. Use for ongoing traffic simulation
              or security monitoring validation.
            </Paragraph>
          </div>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Starting a Deployment
        </Title>
        <ol style={{ color: TEXT_PARAGRAPH, paddingLeft: 20 }}>
          <li>Open a scenario in Scenario Studio</li>
          <li>Click the "Deploy" tab in the right panel</li>
          <li>Select a traffic agent</li>
          <li>Choose the network interface</li>
          <li>Optionally configure phase scheduling</li>
          <li>Click "Deploy"</li>
        </ol>
        <Alert
          type="info"
          showIcon
          message="Validation"
          description="The scenario is validated before deployment. Issues like missing IP addresses or incomplete flows must be fixed first."
          style={{ background: BG_INSET, border: `1px solid ${BORDER_DEFAULT}`, marginTop: 12 }}
        />
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Deployment Status
        </Title>
        <Table
          size="small"
          pagination={false}
          dataSource={[
            { status: 'Pending', color: 'default', desc: 'Queued for execution' },
            { status: 'Starting', color: 'processing', desc: 'Container initializing' },
            { status: 'Running', color: 'success', desc: 'Traffic generation in progress' },
            { status: 'Stopping', color: 'warning', desc: 'Graceful shutdown in progress' },
            { status: 'Completed', color: 'default', desc: 'Finished successfully' },
            { status: 'Failed', color: 'error', desc: 'Error occurred - check logs' },
          ]}
          columns={[
            {
              title: 'Status',
              dataIndex: 'status',
              render: (text, record) => <Tag color={record.color}>{text}</Tag>,
              width: 120,
            },
            {
              title: 'Description',
              dataIndex: 'desc',
              render: (text) => <Text style={{ color: TEXT_PARAGRAPH }}>{text}</Text>,
            },
          ]}
          style={{ background: 'transparent' }}
          rowKey="status"
        />
      </Card>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Deployment Actions
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Tag color="orange">
              <PauseCircleOutlined /> Stop
            </Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Stop a running deployment gracefully
            </Text>
          </div>
          <div>
            <Tag color="red">Remove</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Remove a completed/failed deployment from the list
            </Text>
          </div>
        </Space>
      </div>

      <Alert
        type="warning"
        showIcon
        message="Network Impact"
        description="Live traffic injection will send packets onto the selected network interface. Ensure you have authorization to inject traffic on the target network."
        style={CARD_STYLE}
      />
    </Space>
  );
};

export const deploymentsArticle: HelpArticle = {
  id: 'deployments',
  title: 'Deployments',
  category: 'traffic-generation',
  keywords: [
    'deploy', 'deployment', 'generate', 'traffic', 'run', 'start',
    'stop', 'agent', 'interface'
  ],
  summary: 'Deploy scenarios to traffic agents for live traffic injection onto network interfaces.',
  content: DeploymentsContent,
  relatedArticles: ['scenarios', 'scenario-studio', 'admin-settings'],
  relatedPages: [],
  order: 1,
};
