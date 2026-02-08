/**
 * IP Management Help Article
 */

import React from 'react';
import { Typography, Space, Card, Table, Divider, Alert } from 'antd';
import {
  GlobalOutlined,
  NumberOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, CARD_STYLE } from '../../constants/theme';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const IPManagementContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <GlobalOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          IP Management
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          PacketArch automatically manages IP address allocation to prevent conflicts between
          scenarios. Each scenario receives a unique /16 network range.
        </Paragraph>
      </div>

      <Alert
        type="info"
        showIcon
        message="Automatic Allocation"
        description="IP ranges are automatically assigned when you create a scenario. You don't need to manually configure IP addresses unless you want to override the defaults."
        style={CARD_STYLE}
      />

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          How IP Allocation Works
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <div style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: ACCENT_BLUE,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Text style={{ color: '#fff', fontWeight: 600 }}>1</Text>
            </div>
            <div>
              <Text strong style={{ color: '#fff' }}>Scenario Gets /16 Range</Text>
              <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
                Each scenario is assigned a unique <Text code>10.X.0.0/16</Text> range,
                where X is 1-254. This provides 65,534 usable addresses per scenario.
              </Paragraph>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <div style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: ACCENT_BLUE,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Text style={{ color: '#fff', fontWeight: 600 }}>2</Text>
            </div>
            <div>
              <Text strong style={{ color: '#fff' }}>Zones Use /24 Subnets</Text>
              <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
                Network zones within a scenario use <Text code>10.X.Y.0/24</Text> subnets.
                The gateway is always .1 (e.g., 10.X.Y.1).
              </Paragraph>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <div style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: ACCENT_BLUE,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Text style={{ color: '#fff', fontWeight: 600 }}>3</Text>
            </div>
            <div>
              <Text strong style={{ color: '#fff' }}>Hosts Start at .10</Text>
              <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
                Device IPs start at .10 within each subnet (e.g., 10.X.Y.10, 10.X.Y.11).
                Reserved: .0 (network), .1 (gateway), .255 (broadcast).
              </Paragraph>
            </div>
          </div>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          IP Range Allocation Table
        </Title>
        <Table
          size="small"
          pagination={false}
          dataSource={[
            { range: '10.1.0.0/16', scenario: 'First scenario created' },
            { range: '10.2.0.0/16', scenario: 'Second scenario created' },
            { range: '10.3.0.0/16', scenario: 'Third scenario created' },
            { range: '...', scenario: '...' },
            { range: '10.254.0.0/16', scenario: 'Maximum 254 scenarios' },
          ]}
          columns={[
            {
              title: 'IP Range',
              dataIndex: 'range',
              render: (text) => <Text code style={{ color: ACCENT_BLUE }}>{text}</Text>,
            },
            {
              title: 'Allocation',
              dataIndex: 'scenario',
              render: (text) => <Text style={{ color: TEXT_PARAGRAPH }}>{text}</Text>,
            },
          ]}
          style={{ background: 'transparent' }}
          rowKey="range"
        />
      </Card>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          IP Management Page
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          The IP Management page shows:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircleOutlined style={{ color: '#6CC04A' }} />
            <Text style={{ color: TEXT_PARAGRAPH }}>Summary statistics (allocated, available, usage %)</Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircleOutlined style={{ color: '#6CC04A' }} />
            <Text style={{ color: TEXT_PARAGRAPH }}>Table of all IP allocations by scenario</Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircleOutlined style={{ color: '#6CC04A' }} />
            <Text style={{ color: TEXT_PARAGRAPH }}>Next available host offset per range</Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircleOutlined style={{ color: '#6CC04A' }} />
            <Text style={{ color: TEXT_PARAGRAPH }}>Links to view each scenario</Text>
          </div>
        </Space>
      </div>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Special Cases
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ color: '#fff' }}>Duplicating Scenarios</Text>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 8 }}>
              Duplicated scenarios receive a new IP range. Device IPs are automatically
              remapped to the new range.
            </Paragraph>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Importing Scenarios</Text>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 8 }}>
              Imported scenarios receive a new IP range. IPs from the original export
              are remapped to avoid conflicts.
            </Paragraph>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Deleting Scenarios</Text>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 8 }}>
              When a scenario is deleted, its IP range becomes available for reuse
              by future scenarios.
            </Paragraph>
          </div>
        </Space>
      </div>
    </Space>
  );
};

export const ipManagementArticle: HelpArticle = {
  id: 'ip-management',
  title: 'IP Management',
  category: 'traffic-generation',
  keywords: [
    'ip', 'address', 'range', 'allocation', 'subnet', 'network', 'cidr',
    'conflict', 'automatic', 'management'
  ],
  summary: 'Understand how PacketArch automatically manages IP address allocation for scenarios.',
  content: IPManagementContent,
  relatedArticles: ['scenarios', 'scenario-studio'],
  relatedPages: ['/ip-management'],
  order: 3,
};
