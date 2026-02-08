/**
 * Scenario Studio Help Article
 */

import React from 'react';
import { Typography, Space, Card, Divider, Alert, Table, Tag } from 'antd';
import {
  AppstoreOutlined,
  DragOutlined,
  NodeIndexOutlined,
  SettingOutlined,
  SaveOutlined,
  PlayCircleOutlined,
  ZoomInOutlined,
} from '@ant-design/icons';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, BG_INSET, CARD_STYLE } from '../../constants/theme';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const ScenarioStudioContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <AppstoreOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Scenario Studio
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          The Scenario Studio is a visual canvas editor for designing OT network scenarios.
          Drag devices from the palette, connect them with communication flows, and configure
          protocol settings.
        </Paragraph>
      </div>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Interface Layout
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Tag color="blue">Left Sidebar</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Device Palette - Drag devices onto the canvas
            </Text>
          </div>
          <div>
            <Tag color="green">Center</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Canvas - Visual workspace for building scenarios
            </Text>
          </div>
          <div>
            <Tag color="orange">Right Sidebar</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Properties Panel - Configure selected device or flow
            </Text>
          </div>
          <div>
            <Tag color="purple">Bottom</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Timeline Editor - Define execution phases
            </Text>
          </div>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <DragOutlined style={{ marginRight: 8 }} />
          Adding Devices
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          To add a device to your scenario:
        </Paragraph>
        <ol style={{ color: TEXT_PARAGRAPH, paddingLeft: 20 }}>
          <li>Find the device type in the left palette (PLC, RTU, HMI, Drive, etc.)</li>
          <li>Drag the device icon onto the canvas</li>
          <li>Drop it in the desired location</li>
          <li>Click on the device to select it and configure properties</li>
        </ol>
        <Alert
          type="info"
          showIcon
          message="Tip"
          description="Devices are automatically assigned IP addresses from your scenario's allocated range."
          style={{ ...CARD_STYLE, background: BG_INSET, marginTop: 12 }}
        />
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <NodeIndexOutlined style={{ marginRight: 8 }} />
          Creating Flows
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Flows define communication between devices. To create a flow:
        </Paragraph>
        <ol style={{ color: TEXT_PARAGRAPH, paddingLeft: 20 }}>
          <li>Click on a device's output handle (right side)</li>
          <li>Drag to the target device's input handle (left side)</li>
          <li>Release to create the connection</li>
          <li>Click on the flow line to configure protocol settings</li>
        </ol>
        <Divider style={{ borderColor: BORDER_DEFAULT }} />
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Flow Properties
        </Title>
        <Table
          size="small"
          pagination={false}
          dataSource={[
            { prop: 'Protocol', desc: 'Modbus TCP, EtherNet/IP, or PROFINET' },
            { prop: 'Polling Interval', desc: 'How often the master polls the slave (ms)' },
            { prop: 'Function Codes', desc: 'Modbus functions to use (read/write registers, coils)' },
            { prop: 'Address Range', desc: 'Register or coil addresses to access' },
            { prop: 'Data Points', desc: 'Number of data points per poll cycle' },
          ]}
          columns={[
            {
              title: 'Property',
              dataIndex: 'prop',
              render: (text) => <Text strong style={{ color: '#fff' }}>{text}</Text>,
            },
            {
              title: 'Description',
              dataIndex: 'desc',
              render: (text) => <Text style={{ color: TEXT_PARAGRAPH }}>{text}</Text>,
            },
          ]}
          style={{ background: 'transparent' }}
          rowKey="prop"
        />
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <SettingOutlined style={{ marginRight: 8 }} />
          Device Configuration
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Select a device to view and edit its properties in the right panel:
        </Paragraph>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ color: '#fff' }}>Name & Type</Text>
            <Text style={{ color: '#6b6b8a' }}> - Device identification</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>IP Address</Text>
            <Text style={{ color: '#6b6b8a' }}> - Network address (auto-assigned or custom)</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>MAC Address</Text>
            <Text style={{ color: '#6b6b8a' }}> - Physical address (auto-generated from vendor OUI)</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Vendor Fingerprint</Text>
            <Text style={{ color: '#6b6b8a' }}> - Real device identity (Siemens, Rockwell, etc.)</Text>
          </div>
          <div>
            <Text strong style={{ color: '#fff' }}>Protocols</Text>
            <Text style={{ color: '#6b6b8a' }}> - Enabled communication protocols</Text>
          </div>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Canvas Controls
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Tag color="blue">Scroll/Drag</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Pan the canvas view
            </Text>
          </div>
          <div>
            <Tag color="blue">Scroll Wheel</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Zoom in/out
            </Text>
          </div>
          <div>
            <Tag color="blue">Click Device</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Select and view properties
            </Text>
          </div>
          <div>
            <Tag color="blue">Delete Key</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Remove selected device or flow
            </Text>
          </div>
          <div>
            <Tag color="blue">Minimap</Tag>
            <Text style={{ color: TEXT_PARAGRAPH, marginLeft: 8 }}>
              Navigate large scenarios (bottom-right corner)
            </Text>
          </div>
        </Space>
      </Card>

      <Alert
        type="success"
        showIcon
        icon={<SaveOutlined />}
        message="Auto-Save"
        description="Changes are automatically saved as you work. You'll see a brief indicator when saves occur."
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
    'studio', 'canvas', 'editor', 'visual', 'drag', 'drop', 'device', 'flow',
    'connection', 'configure', 'design', 'build', 'create', 'node', 'edge'
  ],
  summary: 'Visual canvas editor for designing OT network scenarios with drag-and-drop devices and flows.',
  content: ScenarioStudioContent,
  relatedArticles: ['scenarios', 'device-library', 'deployments'],
  relatedPages: ['/studio'],
  order: 2,
};
