/**
 * Device Library Help Article
 */

import React from 'react';
import { Typography, Space, Card, Table, Tag, Divider } from 'antd';
import {
  DatabaseOutlined,
  SearchOutlined,
  FilterOutlined,
  CopyOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const DeviceLibraryContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <DatabaseOutlined style={{ marginRight: 8, color: '#049FD9' }} />
          Device Library
        </Title>
        <Paragraph style={{ color: '#8aa4bc', fontSize: 15 }}>
          The Device Library contains pre-configured device profiles representing real-world
          industrial equipment. Browse, search, and clone devices to use in your scenarios.
        </Paragraph>
      </div>

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Device Types
        </Title>
        <Table
          size="small"
          pagination={false}
          dataSource={[
            { type: 'PLC', desc: 'Programmable Logic Controller - main automation controller', protocols: 'Modbus, EtherNet/IP, PROFINET' },
            { type: 'RTU', desc: 'Remote Terminal Unit - remote monitoring/control', protocols: 'Modbus, DNP3' },
            { type: 'HMI', desc: 'Human-Machine Interface - operator displays', protocols: 'Modbus, EtherNet/IP' },
            { type: 'Drive', desc: 'Variable Frequency Drive - motor control', protocols: 'Modbus, PROFINET' },
            { type: 'IO Module', desc: 'Input/Output module - field I/O expansion', protocols: 'PROFINET, EtherNet/IP' },
            { type: 'Gateway', desc: 'Protocol converter/bridge', protocols: 'Multiple' },
            { type: 'Sensor', desc: 'Field instrumentation', protocols: 'Modbus' },
          ]}
          columns={[
            {
              title: 'Type',
              dataIndex: 'type',
              render: (text) => <Text strong style={{ color: '#049FD9' }}>{text}</Text>,
              width: 100,
            },
            {
              title: 'Description',
              dataIndex: 'desc',
              render: (text) => <Text style={{ color: '#8aa4bc' }}>{text}</Text>,
            },
            {
              title: 'Protocols',
              dataIndex: 'protocols',
              render: (text) => <Text style={{ color: '#6b6b8a' }}>{text}</Text>,
              width: 180,
            },
          ]}
          style={{ background: 'transparent' }}
          rowKey="type"
        />
      </Card>

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <SearchOutlined style={{ marginRight: 8 }} />
          Finding Devices
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Tag color="blue">Search</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Type to search by device name, type, or vendor
            </Text>
          </div>
          <div>
            <Tag color="green">Filter by Type</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Select specific device types (PLC, RTU, HMI, etc.)
            </Text>
          </div>
          <div>
            <Tag color="orange">Filter by Protocol</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Show devices supporting specific protocols
            </Text>
          </div>
          <div>
            <Tag color="purple">Filter by Vertical</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Show devices for specific industries
            </Text>
          </div>
        </Space>
      </Card>

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <SettingOutlined style={{ marginRight: 8 }} />
          Device Properties
        </Title>
        <Paragraph style={{ color: '#8aa4bc' }}>
          Click on a device to view its details:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ color: '#fff' }}>Basic Info</Text>
            <Text style={{ color: '#6b6b8a' }}> - Name, type, vendor, model</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Protocols</Text>
            <Text style={{ color: '#6b6b8a' }}> - Supported communication protocols</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Vendor Fingerprint</Text>
            <Text style={{ color: '#6b6b8a' }}> - Protocol-specific identity data</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Timing Model</Text>
            <Text style={{ color: '#6b6b8a' }}> - Polling intervals, jitter, response times</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Industry Verticals</Text>
            <Text style={{ color: '#6b6b8a' }}> - Where this device is typically used</Text>
          </div>
        </Space>
      </Card>

      <Divider style={{ borderColor: '#2a3f54' }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          <CopyOutlined style={{ marginRight: 8 }} />
          Cloning Devices
        </Title>
        <Paragraph style={{ color: '#8aa4bc' }}>
          To create a custom variation of an existing device:
        </Paragraph>
        <ol style={{ color: '#8aa4bc', paddingLeft: 20 }}>
          <li>Find the device you want to clone</li>
          <li>Click the "Clone" button</li>
          <li>Modify the properties as needed</li>
          <li>Save with a new name</li>
        </ol>
        <Paragraph style={{ color: '#8aa4bc', marginTop: 12 }}>
          Cloned devices appear in your custom devices list and can be used in any scenario.
        </Paragraph>
      </div>

      <Divider style={{ borderColor: '#2a3f54' }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Vendor Fingerprints
        </Title>
        <Paragraph style={{ color: '#8aa4bc' }}>
          Each device includes vendor-specific fingerprints that make generated traffic
          appear authentic. Fingerprints include:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Tag color="blue">Modbus</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Device ID, supported function codes
            </Text>
          </div>
          <div>
            <Tag color="green">EtherNet/IP</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Vendor ID, product code, serial number, CIP identity
            </Text>
          </div>
          <div>
            <Tag color="orange">PROFINET</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Station name, vendor ID, device ID
            </Text>
          </div>
          <div>
            <Tag color="purple">TCP Stack</Tag>
            <Text style={{ color: '#8aa4bc', marginLeft: 8 }}>
              Window size, TTL, TCP options (for OS fingerprinting)
            </Text>
          </div>
        </Space>
      </div>
    </Space>
  );
};

export const deviceLibraryArticle: HelpArticle = {
  id: 'device-library',
  title: 'Device Library',
  category: 'device-management',
  keywords: [
    'device', 'library', 'profile', 'plc', 'rtu', 'hmi', 'drive', 'io',
    'browse', 'search', 'filter', 'clone', 'vendor', 'fingerprint'
  ],
  summary: 'Browse and manage device profiles representing real-world industrial equipment.',
  content: DeviceLibraryContent,
  relatedArticles: ['scenario-studio', 'templates'],
  relatedPages: ['/devices'],
  order: 1,
};
