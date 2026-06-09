/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Attack Simulation Help Article
 */

import React from 'react';
import { Typography, Space, Card, Tag, Divider, Table, Alert } from 'antd';
import { ThunderboltOutlined, FileSearchOutlined } from '@ant-design/icons';
import type { HelpArticle } from './index';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, CARD_STYLE } from '../../constants/theme';

const { Title, Paragraph, Text } = Typography;

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'red',
  high: 'orange',
  medium: 'gold',
  low: 'green',
};

const PLAYBOOKS = [
  { name: 'TRITON-like Safety System Attack', severity: 'critical', category: 'APT' },
  { name: 'PIPEDREAM-like Multi-Protocol Toolkit', severity: 'critical', category: 'APT' },
  { name: 'INDUSTROYER-like Grid Attack', severity: 'critical', category: 'APT' },
  { name: 'INDUSTROYER2-like Substation Attack', severity: 'critical', category: 'APT' },
  { name: 'HAVEX-like Recon & Data Theft', severity: 'high', category: 'APT' },
  { name: 'VOLT TYPHOON-like LotL Reconnaissance', severity: 'high', category: 'APT' },
  { name: 'Building Automation System Compromise', severity: 'high', category: 'APT' },
  { name: 'Traffic Infrastructure Disruption', severity: 'high', category: 'APT' },
  { name: 'Insider Threat - Unauthorized OT Access', severity: 'high', category: 'Insider' },
  { name: 'Network Reconnaissance', severity: 'medium', category: 'Recon' },
  { name: 'Snort/Suricata IDS Validation Suite', severity: 'low', category: 'IDS testing' },
];

const AttackSimulationContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <ThunderboltOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Attack Simulation
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          Attack playbooks layer realistic ICS attack traffic — modeled on real-world
          campaigns and mapped to MITRE ATT&amp;CK for ICS — over a scenario's baseline
          traffic. Use them to validate that your detection stack (Cyber Vision, IDS,
          SIEM) actually catches each stage of a kill chain.
        </Paragraph>
      </div>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Playbook Library
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Browse playbooks at <Text code>Libraries → Attacks</Text>. Each card shows
          severity, MITRE ID, category, target verticals, required protocols, stage
          count, and duration. Click through for the full detail page: a kill-chain
          flowchart, planned MITRE technique coverage, and per-stage cards listing each
          action with the Cyber Vision alerts it is expected to trigger.
        </Paragraph>
        <Table
          size="small"
          pagination={false}
          dataSource={PLAYBOOKS}
          columns={[
            {
              title: 'Playbook',
              dataIndex: 'name',
              render: (text: string) => <Text strong style={{ color: '#fff' }}>{text}</Text>,
            },
            {
              title: 'Severity',
              dataIndex: 'severity',
              width: 100,
              render: (text: string) => <Tag color={SEVERITY_COLORS[text]}>{text}</Tag>,
            },
            {
              title: 'Category',
              dataIndex: 'category',
              width: 110,
              render: (text: string) => <Text style={{ color: '#6b6b8a' }}>{text}</Text>,
            },
          ]}
          style={{ background: 'transparent' }}
          rowKey="name"
        />
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Running an Attack (Studio Attack Tab)
        </Title>
        <ol style={{ color: TEXT_PARAGRAPH, paddingLeft: 20, marginBottom: 8 }}>
          <li>
            <Text strong style={{ color: '#fff' }}>Select</Text> — open the Attack tab
            in the Studio right panel and pick a playbook from the embedded library
          </li>
          <li>
            <Text strong style={{ color: '#fff' }}>Configure</Text> — set intensity,
            start mode (manual or auto), and optional timing overrides
          </li>
          <li>
            <Text strong style={{ color: '#fff' }}>Arm</Text> — the configured playbook
            is included in the next deployment, or injected directly into an
            already-running deployment with <Text code>Inject Into Running Deployment</Text>
          </li>
          <li>
            <Text strong style={{ color: '#fff' }}>Monitor</Text> — once active, the
            kill-chain timeline tracks the current stage, actions completed, and packets
            generated; you can pause, advance stages, or stop
          </li>
        </ol>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
          A red dot on the Attack tab means an attack is live; orange means a playbook
          is configured and waiting. The kill-chain timeline also appears on the
          deployment card in Live Traffic.
        </Paragraph>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <FileSearchOutlined style={{ marginRight: 8 }} />
          After-Action Reports
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Every attack run produces an after-action report, available live during the
          run and persisted with the scenario afterwards:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ color: '#fff' }}>Run summary</Text>
            <Text style={{ color: '#6b6b8a' }}> - status, start/end time, total packets and actions fired</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Stage breakdown</Text>
            <Text style={{ color: '#6b6b8a' }}> - planned vs actual duration per stage, packets, per-action fire counts and IOCs (target IPs, DNS queries)</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>MITRE coverage</Text>
            <Text style={{ color: '#6b6b8a' }}> - techniques that actually executed highlight green</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>JSON export</Text>
            <Text style={{ color: '#6b6b8a' }}> - download the full report for evidence or tooling</Text>
          </div>
        </Space>
      </Card>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <Alert
        type="info"
        showIcon
        message="Attacks in PCAP files"
        description="You don't need live agents to use playbooks: the Generate PCAP dialog has an attack playbook dropdown and intensity setting, so attack traffic is woven into the capture alongside baseline traffic. This works on PCAP-only builds too."
        style={CARD_STYLE}
      />
    </Space>
  );
};

export const attackSimulationArticle: HelpArticle = {
  id: 'attack-simulation',
  title: 'Attack Simulation',
  category: 'security-testing',
  keywords: [
    'attack', 'playbook', 'kill chain', 'mitre', 'att&ck', 'triton',
    'pipedream', 'industroyer', 'havex', 'volt typhoon', 'insider',
    'recon', 'ids', 'snort', 'suricata', 'after-action', 'report',
    'inject', 'intensity', 'stages'
  ],
  summary: 'Run ICS attack playbooks over baseline traffic — live or in PCAPs — with kill-chain tracking, MITRE coverage, and after-action reports.',
  content: AttackSimulationContent,
  relatedArticles: ['anomalies', 'scenario-studio', 'cve-browser', 'deployments'],
  relatedPages: ['/libraries/attacks'],
  order: 2,
};
