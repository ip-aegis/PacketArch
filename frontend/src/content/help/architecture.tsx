/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Architecture Reference Help Article
 */

import React from 'react';
import { Typography, Space, Card, Tag, Divider } from 'antd';
import { ApartmentOutlined, NodeIndexOutlined, ClusterOutlined } from '@ant-design/icons';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, CARD_STYLE } from '../../constants/theme';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const ArchitectureContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <ApartmentOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Architecture Reference
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          The Architecture page is a reference for the OT/ICS network models PacketArch simulates:
          Purdue levels, IEC 62443 zones and conduits, and protocol affinity rules. Use it as a
          glossary while designing or auditing a scenario.
        </Paragraph>
      </div>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          <ClusterOutlined style={{ marginRight: 8 }} />
          Purdue Model (ISA-95) Levels
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="red">L4–L5</Tag> Enterprise & DMZ — ERP, business logistics, internet-facing services
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="orange">L3</Tag> Operations & control — MES, historians, engineering workstations
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="gold">L2</Tag> Supervisory — SCADA, HMI, operator stations
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="green">L1</Tag> Basic control — PLCs, RTUs, controllers
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="blue">L0</Tag> Process — sensors, actuators, drives, field I/O
          </Text>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          <NodeIndexOutlined style={{ marginRight: 8 }} />
          Zones & Conduits (IEC 62443)
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          A <Text strong style={{ color: '#fff' }}>zone</Text> is a logical group of devices sharing
          common security requirements (e.g. "Control LAN", "DMZ"). A <Text strong style={{ color: '#fff' }}>conduit</Text>
          is a sanctioned communication path between zones — every cross-zone flow in a scenario must
          map to a defined conduit, or it gets flagged at readiness check.
        </Paragraph>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Intra-zone traffic is unrestricted. This mirrors how real OT networks segment traffic and is
          enforced by the conduit compliance service in the backend.
        </Paragraph>
      </Card>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Protocol → Layer Affinity
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="blue">Modbus TCP, S7, EtherNet/IP, PROFINET</Tag> typically L1 ↔ L2
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="cyan">BACnet/IP</Tag> typically L1 ↔ L2 within building automation systems
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="green">SNMP / NTCIP</Tag> management traffic, typically L2 ↔ L3
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="orange">OPC UA</Tag> L2 ↔ L3 historians and MES
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="purple">DNP3 / IEC-104</Tag> SCADA → RTU (energy, water)
          </Text>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Vendor-Protocol Rules (Enforced)
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          PacketArch will not let a device speak a protocol its vendor doesn't actually support.
          Some examples that are enforced automatically:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text style={{ color: TEXT_PARAGRAPH }}>• Siemens → S7comm, PROFINET (never EtherNet/IP)</Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>• Rockwell / Allen-Bradley → EtherNet/IP (never PROFINET)</Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>• Schneider → Modbus TCP (primary)</Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>• Honeywell / Yokogawa → vendor-specific + Modbus / OPC</Text>
        </Space>
      </Card>
    </Space>
  );
};

export const architectureArticle: HelpArticle = {
  id: 'architecture',
  title: 'Architecture Reference',
  category: 'reference',
  keywords: [
    'architecture', 'purdue', 'isa-95', 'iec', '62443', 'zone', 'conduit',
    'level', 'segmentation', 'vendor', 'protocol', 'affinity', 'reference'
  ],
  summary: 'Purdue levels, IEC 62443 zones/conduits, and vendor-protocol affinity rules.',
  content: ArchitectureContent,
  relatedArticles: ['scenario-studio', 'device-library', 'glossary'],
  relatedPages: ['/architecture'],
  order: 2,
};
