/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Guided Builder Help Article
 */

import React from 'react';
import { Typography, Space, Card, Steps, Alert } from 'antd';
import {
  CompassOutlined,
  AppstoreOutlined,
  FileSearchOutlined,
  UnorderedListOutlined,
  EditOutlined,
  PartitionOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, CARD_STYLE } from '../../constants/theme';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const GuidedBuilderContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <CompassOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Guided Scenario Builder
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          A six-step wizard that starts from a built-in template and walks you through
          customizing devices and flows before finalizing the scenario. Use this when
          you want template-driven realism without diving into the full Scenario Studio canvas.
        </Paragraph>
      </div>

      <Alert
        type="info"
        showIcon
        message="When to use this vs other paths"
        description="Use Guided Builder when a template close to your target environment exists. Use AI Wizard when you want a custom scenario from a description. Use Scenario Studio directly when you need full canvas control."
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
              title: <Text style={{ color: '#fff' }}>1. Vertical</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Pick your industry (manufacturing, water, energy, oil & gas, building automation, transportation). Determines which template catalog you see next.</Text>,
              icon: <AppstoreOutlined />,
            },
            {
              title: <Text style={{ color: '#fff' }}>2. Template</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Choose a pre-built scenario template from that vertical. Each lists device count, protocols used, and a description of the simulated facility.</Text>,
              icon: <FileSearchOutlined />,
            },
            {
              title: <Text style={{ color: '#fff' }}>3. Review Devices</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Scan the template's device list — name, type, vendor, model, zone, protocols. Confirm the cast matches what you want before customizing.</Text>,
              icon: <UnorderedListOutlined />,
            },
            {
              title: <Text style={{ color: '#fff' }}>4. Customize</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Rename devices, swap vendors/models, change zones, or drop devices you don't need. Edits are bounded by vendor-protocol compatibility rules.</Text>,
              icon: <EditOutlined />,
            },
            {
              title: <Text style={{ color: '#fff' }}>5. Review Flows</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Inspect generated communication flows. Cross-zone flows are checked against IEC 62443 conduit rules and flagged if non-compliant.</Text>,
              icon: <PartitionOutlined />,
            },
            {
              title: <Text style={{ color: '#fff' }}>6. Finalize</Text>,
              description: <Text style={{ color: TEXT_PARAGRAPH }}>Name the scenario, set duration, and create. The result opens in Scenario Studio for any final touch-ups.</Text>,
              icon: <CheckOutlined />,
            },
          ]}
        />
      </Card>

      <Alert
        type="success"
        showIcon
        message="Realism guardrails are always on"
        description="The builder enforces the 5 realism dimensions: unique industrial names, vendor-supported protocols, every device participates in a flow, conduit-compliant cross-zone traffic, and vendor-matched MAC OUIs."
        style={CARD_STYLE}
      />
    </Space>
  );
};

export const guidedBuilderArticle: HelpArticle = {
  id: 'guided-builder',
  title: 'Guided Scenario Builder',
  category: 'scenarios',
  keywords: [
    'guided', 'builder', 'wizard', 'template', 'step', 'customize', 'review',
    'vertical', 'scenario', 'devices', 'flows'
  ],
  summary: 'Template-driven 6-step wizard for building scenarios without using the canvas directly.',
  content: GuidedBuilderContent,
  relatedArticles: ['templates', 'ai-scenario-wizard', 'scenarios', 'scenario-studio'],
  relatedPages: ['/scenarios/guided-builder'],
  order: 4,
};
