/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * AI Costs admin tab — focuses on dollar spend. Pairs with the
 * AI Token Usage tab (which handles raw token volume); both pull from
 * /api/v1/admin/ai-usage.
 *
 * CIRCUIT is intentionally priced at $0 in
 * backend/app/ai_services/pricing.py — those rows still appear here but
 * with $0 cost; the token side of the story belongs on the AI Token
 * Usage tab.
 */

import React, { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Row,
  Segmented,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import { ReloadOutlined, WarningOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  aiUsageApi,
  GroupedTotals,
  UsageEvent,
  UsageRange,
  UsageSummaryResponse,
} from '../../api/aiUsage';
import { extractErrorMessage } from '../../utils/errorUtils';

const { Text, Title } = Typography;

const RANGE_OPTIONS: { label: string; value: UsageRange }[] = [
  { label: 'Last 24h', value: '24h' },
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
  { label: 'All time', value: 'all' },
];

const fmtUsd = (n: number | null | undefined): string => {
  if (n == null) return '—';
  if (n === 0) return '$0.00';
  if (n < 0.01) return `$${n.toFixed(6)}`;
  return `$${n.toFixed(2)}`;
};

const fmtInt = (n: number | null | undefined): string =>
  n == null ? '—' : n.toLocaleString();

const costGroupedColumns = (label: string): ColumnsType<GroupedTotals> => [
  {
    title: label,
    dataIndex: 'key',
    key: 'key',
    render: (v: string) => <Text code>{v || 'unknown'}</Text>,
  },
  {
    title: 'Calls',
    dataIndex: 'call_count',
    key: 'call_count',
    align: 'right',
    render: fmtInt,
    sorter: (a, b) => a.call_count - b.call_count,
  },
  {
    title: 'Cost (USD)',
    dataIndex: 'total_cost_usd',
    key: 'total_cost_usd',
    align: 'right',
    render: fmtUsd,
    defaultSortOrder: 'descend',
    sorter: (a, b) => a.total_cost_usd - b.total_cost_usd,
  },
];

const AICostsTab: React.FC = () => {
  const [range, setRange] = useState<UsageRange>('7d');
  const [summary, setSummary] = useState<UsageSummaryResponse | null>(null);
  const [events, setEvents] = useState<UsageEvent[]>([]);
  const [eventsTotal, setEventsTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const loadSummary = async (r: UsageRange) => {
    setLoading(true);
    setError(null);
    try {
      const data = await aiUsageApi.summary(r);
      setSummary(data);
    } catch (err) {
      setError(extractErrorMessage(err, 'Failed to load AI usage summary'));
    } finally {
      setLoading(false);
    }
  };

  const loadEvents = async (r: UsageRange, pageNum: number) => {
    setEventsLoading(true);
    try {
      const data = await aiUsageApi.events({
        range: r,
        limit: pageSize,
        offset: (pageNum - 1) * pageSize,
      });
      setEvents(data.items);
      setEventsTotal(data.total);
    } catch (err) {
      console.warn('Failed to load AI usage events', err);
    } finally {
      setEventsLoading(false);
    }
  };

  useEffect(() => {
    loadSummary(range);
    setPage(1);
    loadEvents(range, 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range]);

  const refresh = () => {
    loadSummary(range);
    loadEvents(range, page);
  };

  const eventColumns: ColumnsType<UsageEvent> = [
    {
      title: 'When',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: 'User',
      dataIndex: 'user_email',
      key: 'user_email',
      render: (v: string | null) => v || <Text type="secondary">—</Text>,
    },
    {
      title: 'Feature',
      dataIndex: 'feature',
      key: 'feature',
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: 'Provider',
      dataIndex: 'provider',
      key: 'provider',
      width: 100,
    },
    {
      title: 'Model',
      dataIndex: 'model',
      key: 'model',
      ellipsis: true,
    },
    {
      title: 'Cost',
      dataIndex: 'total_cost_usd',
      key: 'total_cost_usd',
      align: 'right',
      width: 120,
      render: (v: number | null) =>
        v == null ? (
          <Tooltip title="No price configured for this model — add it to backend/app/ai_services/pricing.py">
            <Tag icon={<WarningOutlined />} color="warning">
              unpriced
            </Tag>
          </Tooltip>
        ) : (
          fmtUsd(v)
        ),
    },
    {
      title: 'Latency',
      dataIndex: 'latency_ms',
      key: 'latency_ms',
      align: 'right',
      width: 100,
      render: (v: number | null) => (v == null ? '—' : `${(v / 1000).toFixed(2)}s`),
    },
    {
      title: 'Status',
      dataIndex: 'error',
      key: 'error',
      width: 100,
      render: (v: string | null) =>
        v ? (
          <Tooltip title={v}>
            <Tag color="error">error</Tag>
          </Tooltip>
        ) : (
          <Tag color="success">ok</Tag>
        ),
    },
  ];

  if (loading && !summary) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ marginBottom: 4 }}>
          AI Costs
        </Title>
        <Text type="secondary">
          Dollar spend per AI provider call. Costs derive from public
          per-1M token rates in <Text code>backend/app/ai_services/pricing.py</Text>.
          CIRCUIT is intentionally priced at $0 (contract-opaque per appkey);
          for CIRCUIT volume see the <Text strong>AI Token Usage</Text> tab.
          "Unpriced" rows indicate a model without a pricing entry — add one
          to track its spend.
        </Text>
      </div>

      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Segmented
          options={RANGE_OPTIONS}
          value={range}
          onChange={(v) => setRange(v as UsageRange)}
        />
        <Button icon={<ReloadOutlined />} onClick={refresh} loading={loading}>
          Refresh
        </Button>
      </Space>

      {error && (
        <Alert
          message="Failed to load AI usage"
          description={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
        />
      )}

      {summary && (
        <>
          <Row gutter={[16, 16]}>
            <Col xs={12} md={6}>
              <Card size="small">
                <Statistic
                  title="Total cost"
                  value={summary.overall.total_cost_usd}
                  precision={summary.overall.total_cost_usd < 1 ? 4 : 2}
                  prefix="$"
                />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card size="small">
                <Statistic title="Calls" value={summary.overall.call_count} />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card size="small">
                <Statistic
                  title="Unpriced calls"
                  value={summary.overall.unpriced_call_count}
                  valueStyle={
                    summary.overall.unpriced_call_count > 0
                      ? { color: '#faad14' }
                      : undefined
                  }
                />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card size="small">
                <Statistic
                  title="Failed calls"
                  value={summary.overall.error_count}
                  valueStyle={
                    summary.overall.error_count > 0
                      ? { color: '#ff4d4f' }
                      : undefined
                  }
                />
              </Card>
            </Col>
          </Row>

          {(summary.overall.unpriced_call_count > 0 ||
            summary.overall.error_count > 0) && (
            <Alert
              type="warning"
              showIcon
              message={
                <Space size="large">
                  {summary.overall.unpriced_call_count > 0 && (
                    <span>
                      {summary.overall.unpriced_call_count} unpriced call(s)
                      — add the model to pricing.py to track spend.
                    </span>
                  )}
                  {summary.overall.error_count > 0 && (
                    <span>
                      {summary.overall.error_count} failed call(s) in this
                      window.
                    </span>
                  )}
                </Space>
              }
            />
          )}

          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Card title="By feature" size="small">
                {summary.by_feature.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />
                ) : (
                  <Table
                    size="small"
                    rowKey="key"
                    columns={costGroupedColumns('Feature')}
                    dataSource={summary.by_feature}
                    pagination={false}
                  />
                )}
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card title="By model" size="small">
                {summary.by_model.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />
                ) : (
                  <Table
                    size="small"
                    rowKey="key"
                    columns={costGroupedColumns('Model')}
                    dataSource={summary.by_model}
                    pagination={false}
                  />
                )}
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card title="By provider" size="small">
                {summary.by_provider.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />
                ) : (
                  <Table
                    size="small"
                    rowKey="key"
                    columns={costGroupedColumns('Provider')}
                    dataSource={summary.by_provider}
                    pagination={false}
                  />
                )}
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card title="By user" size="small">
                {summary.by_user.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />
                ) : (
                  <Table
                    size="small"
                    rowKey="key"
                    columns={costGroupedColumns('User')}
                    dataSource={summary.by_user}
                    pagination={false}
                  />
                )}
              </Card>
            </Col>
          </Row>

          <Card title="Recent calls" size="small">
            <Table
              size="small"
              rowKey="id"
              loading={eventsLoading}
              columns={eventColumns}
              dataSource={events}
              pagination={{
                current: page,
                pageSize,
                total: eventsTotal,
                showSizeChanger: false,
                onChange: (p) => {
                  setPage(p);
                  loadEvents(range, p);
                },
              }}
              scroll={{ x: 1100 }}
            />
          </Card>
        </>
      )}
    </Space>
  );
};

export default AICostsTab;
