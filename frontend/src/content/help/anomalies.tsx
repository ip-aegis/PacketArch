/**
 * Anomaly Injection Help Article
 */

import React from 'react';
import { Typography, Space, Card, Table, Tag, Divider, Alert } from 'antd';
import {
  WarningOutlined,
  ClockCircleOutlined,
  ApiOutlined,
  OrderedListOutlined,
  FileTextOutlined,
  GlobalOutlined,
  LockOutlined,
} from '@ant-design/icons';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const AnomaliesContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <WarningOutlined style={{ marginRight: 8, color: '#049FD9' }} />
          Anomaly Injection
        </Title>
        <Paragraph style={{ color: '#8aa4bc', fontSize: 15 }}>
          Inject anomalies into your traffic scenarios to test security monitoring,
          detection systems, and incident response procedures. Create realistic
          attack simulations and protocol violations.
        </Paragraph>
      </div>

      <Alert
        type="warning"
        showIcon
        icon={<LockOutlined />}
        message="Authorized Testing Only"
        description="Anomaly injection is intended for authorized security testing on networks you own or have permission to test. Never use these features on production systems without proper authorization."
        style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}
      />

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Anomaly Categories
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Tag color="blue" icon={<ClockCircleOutlined />} style={{ marginBottom: 4 }}>
              Timing Anomalies
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Unusual polling intervals, traffic bursts, unexpected timing patterns.
              Tests detection of operational changes.
            </Paragraph>
          </div>

          <div>
            <Tag color="orange" icon={<ApiOutlined />} style={{ marginBottom: 4 }}>
              Protocol Anomalies
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Invalid function codes, malformed packets, protocol violations.
              Tests protocol-aware intrusion detection.
            </Paragraph>
          </div>

          <div>
            <Tag color="purple" icon={<OrderedListOutlined />} style={{ marginBottom: 4 }}>
              Sequence Anomalies
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Out-of-order commands, unexpected state transitions, unauthorized operations.
              Tests behavioral analysis systems.
            </Paragraph>
          </div>

          <div>
            <Tag color="cyan" icon={<FileTextOutlined />} style={{ marginBottom: 4 }}>
              Payload Anomalies
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Unusual data values, out-of-range parameters, suspicious payloads.
              Tests content inspection capabilities.
            </Paragraph>
          </div>

          <div>
            <Tag color="green" icon={<GlobalOutlined />} style={{ marginBottom: 4 }}>
              Network Anomalies
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Port scanning, network enumeration, broadcast storms.
              Tests network-level detection.
            </Paragraph>
          </div>

          <div>
            <Tag color="red" icon={<LockOutlined />} style={{ marginBottom: 4 }}>
              Security Anomalies
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Authentication failures, privilege escalation attempts, known exploits.
              Tests security-specific detection rules.
            </Paragraph>
          </div>
        </Space>
      </Card>

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Severity Levels
        </Title>
        <Table
          size="small"
          pagination={false}
          dataSource={[
            { level: 'Low', color: 'green', desc: 'Minor deviations, often benign', example: 'Slightly unusual timing' },
            { level: 'Medium', color: 'gold', desc: 'Noticeable anomalies worth investigating', example: 'Unexpected function codes' },
            { level: 'High', color: 'orange', desc: 'Significant deviations from normal', example: 'Write to unusual addresses' },
            { level: 'Critical', color: 'red', desc: 'Clear security concern', example: 'Known exploit patterns' },
          ]}
          columns={[
            {
              title: 'Level',
              dataIndex: 'level',
              render: (text, record) => <Tag color={record.color}>{text}</Tag>,
              width: 90,
            },
            {
              title: 'Description',
              dataIndex: 'desc',
              render: (text) => <Text style={{ color: '#8aa4bc' }}>{text}</Text>,
            },
            {
              title: 'Example',
              dataIndex: 'example',
              render: (text) => <Text style={{ color: '#6b6b8a' }}>{text}</Text>,
            },
          ]}
          style={{ background: 'transparent' }}
          rowKey="level"
        />
      </Card>

      <Divider style={{ borderColor: '#2a3f54' }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          External Communications
        </Title>
        <Paragraph style={{ color: '#8aa4bc' }}>
          Simulate malicious external communications for advanced threat detection testing:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Tag color="red">C2 Beacons</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Simulated command-and-control callback patterns
            </Text>
          </div>
          <div>
            <Tag color="orange">Data Exfiltration</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Simulated data theft patterns
            </Text>
          </div>
          <div>
            <Tag color="purple">Port Scanning</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Network reconnaissance simulation
            </Text>
          </div>
        </Space>
        <Paragraph style={{ color: '#6b6b8a', marginTop: 12, fontSize: 12 }}>
          External IPs use RFC 5737 TEST-NET ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24)
          to avoid accidental real connections.
        </Paragraph>
      </div>

      <Divider style={{ borderColor: '#2a3f54' }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Anomaly Campaigns
        </Title>
        <Paragraph style={{ color: '#8aa4bc' }}>
          Group anomalies into campaigns for coordinated injection:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ color: '#fff' }}>Scheduled Timing</Text>
            <Text style={{ color: '#6b6b8a' }}> - Inject anomalies at specific times in the scenario</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Probability-Based</Text>
            <Text style={{ color: '#6b6b8a' }}> - Random injection with configurable probability</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>MITRE ATT&CK Mapping</Text>
            <Text style={{ color: '#6b6b8a' }}> - Tag anomalies with relevant techniques</Text>
          </div>
        </Space>
      </div>

      <Alert
        type="info"
        showIcon
        message="Testing Workflow"
        description="1. Create scenario with normal traffic. 2. Add anomaly campaign. 3. Deploy and monitor with security tools. 4. Verify detection and alerting."
        style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}
      />
    </Space>
  );
};

export const anomaliesArticle: HelpArticle = {
  id: 'anomalies',
  title: 'Anomaly Injection',
  category: 'security-testing',
  keywords: [
    'anomaly', 'injection', 'security', 'testing', 'attack', 'simulation',
    'detection', 'timing', 'protocol', 'violation', 'c2', 'beacon'
  ],
  summary: 'Inject anomalies for security testing including timing violations, protocol attacks, and more.',
  content: AnomaliesContent,
  relatedArticles: ['cve-browser', 'deployments'],
  relatedPages: [],
  order: 2,
};
