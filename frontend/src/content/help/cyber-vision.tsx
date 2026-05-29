/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Cyber Vision Integration Help Article
 */

import React from 'react';
import { Typography, Space, Card, Alert, Table, Tag } from 'antd';
import { EyeOutlined, LinkOutlined, ApiOutlined, SwapOutlined } from '@ant-design/icons';
import { TEXT_PARAGRAPH, ACCENT_BLUE, CARD_STYLE } from '../../constants/theme';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const CyberVisionContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <EyeOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Cisco Cyber Vision Integration
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          Connect PacketArch to a Cisco Cyber Vision (CV) center to compare your simulated
          scenarios against what CV actually sees on the network, and to enrich simulations
          with components discovered by CV in production.
        </Paragraph>
      </div>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          <LinkOutlined style={{ marginRight: 8 }} />
          Connecting a Center
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Configure your CV connection in <Text strong style={{ color: '#fff' }}>Settings → Cyber Vision</Text>:
          base URL (e.g. <Text code>https://cv-center.example.com</Text>) and an API token
          with read access. The connection is tested before save; check the test result for
          TLS and auth errors.
        </Paragraph>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          <SwapOutlined style={{ marginRight: 8 }} />
          Device Matching
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          PacketArch matches simulated devices against CV components using a tiered strategy:
        </Paragraph>
        <Table
          size="small"
          pagination={false}
          dataSource={[
            { match: 'MAC address', confidence: '100%', note: 'Strongest match — same physical interface' },
            { match: 'IP address', confidence: '95%', note: 'Strong match — same network location' },
            { match: 'Vendor + Model', confidence: '70%', note: 'Heuristic match across runs' },
            { match: 'Vendor only', confidence: '40%', note: 'Weak match — useful for fuzzy comparison' },
          ]}
          columns={[
            { title: 'Match Type', dataIndex: 'match', render: (t) => <Text style={{ color: '#fff' }}>{t}</Text> },
            { title: 'Confidence', dataIndex: 'confidence', render: (t) => <Tag color="blue">{t}</Tag> },
            { title: 'Notes', dataIndex: 'note', render: (t) => <Text style={{ color: TEXT_PARAGRAPH }}>{t}</Text> },
          ]}
          rowKey="match"
          style={{ background: 'transparent' }}
        />
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          <ApiOutlined style={{ marginRight: 8 }} />
          What You Can Do
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="cyan">Browse</Tag> Inspect CV centers, presets, components, flows, and tags
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="green">Compare</Tag> Run a scenario and diff simulated devices vs CV-observed components
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="orange">Enrich</Tag> Pull real fingerprints from CV into the device library
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="purple">Validate</Tag> Confirm that simulated traffic produces the expected CV classifications
          </Text>
        </Space>
      </Card>

      <Alert
        type="warning"
        showIcon
        message="Identical fingerprints get merged"
        description="CV merges devices with identical sys_object_id + model into a single component. To get N distinct devices in CV, each simulated device's fingerprint must be unique. Running scenarios need a restart to pick up fingerprint changes."
        style={CARD_STYLE}
      />
    </Space>
  );
};

export const cyberVisionArticle: HelpArticle = {
  id: 'cyber-vision',
  title: 'Cisco Cyber Vision Integration',
  category: 'security-testing',
  keywords: [
    'cyber vision', 'cv', 'cisco', 'integration', 'compare', 'match',
    'component', 'flow', 'enrichment', 'preset', 'fingerprint'
  ],
  summary: 'Connect to a Cisco Cyber Vision center, match simulated devices to CV components, and validate fingerprints.',
  content: CyberVisionContent,
  relatedArticles: ['device-library', 'deployments', 'admin-settings'],
  relatedPages: ['/cyber-vision'],
  order: 1,
};
