/**
 * Learning Page - Global PCAP learning and pattern management
 */

import React, { useState } from 'react';
import { Typography, Row, Col, Card, Tabs, Space, Statistic, Button, Spin } from 'antd';
import {
  UploadOutlined,
  LineChartOutlined,
  FileSearchOutlined,
  DatabaseOutlined,
  ReloadOutlined,
  CodeOutlined,
  SafetyCertificateOutlined,
  OrderedListOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import PcapUploadPanel from '../components/learning/PcapUploadPanel';
import LearnedPatternsPanel from '../components/learning/LearnedPatternsPanel';
import ProtocolPatternsPanel from '../components/learning/ProtocolPatternsPanel';
import DeviceFingerprintsPanel from '../components/learning/DeviceFingerprintsPanel';
import LearnedSequencesPanel from '../components/learning/LearnedSequencesPanel';
import { getLearningStats } from '../api/learning';

const { Title, Text, Paragraph } = Typography;

const LearningPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('upload');
  const [refreshKey, setRefreshKey] = useState(0);

  // Fetch learning stats
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQuery({
    queryKey: ['learning', 'stats'],
    queryFn: getLearningStats,
  });

  const handlePcapProcessed = (captureId: string) => {
    // Refresh patterns list and stats when a new PCAP is processed
    setRefreshKey((k) => k + 1);
    refetchStats();
    // Switch to patterns tab
    setActiveTab('patterns');
  };

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ color: '#fff', marginBottom: 8 }}>
          <FileSearchOutlined style={{ marginRight: 12 }} />
          PCAP Learning
        </Title>
        <Paragraph style={{ color: '#8aa4bc', fontSize: 14, maxWidth: 800 }}>
          Upload real network captures to learn authentic timing patterns, payload structures,
          and protocol behaviors. Apply learned patterns to scenarios for hyper-realistic traffic generation.
        </Paragraph>
      </div>

      {/* Stats Overview */}
      <Spin spinning={statsLoading}>
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={12} sm={8} md={4}>
            <Card
              size="small"
              style={{
                background: 'linear-gradient(135deg, #1a2734 0%, #1e2d3d 100%)',
                border: '1px solid #2a3f54',
              }}
            >
              <Statistic
                title={<Text style={{ color: '#6a8caf', fontSize: 11 }}>PCAPs</Text>}
                value={stats?.uploaded_pcaps ?? 0}
                prefix={<UploadOutlined />}
                valueStyle={{ color: '#5a9fd4', fontSize: 20 }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card
              size="small"
              style={{
                background: 'linear-gradient(135deg, #1a2734 0%, #1e2d3d 100%)',
                border: '1px solid #2a3f54',
              }}
            >
              <Statistic
                title={<Text style={{ color: '#6a8caf', fontSize: 11 }}>Timing Patterns</Text>}
                value={stats?.learned_patterns ?? 0}
                prefix={<LineChartOutlined />}
                valueStyle={{ color: '#52c41a', fontSize: 20 }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card
              size="small"
              style={{
                background: 'linear-gradient(135deg, #1a2734 0%, #1e2d3d 100%)',
                border: '1px solid #2a3f54',
              }}
            >
              <Statistic
                title={<Text style={{ color: '#6a8caf', fontSize: 11 }}>Protocol Patterns</Text>}
                value={stats?.protocol_patterns ?? 0}
                prefix={<CodeOutlined />}
                valueStyle={{ color: '#722ed1', fontSize: 20 }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card
              size="small"
              style={{
                background: 'linear-gradient(135deg, #1a2734 0%, #1e2d3d 100%)',
                border: '1px solid #2a3f54',
              }}
            >
              <Statistic
                title={<Text style={{ color: '#6a8caf', fontSize: 11 }}>Fingerprints</Text>}
                value={stats?.device_fingerprints ?? 0}
                prefix={<SafetyCertificateOutlined />}
                valueStyle={{ color: '#faad14', fontSize: 20 }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card
              size="small"
              style={{
                background: 'linear-gradient(135deg, #1a2734 0%, #1e2d3d 100%)',
                border: '1px solid #2a3f54',
              }}
            >
              <Statistic
                title={<Text style={{ color: '#6a8caf', fontSize: 11 }}>Sequences</Text>}
                value={stats?.learned_sequences ?? 0}
                prefix={<OrderedListOutlined />}
                valueStyle={{ color: '#13c2c2', fontSize: 20 }}
              />
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card
              size="small"
              style={{
                background: 'linear-gradient(135deg, #1a2734 0%, #1e2d3d 100%)',
                border: '1px solid #2a3f54',
              }}
            >
              <Statistic
                title={<Text style={{ color: '#6a8caf', fontSize: 11 }}>Protocols</Text>}
                value={stats?.protocols_covered ?? 0}
                prefix={<DatabaseOutlined />}
                valueStyle={{ color: '#eb2f96', fontSize: 20 }}
              />
            </Card>
          </Col>
        </Row>
      </Spin>

      {/* Main Content */}
      <Card
        style={{
          background: '#1e2d3d',
          border: '1px solid #2a3f54',
        }}
        styles={{ body: { padding: 0 } }}
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          tabBarStyle={{
            padding: '0 24px',
            background: '#1a2734',
            marginBottom: 0,
          }}
          tabBarExtraContent={
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={() => setRefreshKey((k) => k + 1)}
              style={{ color: '#8aa4bc' }}
            >
              Refresh
            </Button>
          }
          items={[
            {
              key: 'upload',
              label: (
                <span>
                  <UploadOutlined /> Upload PCAPs
                </span>
              ),
              children: (
                <div style={{ padding: 24 }}>
                  <Row gutter={24}>
                    <Col span={24}>
                      <PcapUploadPanel
                        onPcapProcessed={handlePcapProcessed}
                      />
                    </Col>
                  </Row>
                </div>
              ),
            },
            {
              key: 'patterns',
              label: (
                <span>
                  <LineChartOutlined /> Timing Patterns
                </span>
              ),
              children: (
                <div style={{ padding: 24 }} key={refreshKey}>
                  <LearnedPatternsPanel />
                </div>
              ),
            },
            {
              key: 'protocol-patterns',
              label: (
                <span>
                  <CodeOutlined /> Protocol Patterns
                </span>
              ),
              children: (
                <div style={{ padding: 24 }} key={refreshKey}>
                  <ProtocolPatternsPanel />
                </div>
              ),
            },
            {
              key: 'fingerprints',
              label: (
                <span>
                  <SafetyCertificateOutlined /> Device Fingerprints
                </span>
              ),
              children: (
                <div style={{ padding: 24 }} key={refreshKey}>
                  <DeviceFingerprintsPanel />
                </div>
              ),
            },
            {
              key: 'sequences',
              label: (
                <span>
                  <OrderedListOutlined /> Sequences
                </span>
              ),
              children: (
                <div style={{ padding: 24 }} key={refreshKey}>
                  <LearnedSequencesPanel />
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* Help Section */}
      <Card
        style={{
          background: '#1a2734',
          border: '1px solid #2a3f54',
          marginTop: 24,
        }}
      >
        <Title level={5} style={{ color: '#c9d1d9', marginBottom: 16 }}>
          How PCAP Learning Works
        </Title>
        <Row gutter={24}>
          <Col span={8}>
            <Space direction="vertical" size={8}>
              <Text strong style={{ color: '#5a9fd4' }}>
                1. Upload PCAP Files
              </Text>
              <Text style={{ color: '#6a8caf', fontSize: 12 }}>
                Upload .pcap, .pcapng, or .cap files containing real OT traffic.
                The system will automatically detect protocols and extract flows.
              </Text>
            </Space>
          </Col>
          <Col span={8}>
            <Space direction="vertical" size={8}>
              <Text strong style={{ color: '#5a9fd4' }}>
                2. Pattern Extraction
              </Text>
              <Text style={{ color: '#6a8caf', fontSize: 12 }}>
                The analyzer extracts timing distributions, payload patterns,
                and sequence behaviors. Statistical models are fitted to the data.
              </Text>
            </Space>
          </Col>
          <Col span={8}>
            <Space direction="vertical" size={8}>
              <Text strong style={{ color: '#5a9fd4' }}>
                3. Apply to Scenarios
              </Text>
              <Text style={{ color: '#6a8caf', fontSize: 12 }}>
                Use learned patterns in scenarios via the Realism tab.
                Patterns are applied per-device or per-flow for authentic traffic.
              </Text>
            </Space>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default LearningPage;
