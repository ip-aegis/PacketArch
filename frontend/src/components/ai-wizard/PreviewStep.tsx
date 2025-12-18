/**
 * Step 6: Preview Generated Scenario
 */

import React, { useState } from 'react';
import { Typography, Spin, Table, Tag, Alert, Statistic, Row, Col, Card, Button, Collapse, Badge } from 'antd';
import {
  LoadingOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  DesktopOutlined,
  SwapOutlined,
  RobotOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { useAIScenarioWizardStore } from '../../stores/aiScenarioWizardStore';

const { Title, Text, Paragraph } = Typography;

const PreviewStep: React.FC = () => {
  const {
    isGenerating,
    preview,
    previewError,
    createError,
    generatePreview,
  } = useAIScenarioWizardStore();

  if (isGenerating) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin indicator={<LoadingOutlined style={{ fontSize: 48, color: '#5a9fd4' }} spin />} />
        <Title level={4} style={{ color: '#e0e8f0', marginTop: 24 }}>
          Generating Scenario Preview...
        </Title>
        <Paragraph style={{ color: '#8aa4bc' }}>
          AI is analyzing your description and creating devices and communication flows.
        </Paragraph>
      </div>
    );
  }

  if (previewError) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <Alert
          type="error"
          message="Generation Failed"
          description={previewError}
          showIcon
          style={{ marginBottom: 24 }}
        />
        <Button icon={<ReloadOutlined />} onClick={generatePreview}>
          Try Again
        </Button>
      </div>
    );
  }

  if (!preview) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Text style={{ color: '#8aa4bc' }}>No preview available</Text>
      </div>
    );
  }

  const deviceColumns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Type',
      dataIndex: 'device_type',
      key: 'device_type',
      render: (type: string) => (
        <Tag color="blue">{type.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Vendor',
      dataIndex: 'vendor',
      key: 'vendor',
      render: (vendor: string) => vendor || '-',
    },
    {
      title: 'Protocols',
      dataIndex: 'protocols',
      key: 'protocols',
      render: (protocols: string[]) => (
        <>
          {protocols.map(p => (
            <Tag key={p} color="green" style={{ marginBottom: 2 }}>
              {p}
            </Tag>
          ))}
        </>
      ),
    },
  ];

  const flowColumns = [
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Protocol',
      dataIndex: 'protocol',
      key: 'protocol',
      render: (protocol: string) => (
        <Tag color="cyan">{protocol}</Tag>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 24 }} />
        <Title level={4} style={{ color: '#e0e8f0', margin: 0 }}>
          Preview: {preview.name}
        </Title>
        {preview.ai_enhanced && (
          <Tag
            icon={<RobotOutlined />}
            color="purple"
            style={{ marginLeft: 8 }}
          >
            AI Enhanced
          </Tag>
        )}
      </div>

      {/* AI Design Rationale */}
      {preview.ai_enhanced && preview.design_rationale && (
        <Collapse
          ghost
          style={{ marginBottom: 16, backgroundColor: '#1a2735', borderRadius: 6 }}
          items={[
            {
              key: 'rationale',
              label: (
                <span style={{ color: '#8aa4bc' }}>
                  <InfoCircleOutlined style={{ marginRight: 8 }} />
                  AI Design Rationale
                </span>
              ),
              children: (
                <Paragraph style={{ color: '#c0d0e0', margin: 0 }}>
                  {preview.design_rationale}
                </Paragraph>
              ),
            },
          ]}
        />
      )}

      {/* AI Features Used */}
      {preview.ai_enhanced && preview.ai_features && preview.ai_features.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Text style={{ color: '#8aa4bc', marginRight: 8 }}>AI determined: </Text>
          {preview.ai_features.map(feature => (
            <Tag key={feature} color="geekblue" style={{ marginRight: 4 }}>
              {feature}
            </Tag>
          ))}
        </div>
      )}

      {createError && (
        <Alert
          type="error"
          message="Failed to create scenario"
          description={createError}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card style={{ backgroundColor: '#1e2d3d', borderColor: '#2a3f54' }}>
            <Statistic
              title={<span style={{ color: '#8aa4bc' }}>Devices</span>}
              value={preview.device_count}
              prefix={<DesktopOutlined style={{ color: '#5a9fd4' }} />}
              valueStyle={{ color: '#e0e8f0' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={{ backgroundColor: '#1e2d3d', borderColor: '#2a3f54' }}>
            <Statistic
              title={<span style={{ color: '#8aa4bc' }}>Flows</span>}
              value={preview.flow_count}
              prefix={<SwapOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#e0e8f0' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={{ backgroundColor: '#1e2d3d', borderColor: '#2a3f54' }}>
            <Statistic
              title={<span style={{ color: '#8aa4bc' }}>Protocols</span>}
              value={preview.protocols_used.length}
              valueStyle={{ color: '#e0e8f0' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={{ backgroundColor: '#1e2d3d', borderColor: '#2a3f54' }}>
            <Statistic
              title={<span style={{ color: '#8aa4bc' }}>Vendors</span>}
              value={preview.vendors_used.length}
              valueStyle={{ color: '#e0e8f0' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Protocols & Vendors Tags */}
      <div style={{ marginBottom: 24 }}>
        <Text style={{ color: '#8aa4bc' }}>Protocols: </Text>
        {preview.protocols_used.map(p => (
          <Tag key={p} color="cyan" style={{ marginRight: 4 }}>{p}</Tag>
        ))}
        <Text style={{ color: '#8aa4bc', marginLeft: 16 }}>Vendors: </Text>
        {preview.vendors_used.map(v => (
          <Tag key={v} color="purple" style={{ marginRight: 4 }}>{v}</Tag>
        ))}
      </div>

      {/* Devices Table */}
      <Title level={5} style={{ color: '#e0e8f0' }}>Devices</Title>
      <Table
        dataSource={preview.devices}
        columns={deviceColumns}
        rowKey="device_id"
        pagination={false}
        size="small"
        style={{ marginBottom: 24 }}
        scroll={{ y: 150 }}
      />

      {/* Flows Table */}
      <Title level={5} style={{ color: '#e0e8f0' }}>Communication Flows</Title>
      <Table
        dataSource={preview.flows}
        columns={flowColumns}
        rowKey="flow_id"
        pagination={false}
        size="small"
        scroll={{ y: 150 }}
      />

      <div style={{ marginTop: 16, textAlign: 'center' }}>
        <Button
          icon={<ReloadOutlined />}
          onClick={generatePreview}
          style={{ color: '#8aa4bc' }}
        >
          Regenerate Preview
        </Button>
      </div>
    </div>
  );
};

export default PreviewStep;
