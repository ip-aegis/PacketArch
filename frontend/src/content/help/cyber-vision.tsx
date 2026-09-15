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
          Connecting Centers
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Add each Cyber Vision Center in <Text strong style={{ color: '#fff' }}>Settings → Cyber Vision</Text>:
          base URL (e.g. <Text code>https://cv-center.example.com</Text>), an API token, and
          optionally the separate New UI API token that enables the Organization Hierarchy
          sync. Use <Text strong style={{ color: '#fff' }}>Test connection</Text> to check TLS and
          auth before saving.
        </Paragraph>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          On <Text strong style={{ color: '#fff' }}>Cyber Vision 5.6 and later</Text>, also add a
          <Text strong style={{ color: '#fff' }}> UI username and password</Text>. 5.6 moved network
          creation into its own UI, and a network created through the API is left
          half-registered — it appears in the inventory and devices are attributed to it, but
          Cyber Vision never builds its asset group, and the communications map is drawn from
          asset groups. The zone is simply absent from the map while looking healthy
          everywhere else. Creating the network the way the UI does is the only route that
          registers it fully, and that needs a real login rather than a token. Without one,
          PacketArch still provisions the network the old way and warns that it will not reach
          the map. Networks created before the credentials were added keep the gap until they
          are repaired.
        </Paragraph>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
          One PacketArch server can talk to several centers. One of them is the
          <Text strong style={{ color: '#fff' }}> default</Text>, used whenever you don&apos;t pick one.
          With more than one center, a picker appears on this page, when you build a local lab,
          and when you deploy with <Text strong style={{ color: '#fff' }}>Provision to Cyber Vision</Text>.
          A local lab&apos;s sensor enrolls into one center for good, so deploys to that lab always
          provision there. A scenario lives on one center at a time: tear down its Cyber Vision
          objects before provisioning it on another.
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
    'component', 'flow', 'enrichment', 'preset', 'fingerprint',
    'center', 'multiple centers', 'default center'
  ],
  summary: 'Connect one or more Cisco Cyber Vision centers, match simulated devices to CV components, and validate fingerprints.',
  content: CyberVisionContent,
  relatedArticles: ['device-library', 'deployments', 'admin-settings'],
  relatedPages: ['/cyber-vision'],
  order: 1,
};
