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
} from '@ant-design/icons';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const TemplatesContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <AppstoreAddOutlined style={{ marginRight: 8, color: '#049FD9' }} />
          Industry Templates
        </Title>
        <Paragraph style={{ color: '#8aa4bc', fontSize: 15 }}>
          Pre-built scenario templates provide realistic starting points for different
          industrial environments. Each template includes devices, protocols, and traffic
          patterns specific to the industry vertical.
        </Paragraph>
      </div>

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Industry Verticals
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Tag color="blue" icon={<ToolOutlined />} style={{ marginBottom: 4 }}>
              Manufacturing
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              High-speed automation with PLCs, HMIs, and variable frequency drives.
              Protocols: PROFINET, EtherNet/IP, Modbus TCP. Typical devices include
              Siemens S7-1500, Rockwell CompactLogix, and Allen-Bradley drives.
            </Paragraph>
          </div>

          <div>
            <Tag color="cyan" icon={<ExperimentOutlined />} style={{ marginBottom: 4 }}>
              Water/Wastewater
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              SCADA systems with RTUs for remote pump stations and treatment facilities.
              Protocols: Modbus TCP, DNP3. Includes master/outstation configurations
              with realistic polling patterns.
            </Paragraph>
          </div>

          <div>
            <Tag color="orange" icon={<ThunderboltOutlined />} style={{ marginBottom: 4 }}>
              Energy/Power
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Substation automation and power distribution. Protocols: IEC 104, Modbus TCP.
              Includes protective relays, meters, and substation RTUs with event-driven traffic.
            </Paragraph>
          </div>

          <div>
            <Tag color="purple" icon={<FireOutlined />} style={{ marginBottom: 4 }}>
              Oil & Gas
            </Tag>
            <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
              Pipeline SCADA and refinery automation. Protocols: Modbus TCP, OPC UA.
              Sparse polling patterns typical of geographically distributed systems.
            </Paragraph>
          </div>
        </Space>
      </Card>

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Template Contents
        </Title>
        <Paragraph style={{ color: '#8aa4bc' }}>
          Each template includes:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ color: '#fff' }}>Pre-configured Devices</Text>
            <Text style={{ color: '#6b6b8a' }}> - PLCs, RTUs, HMIs, drives with realistic fingerprints</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Communication Flows</Text>
            <Text style={{ color: '#6b6b8a' }}> - Master-slave relationships with proper protocols</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Network Zones</Text>
            <Text style={{ color: '#6b6b8a' }}> - Logical groupings (Control, Field, DMZ)</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Traffic Phases</Text>
            <Text style={{ color: '#6b6b8a' }}> - Time-based traffic variations</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Vendor Fingerprints</Text>
            <Text style={{ color: '#6b6b8a' }}> - Real device identities (Siemens, Rockwell, etc.)</Text>
          </div>
        </Space>
      </Card>

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Creating from Template
        </Title>
        <ol style={{ color: '#8aa4bc', paddingLeft: 20 }}>
          <li>Go to <Text code>Scenarios</Text> page</li>
          <li>Click <Text code>Create from Template</Text></li>
          <li>Select an industry vertical</li>
          <li>Browse available templates and select one</li>
          <li>Enter a name for your scenario</li>
          <li>Optionally enable:
            <ul style={{ marginTop: 4 }}>
              <li><Text strong style={{ color: '#fff' }}>Apply Learned Patterns</Text> - Use timing from PCAP learning</li>
              <li><Text strong style={{ color: '#fff' }}>Include Vulnerable Devices</Text> - Apply CVE variants</li>
            </ul>
          </li>
          <li>Click <Text code>Create Scenario</Text></li>
        </ol>
      </Card>

      <Divider style={{ borderColor: '#2a3f54' }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Example Templates
        </Title>
        <Table
          size="small"
          pagination={false}
          dataSource={[
            { vertical: 'Manufacturing', template: 'Assembly Line', devices: '8-12', protocols: 'PROFINET, EtherNet/IP' },
            { vertical: 'Manufacturing', template: 'Packaging Cell', devices: '6-8', protocols: 'EtherNet/IP, Modbus' },
            { vertical: 'Water', template: 'Water Treatment', devices: '10-15', protocols: 'Modbus TCP' },
            { vertical: 'Water', template: 'Pump Station', devices: '4-6', protocols: 'Modbus TCP, DNP3' },
            { vertical: 'Energy', template: 'Substation', devices: '8-10', protocols: 'IEC 104, Modbus' },
            { vertical: 'Oil & Gas', template: 'Pipeline SCADA', devices: '6-8', protocols: 'Modbus TCP, OPC UA' },
          ]}
          columns={[
            {
              title: 'Vertical',
              dataIndex: 'vertical',
              render: (text) => <Tag color={
                text === 'Manufacturing' ? 'blue' :
                text === 'Water' ? 'cyan' :
                text === 'Energy' ? 'orange' : 'purple'
              }>{text}</Tag>,
              width: 120,
            },
            {
              title: 'Template',
              dataIndex: 'template',
              render: (text) => <Text strong style={{ color: '#fff' }}>{text}</Text>,
            },
            {
              title: 'Devices',
              dataIndex: 'devices',
              render: (text) => <Text style={{ color: '#8aa4bc' }}>{text}</Text>,
              width: 80,
            },
            {
              title: 'Protocols',
              dataIndex: 'protocols',
              render: (text) => <Text style={{ color: '#6b6b8a' }}>{text}</Text>,
            },
          ]}
          style={{ background: 'transparent' }}
          rowKey="template"
        />
      </div>

      <Divider style={{ borderColor: '#2a3f54' }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Traffic Phases
        </Title>
        <Paragraph style={{ color: '#8aa4bc' }}>
          Templates can include time-based phases that vary traffic intensity:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Tag color="green">Startup</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Initial device discovery and registration
            </Text>
          </div>
          <div>
            <Tag color="blue">Normal Operation</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Standard polling and monitoring
            </Text>
          </div>
          <div>
            <Tag color="orange">Peak Load</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Increased traffic during production
            </Text>
          </div>
          <div>
            <Tag color="purple">Maintenance</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Configuration changes and diagnostics
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
    'oil', 'gas', 'preset', 'pre-built', 'quick start'
  ],
  summary: 'Use pre-built templates for Manufacturing, Water, Energy, and Oil & Gas scenarios.',
  content: TemplatesContent,
  relatedArticles: ['scenarios', 'scenario-studio', 'pcap-learning'],
  relatedPages: ['/scenarios'],
  order: 3,
};
