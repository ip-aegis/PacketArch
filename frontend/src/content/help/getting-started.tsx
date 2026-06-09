/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Getting Started Help Article
 */

import React from 'react';
import { Typography, Space, Card, Alert, Divider } from 'antd';
import { RocketOutlined, CheckCircleOutlined } from '@ant-design/icons';
import type { HelpArticle } from './index';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, CARD_STYLE } from '../../constants/theme';

const { Title, Paragraph, Text } = Typography;

const PROTOCOLS: { name: string; detail: string }[] = [
  { name: 'Modbus TCP', detail: 'Port 502' },
  { name: 'EtherNet/IP', detail: 'Port 44818 / 2222' },
  { name: 'PROFINET', detail: 'Layer 2' },
  { name: 'S7comm', detail: 'Port 102' },
  { name: 'BACnet/IP', detail: 'Port 47808' },
  { name: 'SNMP', detail: 'Port 161 / 162' },
  { name: 'OPC UA', detail: 'Port 4840' },
  { name: 'DNP3', detail: 'Port 20000' },
  { name: 'IEC 60870-5-104', detail: 'Port 2404' },
];

const WorkflowStep: React.FC<{ n: number; title: string; children: React.ReactNode }> = ({ n, title, children }) => (
  <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
    <div style={{
      width: 28,
      height: 28,
      borderRadius: '50%',
      background: ACCENT_BLUE,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
    }}>
      <Text style={{ color: '#fff', fontWeight: 600 }}>{n}</Text>
    </div>
    <div>
      <Text strong style={{ color: '#fff' }}>{title}</Text>
      <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
        {children}
      </Paragraph>
    </div>
  </div>
);

const Feature: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
    <CheckCircleOutlined style={{ color: '#6CC04A' }} />
    <Text style={{ color: TEXT_PARAGRAPH }}>{children}</Text>
  </div>
);

const GettingStartedContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <RocketOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Welcome to PacketArch
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          PacketArch is an OT (Operational Technology) traffic simulation platform for
          security testing, training, and validation. It generates realistic industrial
          protocol traffic — Modbus TCP, EtherNet/IP, PROFINET, S7comm, BACnet/IP, SNMP,
          OPC UA, DNP3, IEC 104 and more — as PCAP files or as live traffic injected by
          remote agents, complete with vendor-accurate device fingerprints.
        </Paragraph>
      </div>

      <Alert
        type="info"
        showIcon
        message="Quick Start"
        description="The fastest way to get started is to create a scenario from an industry template, or describe what you want in plain language with AI Create. Templates include pre-configured devices and traffic patterns for common industrial environments."
        style={CARD_STYLE}
      />

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Typical Workflow
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <WorkflowStep n={1} title="Create a Scenario">
            Go to <Text code>Scenarios</Text> and create from a template, with the
            Guided Builder, with AI Create (natural language), or from a blank canvas.
            Templates cover seven verticals: Manufacturing, Water/Wastewater,
            Energy/Power, Oil &amp; Gas, Transportation, Building Automation, and
            Distribution &amp; Logistics.
          </WorkflowStep>
          <WorkflowStep n={2} title="Refine in Scenario Studio">
            Use the visual canvas to add devices, configure vendor fingerprints and
            protocols, and define communication flows. The readiness checklist and AI
            scenario review help you verify realism before running.
          </WorkflowStep>
          <WorkflowStep n={3} title="Generate Traffic">
            Generate a PCAP file, or deploy the scenario to a traffic agent for live,
            perpetual traffic on a real network interface. Monitor live runs on the
            Live Traffic dashboard.
          </WorkflowStep>
          <WorkflowStep n={4} title="Test Detection">
            Optionally layer an ICS attack playbook over the baseline traffic and
            verify what your monitoring stack catches. With the Cisco Cyber Vision
            integration you can compare what CV observed against the scenario design.
          </WorkflowStep>
        </Space>
      </Card>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Key Features
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Feature>Visual scenario builder with drag-and-drop canvas</Feature>
          <Feature>Industry templates across 7 verticals</Feature>
          <Feature>AI scenario generation, review, and assistant</Feature>
          <Feature>295+ vendor fingerprints for realistic device emulation</Feature>
          <Feature>Live traffic agents and PCAP generation from the same scenario</Feature>
          <Feature>ICS attack playbooks with MITRE ATT&amp;CK mapping and after-action reports</Feature>
          <Feature>Anomaly injection and CVE-vulnerable device variants</Feature>
          <Feature>Cisco Cyber Vision integration for ground-truth comparison</Feature>
        </Space>
      </div>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Supported Protocols
        </Title>
        <Space wrap>
          {PROTOCOLS.map((p) => (
            <Card key={p.name} size="small" style={CARD_STYLE}>
              <Text strong style={{ color: ACCENT_BLUE }}>{p.name}</Text>
              <br />
              <Text style={{ color: '#6b6b8a', fontSize: 12 }}>{p.detail}</Text>
            </Card>
          ))}
        </Space>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 12, marginBottom: 0 }}>
          Energy scenarios additionally emit IEC 61850 and C37.118 synchrophasor
          traffic, and every scenario can include ambient broadcast traffic (ARP, LLDP,
          CDP, NTP, DHCP, and more) for realism.
        </Paragraph>
      </div>
    </Space>
  );
};

export const gettingStartedArticle: HelpArticle = {
  id: 'getting-started',
  title: 'Getting Started',
  category: 'getting-started',
  keywords: [
    'start', 'begin', 'introduction', 'overview', 'quick start', 'tutorial',
    'workflow', 'first steps', 'new user', 'basics', 'help'
  ],
  summary: 'Learn the basics of PacketArch and how to create your first OT traffic scenario.',
  content: GettingStartedContent,
  relatedArticles: ['scenarios', 'scenario-studio', 'templates'],
  relatedPages: ['/'],
  order: 1,
};
