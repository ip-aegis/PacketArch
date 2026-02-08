/**
 * Step 3 — Read-only review of devices the template will create.
 */

import React from 'react';
import { Table, Tag, Spin, Typography, Alert } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useGuidedBuilderStore } from '../../stores/guidedBuilderStore';
import type { TemplateDevicePreview } from '../../stores/guidedBuilderStore';
import { DEVICE_TYPE_COLORS_EXTENDED, getProtocolColor, getProtocolLabel } from '../../constants/protocols';

const { Title, Text } = Typography;

const columns: ColumnsType<TemplateDevicePreview> = [
  {
    title: 'Name',
    dataIndex: 'name',
    key: 'name',
    render: (name: string) => <span style={{ color: '#e0e8f0' }}>{name}</span>,
  },
  {
    title: 'Type',
    dataIndex: 'type',
    key: 'type',
    width: 100,
    render: (type: string) => (
      <Tag color={DEVICE_TYPE_COLORS_EXTENDED[type] ?? '#8c8c8c'}>
        {type.toUpperCase()}
      </Tag>
    ),
  },
  {
    title: 'Vendor',
    dataIndex: 'vendor',
    key: 'vendor',
    render: (v: string | undefined) => (
      <span style={{ color: v ? '#c9d1d9' : '#555' }}>{v ?? '—'}</span>
    ),
  },
  {
    title: 'Model',
    dataIndex: 'fingerprintModel',
    key: 'fingerprintModel',
    render: (m: string | undefined) => (
      <span style={{ color: m ? '#c9d1d9' : '#555', fontSize: 12 }}>{m ?? '—'}</span>
    ),
  },
  {
    title: 'Zone',
    dataIndex: 'zone',
    key: 'zone',
    width: 120,
    render: (z: string | undefined) => (
      <span style={{ color: z ? '#c9d1d9' : '#555' }}>{z ?? '—'}</span>
    ),
  },
  {
    title: 'Protocols',
    dataIndex: 'protocols',
    key: 'protocols',
    render: (protocols: string[]) => (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {protocols.map((p) => (
          <Tag key={p} color={getProtocolColor(p)} style={{ fontSize: 11 }}>
            {getProtocolLabel(p)}
          </Tag>
        ))}
      </div>
    ),
  },
];

const DeviceReviewStep: React.FC = () => {
  const { expandedDevices, templateDetailLoading, templateDetailError } =
    useGuidedBuilderStore();

  if (templateDetailLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
        <div style={{ marginTop: 12, color: '#8aa4bc' }}>Loading template details...</div>
      </div>
    );
  }

  if (templateDetailError) {
    return (
      <Alert
        type="error"
        message="Failed to load template"
        description={templateDetailError}
        showIcon
      />
    );
  }

  // Group by zone for display
  const zones = [...new Set(expandedDevices.map((d) => d.zone ?? 'Unassigned'))].sort();

  return (
    <div>
      <Title level={5} style={{ color: '#e0e8f0', marginBottom: 8 }}>
        Review Devices
      </Title>
      <Text style={{ color: '#8aa4bc', display: 'block', marginBottom: 16 }}>
        This template will create {expandedDevices.length} device{expandedDevices.length !== 1 ? 's' : ''} across {zones.length} zone{zones.length !== 1 ? 's' : ''}. You can customize them in the next step.
      </Text>

      <Table
        dataSource={expandedDevices}
        columns={columns}
        rowKey="uid"
        pagination={false}
        size="small"
        scroll={{ y: 450 }}
        style={{ backgroundColor: '#141428' }}
      />
    </div>
  );
};

export default DeviceReviewStep;
