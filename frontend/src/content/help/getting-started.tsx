/**
 * Getting Started Help Article
 */

import React from 'react';
import { Typography, Space, Card, Alert, Divider } from 'antd';
import {
  RocketOutlined,
  FolderOutlined,
  AppstoreOutlined,
  CloudServerOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const GettingStartedContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <RocketOutlined style={{ marginRight: 8, color: '#049FD9' }} />
          Welcome to PacketArch
        </Title>
        <Paragraph style={{ color: '#8aa4bc', fontSize: 15 }}>
          PacketArch is an OT (Operational Technology) traffic simulation platform designed for
          security testing, training, and validation. Generate realistic industrial protocol
          traffic for Modbus TCP, EtherNet/IP, and PROFINET.
        </Paragraph>
      </div>

      <Alert
        type="info"
        showIcon
        message="Quick Start"
        description="The fastest way to get started is to create a scenario from a template. Templates include pre-configured devices and traffic patterns for common industrial environments."
        style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}
      />

      <Card style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Typical Workflow
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <div style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: '#049FD9',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Text style={{ color: '#fff', fontWeight: 600 }}>1</Text>
            </div>
            <div>
              <Text strong style={{ color: '#fff' }}>Create a Scenario</Text>
              <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
                Go to <Text code>Scenarios</Text> and click "Create from Template" or "Create Blank Scenario".
                Templates provide pre-built configurations for Manufacturing, Water/Wastewater, Energy, and Oil & Gas.
              </Paragraph>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <div style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: '#049FD9',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Text style={{ color: '#fff', fontWeight: 600 }}>2</Text>
            </div>
            <div>
              <Text strong style={{ color: '#fff' }}>Configure in Scenario Studio</Text>
              <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
                Use the visual canvas editor to add devices, configure protocols, and define
                communication flows between controllers and field devices.
              </Paragraph>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <div style={{
              width: 28,
              height: 28,
              borderRadius: '50%',
              background: '#049FD9',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Text style={{ color: '#fff', fontWeight: 600 }}>3</Text>
            </div>
            <div>
              <Text strong style={{ color: '#fff' }}>Deploy Traffic</Text>
              <Paragraph style={{ color: '#8aa4bc', marginBottom: 0 }}>
                Generate PCAP files or deploy live traffic to a network interface.
                Monitor progress in the Deployments page and download completed captures.
              </Paragraph>
            </div>
          </div>
        </Space>
      </Card>

      <Divider style={{ borderColor: '#2a3f54' }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Key Features
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircleOutlined style={{ color: '#6CC04A' }} />
            <Text style={{ color: '#8aa4bc' }}>Visual scenario builder with drag-and-drop canvas</Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircleOutlined style={{ color: '#6CC04A' }} />
            <Text style={{ color: '#8aa4bc' }}>Industry-specific templates (Manufacturing, Water, Energy, Oil & Gas)</Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircleOutlined style={{ color: '#6CC04A' }} />
            <Text style={{ color: '#8aa4bc' }}>PCAP learning to create realistic traffic from real captures</Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircleOutlined style={{ color: '#6CC04A' }} />
            <Text style={{ color: '#8aa4bc' }}>Vendor fingerprints for realistic device emulation</Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircleOutlined style={{ color: '#6CC04A' }} />
            <Text style={{ color: '#8aa4bc' }}>Anomaly injection for security testing</Text>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircleOutlined style={{ color: '#6CC04A' }} />
            <Text style={{ color: '#8aa4bc' }}>CVE database for vulnerability simulation</Text>
          </div>
        </Space>
      </div>

      <Divider style={{ borderColor: '#2a3f54' }} />

      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Supported Protocols
        </Title>
        <Space wrap>
          <Card size="small" style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
            <Text strong style={{ color: '#049FD9' }}>Modbus TCP</Text>
            <br />
            <Text style={{ color: '#6b6b8a', fontSize: 12 }}>Port 502</Text>
          </Card>
          <Card size="small" style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
            <Text strong style={{ color: '#049FD9' }}>EtherNet/IP</Text>
            <br />
            <Text style={{ color: '#6b6b8a', fontSize: 12 }}>Port 44818</Text>
          </Card>
          <Card size="small" style={{ background: '#1e2d3d', border: '1px solid #2a3f54' }}>
            <Text strong style={{ color: '#049FD9' }}>PROFINET</Text>
            <br />
            <Text style={{ color: '#6b6b8a', fontSize: 12 }}>Layer 2</Text>
          </Card>
        </Space>
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
