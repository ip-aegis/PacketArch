/**
 * Deployments Help Article
 */

import React from 'react';
import { Typography, Space, Card, Table, Tag, Divider, Alert } from 'antd';
import {
  CloudServerOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  DownloadOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const DeploymentsContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <CloudServerOutlined style={{ marginRight: 8, color: '#049FD9' }} />
          Deployments
        </Title>
        <Paragraph style={{ color: '#8aa4bc', fontSize: 15 }}>
          Deploy your scenarios to generate traffic. Choose between generating PCAP files
          for offline analysis or injecting live traffic onto a network interface.
        </Paragraph>
      </div>

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Deployment Modes
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Tag color="blue" style={{ marginBottom: 4 }}>
              <ClockCircleOutlined /> Timed
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Run for a specific duration (from scenario settings). Automatically stops
              when the duration is reached. Best for generating specific capture files.
            </Paragraph>
          </div>
          <div>
            <Tag color="green" style={{ marginBottom: 4 }}>
              <SyncOutlined /> Perpetual
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Run continuously until manually stopped. Use for ongoing traffic simulation
              or security monitoring validation.
            </Paragraph>
          </div>
        </Space>
      </Card>

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Starting a Deployment
        </Title>
        <ol style={{ color: '#8aa4bc', paddingLeft: 20 }}>
          <li>Open a scenario in Scenario Studio</li>
          <li>Click the "Deploy" button in the toolbar</li>
          <li>Select the Docker host (where traffic will be generated)</li>
          <li>Choose the network interface</li>
          <li>Select deployment mode (Timed or Perpetual)</li>
          <li>Click "Start Deployment"</li>
        </ol>
        <Alert
          type="info"
          showIcon
          message="Validation"
          description="The scenario is validated before deployment. Issues like missing IP addresses or incomplete flows must be fixed first."
          style={{ background: '#152330', border: '1px solid #2a3f54', marginTop: 12 }}
        />
      </Card>

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
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
              render: (text) => <Text style={{ color: '#8aa4bc' }}>{text}</Text>,
            },
          ]}
          style={{ background: 'transparent' }}
          rowKey="status"
        />
      </Card>

      <Divider style={{ borderColor: '#2a3f54' }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Deployment Actions
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Tag color="blue">
              <FileTextOutlined /> View Logs
            </Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Stream real-time logs from the traffic generator
            </Text>
          </div>
          <div>
            <Tag color="green">
              <DownloadOutlined /> Download PCAP
            </Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Download generated capture file (available after completion)
            </Text>
          </div>
          <div>
            <Tag color="orange">
              <PauseCircleOutlined /> Stop
            </Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Stop a running deployment gracefully
            </Text>
          </div>
          <div>
            <Tag color="red">Remove</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Remove a completed/failed deployment from the list
            </Text>
          </div>
        </Space>
      </div>

      <Divider style={{ borderColor: '#2a3f54' }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Docker Hosts
        </Title>
        <Paragraph style={{ color: '#8aa4bc' }}>
          Traffic is generated on Docker hosts configured in Admin Settings. Each host can
          inject traffic on any of its network interfaces. Configure hosts with:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ color: '#fff' }}>Host Address</Text>
            <Text style={{ color: '#6b6b8a' }}> - IP or hostname of Docker host</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Docker API Port</Text>
            <Text style={{ color: '#6b6b8a' }}> - Usually 2375 (TCP) or 2376 (TLS)</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>TLS Certificates</Text>
            <Text style={{ color: '#6b6b8a' }}> - Optional for secure connections</Text>
          </div>
        </Space>
      </div>

      <Alert
        type="warning"
        showIcon
        message="Network Impact"
        description="Live traffic injection will send packets onto the selected network interface. Ensure you have authorization to inject traffic on the target network."
        style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}
      />
    </Space>
  );
};

export const deploymentsArticle: HelpArticle = {
  id: 'deployments',
  title: 'Deployments',
  category: 'traffic-generation',
  keywords: [
    'deploy', 'deployment', 'generate', 'traffic', 'pcap', 'run', 'start',
    'stop', 'download', 'logs', 'docker', 'host', 'interface'
  ],
  summary: 'Deploy scenarios to generate PCAP files or inject live traffic onto network interfaces.',
  content: DeploymentsContent,
  relatedArticles: ['scenarios', 'scenario-studio', 'admin-settings'],
  relatedPages: ['/deployments'],
  order: 1,
};
