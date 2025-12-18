/**
 * PCAP Learning Help Article
 */

import React from 'react';
import { Typography, Space, Card, Steps, Tag, Divider, Alert } from 'antd';
import {
  ExperimentOutlined,
  UploadOutlined,
  ScanOutlined,
  BulbOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const PcapLearningContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <ExperimentOutlined style={{ marginRight: 8, color: '#049FD9' }} />
          PCAP Learning
        </Title>
        <Paragraph style={{ color: '#8aa4bc', fontSize: 15 }}>
          Learn traffic patterns from real PCAP captures to make your simulated traffic more
          realistic. The learning system extracts timing patterns, protocol behaviors, device
          fingerprints, and command sequences from captured network traffic.
        </Paragraph>
      </div>

      <Alert
        type="info"
        showIcon
        message="Why Use PCAP Learning?"
        description="Real industrial traffic has unique timing patterns, polling intervals, and protocol behaviors. Learning from actual captures ensures your simulated traffic closely matches production environments."
        style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}
      />

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Learning Workflow
        </Title>
        <Steps
          direction="vertical"
          current={-1}
          items={[
            {
              title: <Text style={{ color: '#fff' }}>Upload PCAP Files</Text>,
              description: (
                <Text style={{ color: '#8aa4bc' }}>
                  Drag and drop or select PCAP/PCAPNG files containing OT protocol traffic.
                  Files are deduplicated by hash to avoid redundant processing.
                </Text>
              ),
              icon: <UploadOutlined style={{ color: '#049FD9' }} />,
            },
            {
              title: <Text style={{ color: '#fff' }}>Automatic Analysis</Text>,
              description: (
                <Text style={{ color: '#8aa4bc' }}>
                  The system processes uploads in the background, extracting timing patterns,
                  protocol behaviors, and device fingerprints.
                </Text>
              ),
              icon: <ScanOutlined style={{ color: '#049FD9' }} />,
            },
            {
              title: <Text style={{ color: '#fff' }}>Review Patterns</Text>,
              description: (
                <Text style={{ color: '#8aa4bc' }}>
                  Browse extracted patterns across tabs: Timing, Protocols, Fingerprints, and Sequences.
                  Each pattern includes confidence scores and statistics.
                </Text>
              ),
              icon: <BulbOutlined style={{ color: '#049FD9' }} />,
            },
            {
              title: <Text style={{ color: '#fff' }}>Apply to Scenarios</Text>,
              description: (
                <Text style={{ color: '#8aa4bc' }}>
                  Use learned patterns when creating scenarios from templates or apply them
                  to existing devices for more realistic traffic.
                </Text>
              ),
              icon: <RocketOutlined style={{ color: '#049FD9' }} />,
            },
          ]}
        />
      </Card>

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          What Gets Learned
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Tag color="blue" style={{ marginBottom: 4 }}>Timing Patterns</Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Inter-packet delays, polling intervals with statistical distributions
              (mean, standard deviation, min/max). Creates realistic timing jitter.
            </Paragraph>
          </div>
          <div>
            <Tag color="green" style={{ marginBottom: 4 }}>Protocol Patterns</Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Function code usage, address ranges, request/response pairs, data sizes.
              Captures how protocols are actually used in the field.
            </Paragraph>
          </div>
          <div>
            <Tag color="orange" style={{ marginBottom: 4 }}>Device Fingerprints</Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              TCP signatures, response timings, inferred vendors, device roles.
              Helps identify master vs. slave devices.
            </Paragraph>
          </div>
          <div>
            <Tag color="purple" style={{ marginBottom: 4 }}>Command Sequences</Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Startup sequences, shutdown procedures, poll cycles, write operations.
              Captures the order of operations in real systems.
            </Paragraph>
          </div>
        </Space>
      </Card>

      <Divider style={{ borderColor: '#2a3f54' }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Supported Protocols
        </Title>
        <Space wrap>
          <Tag color="blue">Modbus TCP</Tag>
          <Tag color="green">EtherNet/IP</Tag>
          <Tag color="orange">PROFINET</Tag>
        </Space>
        <Paragraph style={{ color: '#8aa4bc', marginTop: 12 }}>
          The learning system identifies protocols automatically based on port numbers
          and protocol signatures.
        </Paragraph>
      </div>

      <Divider style={{ borderColor: '#2a3f54' }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Learning Stats Dashboard
        </Title>
        <Paragraph style={{ color: '#8aa4bc' }}>
          The dashboard shows overall statistics:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ color: '#fff' }}>PCAPs Processed</Text>
            <Text style={{ color: '#6b6b8a' }}> - Total files analyzed</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Timing Patterns</Text>
            <Text style={{ color: '#6b6b8a' }}> - Unique timing models learned</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Device Fingerprints</Text>
            <Text style={{ color: '#6b6b8a' }}> - Unique devices identified</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Sequences</Text>
            <Text style={{ color: '#6b6b8a' }}> - Command patterns extracted</Text>
          </div>
        </Space>
      </div>

      <Alert
        type="warning"
        showIcon
        message="Processing Time"
        description="Large PCAP files may take several minutes to process. You can continue using the application while processing runs in the background."
        style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}
      />
    </Space>
  );
};

export const pcapLearningArticle: HelpArticle = {
  id: 'pcap-learning',
  title: 'PCAP Learning',
  category: 'traffic-generation',
  keywords: [
    'pcap', 'learning', 'capture', 'analyze', 'pattern', 'timing', 'fingerprint',
    'upload', 'extract', 'realistic', 'traffic'
  ],
  summary: 'Learn traffic patterns from real PCAP captures to create more realistic simulations.',
  content: PcapLearningContent,
  relatedArticles: ['deployments', 'templates'],
  relatedPages: ['/learning'],
  order: 2,
};
