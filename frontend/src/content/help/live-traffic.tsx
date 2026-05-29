/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Live Traffic Dashboard Help Article
 */

import React from 'react';
import { Typography, Space, Card, Alert, Tag } from 'antd';
import { BarChartOutlined, CloudServerOutlined, WarningOutlined, BellOutlined } from '@ant-design/icons';
import { TEXT_PARAGRAPH, ACCENT_BLUE, CARD_STYLE } from '../../constants/theme';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const LiveTrafficContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <BarChartOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Live Traffic Dashboard
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          Real-time view of every scenario currently running on a connected agent: packet rates,
          per-protocol traffic mix, deployment phase, attack progression, and agent health.
        </Paragraph>
      </div>

      <Alert
        type="info"
        showIcon
        message="Agent-only feature"
        description="The Live Traffic dashboard requires LIVE_TRAFFIC_ENABLED. PCAP-only PacketArch builds hide this page since they don't run live agents."
        style={CARD_STYLE}
      />

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          <CloudServerOutlined style={{ marginRight: 8 }} />
          What You'll See
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="cyan">Deployment cards</Tag> One per active scenario, showing the agent, scenario, current phase, and uptime
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="blue">Phase timeline</Tag> Visual progression through startup → steady → maintenance → shutdown phases
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="green">Packet rates</Tag> Aggregate and per-protocol packets/sec, broken down by flow
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="purple">Attack overlay</Tag> Kill-chain timeline if an attack playbook is running
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="orange">Adaptive state</Tag> Time-of-day rate multiplier, micro-variation drift, last directive applied
          </Text>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          <WarningOutlined style={{ marginRight: 8 }} />
          Troubleshooting
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Text strong style={{ color: '#fff' }}>No deployments shown:</Text> Confirm at least one agent is online (Settings → Traffic Agents) and a scenario has been deployed.
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Text strong style={{ color: '#fff' }}>Stale data / "last update" frozen:</Text> The dashboard polls the backend every 5 seconds. A frozen card usually means the agent's WebSocket dropped — check agent logs.
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Text strong style={{ color: '#fff' }}>Packets/sec is zero:</Text> Phase may be in shutdown, or the scenario has very low natural traffic. Check the orchestrator log on the agent for skipped flows.
          </Text>
        </Space>
      </Card>

      <Alert
        type="success"
        showIcon
        icon={<BellOutlined />}
        message="Health bell badge"
        description="The bell icon in the header shows the count of agents currently in warning/critical state. Clicking it brings you here."
        style={CARD_STYLE}
      />
    </Space>
  );
};

export const liveTrafficArticle: HelpArticle = {
  id: 'live-traffic',
  title: 'Live Traffic Dashboard',
  category: 'traffic-generation',
  keywords: [
    'live', 'traffic', 'dashboard', 'real-time', 'monitor', 'deployment',
    'phase', 'rate', 'packets', 'agent', 'health', 'attack', 'kill chain'
  ],
  summary: 'Real-time monitoring of running scenarios — packet rates, phase progress, attacks, and agent health.',
  content: LiveTrafficContent,
  relatedArticles: ['deployments', 'admin-settings'],
  relatedPages: ['/live-traffic'],
  order: 1,
};
