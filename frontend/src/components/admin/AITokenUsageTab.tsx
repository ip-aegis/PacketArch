/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * AI Token Usage admin tab — focuses purely on volume (input/output/cache
 * tokens, call counts) regardless of pricing. Pairs with the AI Costs tab
 * which handles the dollar side; both read from the same
 * /api/v1/admin/ai-usage endpoints.
 *
 * The split exists because CIRCUIT calls are priced at $0 by policy
 * (see ai_cost_tracking memory) — token counts are the only meaningful
 * usage signal for those, and we plan to gate quotas on tokens, not cost.
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
import { ReloadOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import {
  aiUsageApi,
  GroupedTotals,
  UsageEvent,
  UsageRange,
  UsageSummaryResponse,
} from '../../api/aiUsage';

const { Text, Title } = Typography;

const RANGE_OPTIONS: { label: string; value: UsageRange }[] = [
  { label: 'Last 24h', value: '24h' },
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
  { label: 'All time', value: 'all' },
];

const fmtInt = (n: number | null | undefined): string =>
  n == null ? '—' : n.toLocaleString();

const tokenGroupedColumns = (label: string): ColumnsType<GroupedTotals> => [
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
    title: 'Input tok',
    dataIndex: 'input_tokens',
    key: 'input_tokens',
    align: 'right',
    render: fmtInt,
    sorter: (a, b) => a.input_tokens - b.input_tokens,
  },
  {
    title: 'Output tok',
    dataIndex: 'output_tokens',
    key: 'output_tokens',
    align: 'right',
    render: fmtInt,
    defaultSortOrder: 'descend',
    sorter: (a, b) => a.output_tokens - b.output_tokens,
  },
];

const AITokenUsageTab: React.FC = () => {
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
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          'Failed to load AI usage summary',
      );
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
    } catch (err: any) {
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
      title: 'In',
      dataIndex: 'input_tokens',
      key: 'input_tokens',
      align: 'right',
      width: 90,
      render: fmtInt,
    },
    {
      title: 'Out',
      dataIndex: 'output_tokens',
      key: 'output_tokens',
      align: 'right',
      width: 90,
      render: fmtInt,
    },
    {
      title: 'Cache R',
      dataIndex: 'cache_read_tokens',
      key: 'cache_read_tokens',
      align: 'right',
      width: 90,
      render: (v: number) => (v ? fmtInt(v) : <Text type="secondary">0</Text>),
    },
    {
      title: 'Cache W',
      dataIndex: 'cache_write_tokens',
      key: 'cache_write_tokens',
      align: 'right',
      width: 90,
      render: (v: number) => (v ? fmtInt(v) : <Text type="secondary">0</Text>),
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
          AI Token Usage
        </Title>
        <Text type="secondary">
          Token volume across every AI provider call — independent of dollar
          cost. Useful for CIRCUIT (priced at $0 by policy) and for planning
          per-user / per-feature quotas. Dollar figures live on the
          adjacent <Text strong>AI Costs</Text> tab.
        </Text>
      </div>

      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Segmented
          options={RANGE_OPTIONS as any}
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
                <Statistic title="Calls" value={summary.overall.call_count} />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card size="small">
                <Statistic
                  title="Input tokens"
                  value={summary.overall.input_tokens}
                />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card size="small">
                <Statistic
                  title="Output tokens"
                  value={summary.overall.output_tokens}
                />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card size="small">
                <Statistic
                  title="Cache reads"
                  value={summary.overall.cache_read_tokens}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <Card title="By feature" size="small">
                {summary.by_feature.length === 0 ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />
                ) : (
                  <Table
                    size="small"
                    rowKey="key"
                    columns={tokenGroupedColumns('Feature')}
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
                    columns={tokenGroupedColumns('Model')}
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
                    columns={tokenGroupedColumns('Provider')}
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
                    columns={tokenGroupedColumns('User')}
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
              scroll={{ x: 1200 }}
            />
          </Card>
        </>
      )}
    </Space>
  );
};

export default AITokenUsageTab;
