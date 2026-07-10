/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Agents Hub Help Article
 */

import React from 'react';
import { Typography, Space, Card, Tag, Divider, Alert } from 'antd';
import {
  ApiOutlined,
  PartitionOutlined,
  CloudServerOutlined,
  ClusterOutlined,
} from '@ant-design/icons';
import type { HelpArticle } from './index';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, CARD_STYLE, CODE_BLOCK_STYLE } from '../../constants/theme';

const { Title, Paragraph, Text } = Typography;

const AgentsHubContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <ApiOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Agents Hub
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          The Agents page manages the infrastructure that injects live traffic: remote
          traffic agents, on-box Local Labs with a Cyber Vision sensor, and Cisco
          Modeling Labs (CML) integrations. Agents "phone home" to PacketArch over a
          WebSocket — no inbound ports are needed on the agent host.
        </Paragraph>
      </div>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Tabs
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Tag color="blue" icon={<ApiOutlined />} style={{ marginBottom: 4 }}>
              Agents
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              The agent fleet: online/offline status, version, CPU/memory heartbeats,
              and per-agent details. Install new agents, build an updated agent image,
              and push updates to one agent or the whole fleet.
            </Paragraph>
          </div>
          <div>
            <Tag color="green" icon={<PartitionOutlined />} style={{ marginBottom: 4 }}>
              Topology
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Live visualization of how traffic flows from each agent through its
              injection interface (or virtual SPAN) to the monitoring sensor.
            </Paragraph>
          </div>
          <div>
            <Tag color="cyan" icon={<CloudServerOutlined />} style={{ marginBottom: 4 }}>
              Local Labs
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              App-managed labs that run a traffic agent and a Cisco Cyber Vision docker
              sensor on the PacketArch host itself, wired through an isolated virtual
              SPAN — no external lab needed.
            </Paragraph>
          </div>
          <div>
            <Tag color="purple" icon={<ClusterOutlined />} style={{ marginBottom: 4 }}>
              Modeling Labs
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Connect to a Cisco Modeling Labs server and auto-deploy traffic agents
              into CML lab topologies.
            </Paragraph>
          </div>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Installing an Agent
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          The install drawer shows a one-line installer for any Linux host with Docker.
          Two paths:
        </Paragraph>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 4 }}>
          <Text strong style={{ color: '#fff' }}>Auto-register</Text> — the agent
          registers itself by name on first connect:
        </Paragraph>
        <pre style={CODE_BLOCK_STYLE}>
          {'curl -fsSLk https://<server>/agent/install.sh | sudo bash -s -- \\\n  --server https://<server> --name "My-Agent" --register'}
        </pre>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 4 }}>
          <Text strong style={{ color: '#fff' }}>Pre-issued token</Text> — create the
          agent in the UI first, then install with its token and injection interface:
        </Paragraph>
        <pre style={CODE_BLOCK_STYLE}>
          {'curl -fsSLk https://<server>/agent/install.sh | sudo bash -s -- \\\n  --server https://<server> --token "YOUR_TOKEN" --interface eth0'}
        </pre>
        <Alert
          type="info"
          showIcon
          message="Central updates"
          description="Use 'Build Image' to build and stage a new agent image on the server, then push it to online agents — they download, reload, and restart themselves."
          style={CARD_STYLE}
        />
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <CloudServerOutlined style={{ marginRight: 8 }} />
          Local Labs
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          A Local Lab gives you a complete agent → SPAN → Cyber Vision sensor chain on
          the PacketArch box, with the SPAN fully isolated so simulated traffic cannot
          leak onto your real network.
        </Paragraph>
        <ol style={{ color: TEXT_PARAGRAPH, paddingLeft: 20, marginBottom: 8 }}>
          <li>In Cyber Vision, create a new <Text strong style={{ color: '#fff' }}>docker</Text> sensor and copy the docker-compose it generates</li>
          <li>Click <Text code>New Local Lab</Text>, name it, and paste the compose</li>
          <li>Click <Text code>Build</Text> — the lab provisions in the background (pending → provisioning → running)</li>
          <li>Copy the agent token when it is shown — it is displayed only once</li>
          <li>Watch the Topology tab for the live agent → virtual SPAN → sensor flow</li>
        </ol>
        <Alert
          type="warning"
          showIcon
          message="Single-use provisioning tokens"
          description="Cyber Vision sensor provisioning tokens are single-use. Create a fresh sensor (and token) for each lab. Deleting a lab is a full teardown: containers, virtual SPAN, and the lab + agent records are all removed."
          style={CARD_STYLE}
        />
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <ClusterOutlined style={{ marginRight: 8 }} />
          Modeling Labs (CML)
        </Title>
        <ol style={{ color: TEXT_PARAGRAPH, paddingLeft: 20, marginBottom: 0 }}>
          <li>Enter the CML URL and credentials, then <Text code>Test Connection</Text></li>
          <li>Pick a lab from the list of labs on the CML server</li>
          <li>Deploy an agent into it — either dropped into the lab unattached, or wired to a specific node and port for data attachment</li>
          <li>The agent boots via cloud-init, connects back to PacketArch, and appears in the fleet like any other agent</li>
          <li>Decommission removes the agent VM from the CML lab when you are done</li>
        </ol>
      </Card>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <Paragraph style={{ color: TEXT_PARAGRAPH }}>
        Agents managed by a Local Lab or CML are badged as such, and their injection
        interface is locked at deploy time — PacketArch knows which interface feeds the
        sensor. Manual agents let you pick the interface per deployment. This page is
        unavailable on PCAP-only builds (live traffic disabled).
      </Paragraph>
    </Space>
  );
};

export const agentsHubArticle: HelpArticle = {
  id: 'agents-hub',
  title: 'Agents Hub',
  category: 'traffic-generation',
  keywords: [
    'agent', 'agents', 'install', 'fleet', 'topology', 'local lab', 'sensor',
    'cyber vision sensor', 'span', 'cml', 'modeling labs', 'token', 'register',
    'update', 'build image', 'websocket', 'interface'
  ],
  summary: 'Manage traffic agents, on-box Local Labs with a CV sensor, and Cisco Modeling Labs deployments.',
  content: AgentsHubContent,
  relatedArticles: ['deployments', 'live-traffic', 'cyber-vision', 'local-sensor-labs-scaling'],
  relatedPages: ['/agents'],
  order: 3,
};
