/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Scenario Studio Help Article
 */

import React from 'react';
import { Typography, Space, Card, Tag, Divider, Table, Alert } from 'antd';
import {
  EditOutlined,
  RobotOutlined,
  ControlOutlined,
  CloudUploadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { HelpArticle } from './index';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, CARD_STYLE } from '../../constants/theme';

const { Title, Paragraph, Text } = Typography;

const SHORTCUTS = [
  { keys: 'Ctrl+K', action: 'Open command palette (navigation, canvas actions, @device search)' },
  { keys: 'Ctrl+S', action: 'Save an explicit version snapshot' },
  { keys: 'Ctrl+D', action: 'Duplicate selected device' },
  { keys: 'Ctrl+A', action: 'Select all devices' },
  { keys: 'G', action: 'Cycle canvas grouping mode' },
  { keys: 'Esc', action: 'Clear selection / close context menu' },
  { keys: '?', action: 'Show all keyboard shortcuts' },
];

const ScenarioStudioContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <EditOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Scenario Studio
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          The Studio is the visual editor for scenarios: build the device topology on
          the canvas, configure properties, chat with the AI assistant, deploy to
          agents, and layer attack playbooks — all from one screen.
        </Paragraph>
      </div>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Interface Layout
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Tag color="blue">Left Sidebar</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Device Palette - Drag devices from the template library onto the canvas
            </Text>
          </div>
          <div>
            <Tag color="green">Center</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Canvas - Devices, zones, flows, and conduits with a toolbar above
            </Text>
          </div>
          <div>
            <Tag color="orange">Right Panel</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Four tabs: AI Assistant, Properties, Deploy, and Attack
            </Text>
          </div>
          <div>
            <Tag color="purple">Bottom</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Timeline Editor - Drag/resize execution phases (startup, steady state, maintenance, shutdown, custom)
            </Text>
          </div>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Right Panel Tabs
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Tag color="purple" icon={<RobotOutlined />} style={{ marginBottom: 4 }}>
              AI Assistant
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Chat about the open scenario: ask it to add devices, fix flows, rename
              things, or explain design choices. Ctrl+Enter sends a message. Requires
              an AI provider configured in Settings.
            </Paragraph>
          </div>
          <div>
            <Tag color="blue" icon={<ControlOutlined />} style={{ marginBottom: 4 }}>
              Properties
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Context-aware editor for whatever is selected: device (name, type, vendor
              fingerprint, firmware, IP, MAC, protocols), flow (protocol, poll interval),
              zone, or conduit.
            </Paragraph>
          </div>
          <div>
            <Tag color="green" icon={<CloudUploadOutlined />} style={{ marginBottom: 4 }}>
              Deploy
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Pick a traffic agent, review the readiness checklist (devices present,
              flows complete, unique names and MACs), and launch a timed or perpetual
              deployment. A green dot on the tab means a deployment is running.
            </Paragraph>
          </div>
          <div>
            <Tag color="red" icon={<ThunderboltOutlined />} style={{ marginBottom: 4 }}>
              Attack
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Select and configure an ICS attack playbook, inject it into a running
              deployment, follow the kill chain live, and open the after-action report.
              See the Attack Simulation article for the full workflow.
            </Paragraph>
          </div>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Building the Topology
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ color: '#fff' }}>Add Devices</Text>
            <Text style={{ color: '#6b6b8a' }}> - Drag from the palette; each device gets a vendor fingerprint, IP, and vendor-correct MAC</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Create Flows</Text>
            <Text style={{ color: '#6b6b8a' }}> - Connect two devices to define protocol traffic between them</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Zones &amp; Conduits</Text>
            <Text style={{ color: '#6b6b8a' }}> - Group devices into IEC 62443 zones; draw conduits (or auto-generate them from Purdue adjacency) to justify cross-zone traffic</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Customize Names</Text>
            <Text style={{ color: '#6b6b8a' }}> - AI renaming with optional process context (e.g. "brewery bottling line")</Text>
          </div>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Canvas Toolbar
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ color: '#fff' }}>View &amp; Edit</Text>
            <Text style={{ color: '#6b6b8a' }}> - Zoom, fit view, undo/redo, delete selected, minimap toggle</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Layout &amp; Grouping</Text>
            <Text style={{ color: '#6b6b8a' }}> - Auto-layouts (Purdue Model, Data Flow, Grid, Circular) and cluster grouping (by zone, protocol, vendor, Purdue level, device type)</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Edges</Text>
            <Text style={{ color: '#6b6b8a' }}> - Show/hide flows and conduits; aggregate flows into one edge per zone pair</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Ambient Traffic</Text>
            <Text style={{ color: '#6b6b8a' }}> - Broadcast on/off (ARP, NTP, LLDP, CDP, DHCP, …) and Clean Demo Mode (suppresses PROFINET cyclic flood)</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Cell Isolation</Text>
            <Text style={{ color: '#6b6b8a' }}> - Enforce that cell traffic stays inside its zone except via defined conduits</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Review</Text>
            <Text style={{ color: '#6b6b8a' }}> - Rationality badge (architecture warnings) and AI Scenario Review drawer with remediation actions</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Versions</Text>
            <Text style={{ color: '#6b6b8a' }}> - Save Version (Ctrl+S) and Version History with diff and rollback</Text>
          </div>
        </Space>
      </Card>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Keyboard Shortcuts
        </Title>
        <Table
          size="small"
          pagination={false}
          dataSource={SHORTCUTS}
          columns={[
            {
              title: 'Keys',
              dataIndex: 'keys',
              render: (text: string) => <Text code>{text}</Text>,
              width: 110,
            },
            {
              title: 'Action',
              dataIndex: 'action',
              render: (text: string) => <Text style={{ color: TEXT_PARAGRAPH }}>{text}</Text>,
            },
          ]}
          style={{ background: 'transparent' }}
          rowKey="keys"
        />
      </div>

      <Alert
        type="info"
        showIcon
        message="Readiness before you run"
        description="The Deploy tab's readiness checklist validates the scenario (devices, complete flows, unique names and MAC addresses) before deployment or PCAP generation. Fix errors it reports — warnings are advisory."
        style={CARD_STYLE}
      />
    </Space>
  );
};

export const scenarioStudioArticle: HelpArticle = {
  id: 'scenario-studio',
  title: 'Scenario Studio',
  category: 'scenarios',
  keywords: [
    'studio', 'canvas', 'editor', 'device', 'flow', 'zone', 'conduit',
    'drag', 'drop', 'palette', 'properties', 'ai assistant', 'deploy',
    'attack', 'timeline', 'phases', 'shortcuts', 'command palette', 'layout'
  ],
  summary: 'The visual scenario editor: canvas, device palette, AI assistant, deploy, attack, timeline phases, and keyboard shortcuts.',
  content: ScenarioStudioContent,
  relatedArticles: ['scenarios', 'scenario-versions', 'attack-simulation', 'deployments'],
  relatedPages: ['/studio'],
  order: 2,
};
