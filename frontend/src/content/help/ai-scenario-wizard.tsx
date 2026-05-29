/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * AI Scenario Wizard Help Article
 */

import React from 'react';
import { Typography, Space, Card, Steps, Alert, Tag } from 'antd';
import {
  RobotOutlined,
  EditOutlined,
  AppstoreOutlined,
  TeamOutlined,
  ApiOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { TEXT_PARAGRAPH, ACCENT_BLUE, CARD_STYLE } from '../../constants/theme';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const AIScenarioWizardContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <RobotOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          AI Scenario Wizard
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          Describe the OT environment you want to simulate in plain English and let
          Claude generate a fully-wired scenario — devices, zones, protocols, and
          flows — that you can immediately edit or deploy.
        </Paragraph>
      </div>

      <Alert
        type="info"
        showIcon
        message="Requires AI to be enabled"
        description="The wizard calls the Claude API via the backend AI service. If your install has AI_ENABLED=false this route redirects to /scenarios."
        style={CARD_STYLE}
      />

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          The 6 Steps
        </Title>
        <Steps
          direction="vertical"
          current={-1}
          items={[
            {
              title: <Text style={{ color: '#fff' }}>Name & Vertical</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Pick a scenario name and the industry vertical (manufacturing, water, energy, oil & gas, transportation, building automation). The vertical seeds the AI prompt with realistic device archetypes.</Text>,
              icon: <EditOutlined />,
            },
            {
              title: <Text style={{ color: '#fff' }}>Description</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Write 1–3 sentences describing what the site does — e.g., "City water treatment plant with two filtration trains and a UV disinfection stage." More specific descriptions yield more realistic scenarios.</Text>,
              icon: <EditOutlined />,
            },
            {
              title: <Text style={{ color: '#fff' }}>Devices</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Choose target device count (10–200). The AI will distribute these across Purdue levels appropriate for your vertical.</Text>,
              icon: <AppstoreOutlined />,
            },
            {
              title: <Text style={{ color: '#fff' }}>Vendors</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Constrain which vendors the AI may pick from. Leave empty to let the AI choose vendor mix; pick specific vendors to simulate, e.g., a Siemens-heavy or Rockwell-heavy plant.</Text>,
              icon: <TeamOutlined />,
            },
            {
              title: <Text style={{ color: '#fff' }}>Protocols</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Restrict the protocol set (Modbus, S7, EtherNet/IP, PROFINET, BACnet, SNMP). Vendor-protocol affinity rules still apply — the AI will not pair a Siemens PLC with EtherNet/IP.</Text>,
              icon: <ApiOutlined />,
            },
            {
              title: <Text style={{ color: '#fff' }}>Preview & Create</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Review the generated device list, zone layout, and flow graph. Save creates the scenario and opens it in Scenario Studio for further edits.</Text>,
              icon: <EyeOutlined />,
            },
          ]}
        />
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          What the AI Enforces Automatically
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="blue">Naming</Tag> Industrial-realistic device names tied to role and zone
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="cyan">Protocols</Tag> Only vendor-supported protocols per device
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="green">Completeness</Tag> Every device participates in at least one flow
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="orange">Conduits</Tag> Cross-zone flows follow IEC 62443 conduit rules
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="purple">MAC OUIs</Tag> Vendor-matched IEEE OUI prefixes
          </Text>
        </Space>
      </Card>

      <Alert
        type="success"
        showIcon
        message="Tip: AI is a starting point"
        description="The wizard produces a fully realistic scenario in one shot, but you can still open it in Scenario Studio and add zones, swap devices, or refine flows. Use AI to skip the blank-canvas problem."
        style={CARD_STYLE}
      />
    </Space>
  );
};

export const aiScenarioWizardArticle: HelpArticle = {
  id: 'ai-scenario-wizard',
  title: 'AI Scenario Wizard',
  category: 'scenarios',
  keywords: [
    'ai', 'wizard', 'generate', 'claude', 'natural language', 'auto', 'create',
    'scenario', 'description', 'vendors', 'protocols', 'preview'
  ],
  summary: 'Generate a complete OT scenario from a plain-English description using AI.',
  content: AIScenarioWizardContent,
  relatedArticles: ['scenarios', 'guided-builder', 'scenario-studio', 'templates'],
  relatedPages: ['/scenarios/ai-create'],
  order: 3,
};
