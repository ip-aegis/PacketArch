/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Industry Templates Help Article
 */

import React from 'react';
import { Typography, Space, Card, Tag, Divider, Table } from 'antd';
import {
  AppstoreAddOutlined,
  ToolOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  FireOutlined,
  CarOutlined,
  HomeOutlined,
  InboxOutlined,
} from '@ant-design/icons';
import type { HelpArticle } from './index';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, CARD_STYLE } from '../../constants/theme';

const { Title, Paragraph, Text } = Typography;

const VERTICAL_COLORS: Record<string, string> = {
  'Manufacturing': 'blue',
  'Water/Wastewater': 'cyan',
  'Energy/Power': 'orange',
  'Oil & Gas': 'purple',
  'Transportation': 'magenta',
  'Building Automation': 'geekblue',
  'Distribution & Logistics': 'gold',
};

const EXAMPLE_TEMPLATES = [
  { vertical: 'Manufacturing', template: 'Siemens Discrete Manufacturing', protocols: 'PROFINET, S7comm' },
  { vertical: 'Manufacturing', template: 'Rockwell Automotive Assembly', protocols: 'EtherNet/IP' },
  { vertical: 'Water/Wastewater', template: 'Municipal Water Treatment Plant', protocols: 'Modbus TCP, SNMP' },
  { vertical: 'Water/Wastewater', template: 'Regional Pump Station Network', protocols: 'Modbus TCP, DNP3' },
  { vertical: 'Energy/Power', template: 'Electrical Substation IED Network', protocols: 'IEC 61850, IEC 104' },
  { vertical: 'Energy/Power', template: 'WAMS / PDC Phasor Network', protocols: 'C37.118' },
  { vertical: 'Oil & Gas', template: 'Pipeline SCADA Compressor Station Network', protocols: 'Modbus TCP' },
  { vertical: 'Oil & Gas', template: 'Yokogawa CENTUM VP Refinery Process Unit', protocols: 'Modbus TCP, OPC UA' },
  { vertical: 'Transportation', template: 'Urban Intersection Network', protocols: 'SNMP/NTCIP' },
  { vertical: 'Building Automation', template: 'Commercial Office Building BMS', protocols: 'BACnet/IP' },
  { vertical: 'Distribution & Logistics', template: 'Fulfillment Center', protocols: 'EtherNet/IP, Modbus TCP' },
];

const TemplatesContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <AppstoreAddOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Industry Templates
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          Pre-built scenario templates provide realistic starting points for different
          industrial environments. Each template includes devices, protocols, zones, and
          traffic patterns specific to the industry vertical.
        </Paragraph>
      </div>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Industry Verticals
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Tag color="blue" icon={<ToolOutlined />} style={{ marginBottom: 4 }}>
              Manufacturing
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              High-speed automation with PLCs, HMIs, and drives. Templates range from
              Siemens discrete manufacturing (PROFINET/S7comm) and Rockwell automotive
              assembly (EtherNet/IP) to a strict Purdue-segmented plant and a
              semiconductor fab wafer line.
            </Paragraph>
          </div>

          <div>
            <Tag color="cyan" icon={<ExperimentOutlined />} style={{ marginBottom: 4 }}>
              Water/Wastewater
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              SCADA systems with RTUs for treatment plants and remote pump stations.
              Protocols: Modbus TCP, DNP3, SNMP. Master/outstation configurations with
              realistic polling patterns.
            </Paragraph>
          </div>

          <div>
            <Tag color="orange" icon={<ThunderboltOutlined />} style={{ marginBottom: 4 }}>
              Energy/Power
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Substation automation, generation, and grid control. Protocols: IEC 61850,
              IEC 104, C37.118 synchrophasor, Modbus TCP. Templates include a substation
              IED network, gas turbine plant, grid control center, solar + battery
              storage, and a WAMS/PDC phasor network.
            </Paragraph>
          </div>

          <div>
            <Tag color="purple" icon={<FireOutlined />} style={{ marginBottom: 4 }}>
              Oil &amp; Gas
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              DCS-centric production and pipeline SCADA: Emerson DeltaV offshore platform,
              pipeline compressor stations, Yokogawa CENTUM VP refinery unit, and a
              Honeywell Experion LNG terminal. Protocols: Modbus TCP, OPC UA.
            </Paragraph>
          </div>

          <div>
            <Tag color="magenta" icon={<CarOutlined />} style={{ marginBottom: 4 }}>
              Transportation
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Intelligent transportation systems: highway corridor ITS, urban
              intersections, tunnel control, and toll plaza operations. Protocols:
              SNMP/NTCIP, Modbus TCP.
            </Paragraph>
          </div>

          <div>
            <Tag color="geekblue" icon={<HomeOutlined />} style={{ marginBottom: 4 }}>
              Building Automation
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              BACnet/IP building management: commercial office BMS, data center
              infrastructure, and a university campus BMS.
            </Paragraph>
          </div>

          <div>
            <Tag color="gold" icon={<InboxOutlined />} style={{ marginBottom: 4 }}>
              Distribution &amp; Logistics
            </Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Warehouse automation: fulfillment center, distribution center, cold chain
              warehouse, and parcel sorting hub. Conveyor and sortation control over
              EtherNet/IP and Modbus TCP.
            </Paragraph>
          </div>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Template Contents
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Each template includes:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ color: '#fff' }}>Pre-configured Devices</Text>
            <Text style={{ color: '#6b6b8a' }}> - PLCs, RTUs, HMIs, drives with realistic vendor fingerprints</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Communication Flows</Text>
            <Text style={{ color: '#6b6b8a' }}> - Master/slave relationships using protocols each vendor actually supports</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Network Zones</Text>
            <Text style={{ color: '#6b6b8a' }}> - IEC 62443 zone groupings aligned to Purdue levels</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Traffic Phases</Text>
            <Text style={{ color: '#6b6b8a' }}> - Time-based intensity variation across the run</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Realistic Naming &amp; Addressing</Text>
            <Text style={{ color: '#6b6b8a' }}> - Industrial device names, vendor-correct MAC OUIs, auto-assigned IP ranges</Text>
          </div>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Creating from Template
        </Title>
        <ol style={{ color: TEXT_PARAGRAPH, paddingLeft: 20 }}>
          <li>Go to <Text code>Scenarios</Text> page</li>
          <li>Click <Text code>From Template</Text></li>
          <li>Select an industry vertical</li>
          <li>Browse available templates and select one</li>
          <li>Enter a name for your scenario</li>
          <li>Optionally enable:
            <ul style={{ marginTop: 4 }}>
              <li><Text strong style={{ color: '#fff' }}>Include Vulnerable Devices</Text> - Apply CVE variants</li>
            </ul>
          </li>
          <li>Click <Text code>Create Scenario</Text></li>
        </ol>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
          Prefer a step-by-step walkthrough? The <Text strong style={{ color: '#fff' }}>Guided
          Builder</Text> wraps template selection with device and flow customization.
        </Paragraph>
      </Card>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Example Templates
        </Title>
        <Table
          size="small"
          pagination={false}
          dataSource={EXAMPLE_TEMPLATES}
          columns={[
            {
              title: 'Vertical',
              dataIndex: 'vertical',
              render: (text: string) => <Tag color={VERTICAL_COLORS[text] || 'default'}>{text}</Tag>,
              width: 170,
            },
            {
              title: 'Template',
              dataIndex: 'template',
              render: (text: string) => <Text strong style={{ color: '#fff' }}>{text}</Text>,
            },
            {
              title: 'Protocols',
              dataIndex: 'protocols',
              render: (text: string) => <Text style={{ color: '#6b6b8a' }}>{text}</Text>,
            },
          ]}
          style={{ background: 'transparent' }}
          rowKey="template"
        />
      </div>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Traffic Phases
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Templates include time-based phases that vary traffic intensity. You can edit
          them in the Studio timeline editor:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Tag color="green">Startup</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Device discovery, identification, and connection establishment
            </Text>
          </div>
          <div>
            <Tag color="blue">Steady State</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Standard polling and monitoring
            </Text>
          </div>
          <div>
            <Tag color="orange">Maintenance</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Configuration changes and diagnostics
            </Text>
          </div>
          <div>
            <Tag color="volcano">Shutdown</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Orderly session teardown
            </Text>
          </div>
          <div>
            <Tag color="purple">Custom</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Your own phases with custom rate multipliers
            </Text>
          </div>
        </Space>
      </div>
    </Space>
  );
};

export const templatesArticle: HelpArticle = {
  id: 'templates',
  title: 'Industry Templates',
  category: 'scenarios',
  keywords: [
    'template', 'vertical', 'industry', 'manufacturing', 'water', 'energy',
    'oil', 'gas', 'transportation', 'building automation', 'logistics',
    'warehouse', 'preset', 'pre-built', 'quick start'
  ],
  summary: 'Pre-built templates across 7 industry verticals: Manufacturing, Water, Energy, Oil & Gas, Transportation, Building Automation, and Distribution & Logistics.',
  content: TemplatesContent,
  relatedArticles: ['scenarios', 'guided-builder', 'scenario-studio'],
  relatedPages: [],
  order: 3,
};
