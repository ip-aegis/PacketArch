/**
 * Step 5 — Read-only review of flows the template will generate.
 */

import React from 'react';
import { Table, Tag, Typography, Alert, Empty } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { InfoCircleOutlined } from '@ant-design/icons';
import { useGuidedBuilderStore } from '../../stores/guidedBuilderStore';
import { DEVICE_TYPE_COLORS_EXTENDED, getProtocolColor, getProtocolLabel } from '../../constants/protocols';

const { Title, Text } = Typography;

interface FlowRow {
  key: string;
  protocol: string;
  pattern: string;
  interval_ms: number;
  source_types: string[];
  target_types: string[];
  jitter_ms?: number;
}

function formatInterval(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(ms % 1000 === 0 ? 0 : 1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

const columns: ColumnsType<FlowRow> = [
  {
    title: 'Source Types',
    dataIndex: 'source_types',
    key: 'source_types',
    render: (types: string[]) => (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {types.length > 0
          ? types.map((t) => (
              <Tag key={t} color={DEVICE_TYPE_COLORS_EXTENDED[t] ?? '#8c8c8c'}>
                {t.toUpperCase()}
              </Tag>
            ))
          : <span style={{ color: '#555' }}>Any</span>}
      </div>
    ),
  },
  {
    title: 'Target Types',
    dataIndex: 'target_types',
    key: 'target_types',
    render: (types: string[]) => (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {types.length > 0
          ? types.map((t) => (
              <Tag key={t} color={DEVICE_TYPE_COLORS_EXTENDED[t] ?? '#8c8c8c'}>
                {t.toUpperCase()}
              </Tag>
            ))
          : <span style={{ color: '#555' }}>Any</span>}
      </div>
    ),
  },
  {
    title: 'Protocol',
    dataIndex: 'protocol',
    key: 'protocol',
    width: 130,
    render: (p: string) => (
      <Tag color={getProtocolColor(p)}>{getProtocolLabel(p)}</Tag>
    ),
  },
  {
    title: 'Interval',
    dataIndex: 'interval_ms',
    key: 'interval_ms',
    width: 100,
    render: (ms: number) => (
      <span style={{ color: '#c9d1d9' }}>{formatInterval(ms)}</span>
    ),
  },
  {
    title: 'Pattern',
    dataIndex: 'pattern',
    key: 'pattern',
    width: 110,
    render: (p: string) => (
      <span style={{ color: '#c9d1d9' }}>{p.replace(/_/g, ' ')}</span>
    ),
  },
];

const FlowReviewStep: React.FC = () => {
  const { templateDetail } = useGuidedBuilderStore();

  const flows = templateDetail?.flows ?? [];

  if (flows.length === 0) {
    return (
      <div>
        <Title level={5} style={{ color: '#e0e8f0', marginBottom: 16 }}>
          Review Flows
        </Title>
        <Alert
          type="info"
          icon={<InfoCircleOutlined />}
          message="Auto-Generated Flows"
          description="This template uses the Smart Flow Generator. Flows will be automatically created based on device types, zones, and protocols when the scenario is built."
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Empty
          description="Flow details will be visible after creation in the Scenario Studio"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </div>
    );
  }

  const dataSource: FlowRow[] = flows.map((f, i) => ({
    key: `flow_${i}`,
    protocol: f.protocol,
    pattern: f.pattern,
    interval_ms: f.interval_ms,
    source_types: f.source_types ?? [],
    target_types: f.target_types ?? [],
    jitter_ms: f.jitter_ms,
  }));

  return (
    <div>
      <Title level={5} style={{ color: '#e0e8f0', marginBottom: 8 }}>
        Review Flows
      </Title>
      <Text style={{ color: '#8aa4bc', display: 'block', marginBottom: 16 }}>
        {dataSource.length} flow rule{dataSource.length !== 1 ? 's' : ''} will generate traffic between devices.
        Actual flow instances are created during scenario build based on device matching.
      </Text>

      <Table
        dataSource={dataSource}
        columns={columns}
        rowKey="key"
        pagination={false}
        size="small"
        scroll={{ y: 400 }}
        style={{ backgroundColor: '#141428' }}
      />
    </div>
  );
};

export default FlowReviewStep;
