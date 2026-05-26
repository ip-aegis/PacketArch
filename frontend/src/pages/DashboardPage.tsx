/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Dashboard page.
 *
 * Operator-facing snapshot of the workspace: KPI tiles scoped to the
 * current user, vertical-mix + top-protocols breakdowns, live
 * deployment cards enriched with vertical / pps / packets / protocol
 * mix, and a recently-updated scenarios list. Replaces the old static
 * "Getting Started" prose with a compact tips card.
 */

import React, { useEffect } from 'react';
import {
  Typography, Card, Row, Col, Statistic, Space, Button, Tag, List, Spin,
  Progress, Tooltip, Empty,
} from 'antd';
import {
  AppstoreOutlined, ThunderboltOutlined, FileTextOutlined, PlusOutlined,
  SyncOutlined, PlayCircleOutlined, RocketOutlined, BulbOutlined,
  CompassOutlined, ApiOutlined, ClockCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useDeploymentsStore } from '../stores/deploymentsStore';
import { getOverviewStats } from '../api/stats';
import { dashboardApi, type DashboardDeployment } from '../api/dashboard';
import { useFeatures } from '../hooks/useFeatures';
import type { UnifiedDeployment } from '../types/docker';
import { verticalConfig } from '../components/scenarios/scenarioConstants';
import ContextualHelpIcon from '../components/help/ContextualHelpIcon';
import { PROTOCOL_LABELS, PROTOCOL_COLORS_EXTENDED } from '../constants/protocols';

const { Title, Paragraph, Text } = Typography;

// ─── Helpers ────────────────────────────────────────────────────────

const formatElapsedTime = (startedAt: string | null): string => {
  if (!startedAt) return '0s';
  const elapsed = Date.now() - new Date(startedAt).getTime();
  const hours = Math.floor(elapsed / 3600000);
  const minutes = Math.floor((elapsed % 3600000) / 60000);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
};

const calculateProgress = (deployment: UnifiedDeployment): number => {
  if (!deployment.started_at || !deployment.duration_ms) return 0;
  const elapsed = Date.now() - new Date(deployment.started_at).getTime();
  return Math.min(100, Math.round((elapsed / deployment.duration_ms) * 100));
};

const formatNumber = (n: number | undefined): string => {
  if (!n || !isFinite(n)) return '0';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return n.toString();
};

const formatPps = (pps: number | undefined): string => {
  if (!pps || !isFinite(pps)) return '0';
  if (pps >= 1000) return `${(pps / 1000).toFixed(1)}K`;
  return pps.toFixed(0);
};

const formatRelativeTime = (iso: string | null): string => {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
};

const verticalMeta = (key: string) =>
  verticalConfig[key as keyof typeof verticalConfig] || {
    color: '#8aa4bc', label: key.replace(/_/g, ' '), icon: null,
  };

const protocolLabel = (p: string): string =>
  PROTOCOL_LABELS[p] || p.replace(/_/g, ' ').toUpperCase();

const protocolColor = (p: string): string =>
  PROTOCOL_COLORS_EXTENDED[p] || '#6a9fd4';


// ─── Deployment card content ────────────────────────────────────────

interface ActiveDeploymentRowProps {
  deployment: UnifiedDeployment;
  live: DashboardDeployment | undefined;
  onView: () => void;
}

/**
 * One row in the Active Deployments list. Merges the (slow-polling)
 * deployments-store record with the (fast-polling) /dashboard/live
 * payload so the card shows pps and packet count in real time while
 * still naming the agent and scenario from authoritative state.
 */
const ActiveDeploymentRow: React.FC<ActiveDeploymentRowProps> = ({
  deployment, live, onView,
}) => {
  const isPerpetual = (deployment.run_mode ?? 'timed') === 'perpetual';
  const vertical = live?.vertical || undefined;
  const v = vertical ? verticalMeta(vertical) : null;

  const pps = live?.packets_per_second ?? 0;
  const packets = live?.packets_sent ?? deployment.packets_injected ?? 0;

  // Protocol mix: prefer live runtime breakdown; fall back to static
  // declaration from scenario definition.
  const protocols: string[] = (() => {
    if (live?.protocol_breakdown) {
      return Object.entries(live.protocol_breakdown)
        .sort(([, a], [, b]) => (b.packets ?? 0) - (a.packets ?? 0))
        .slice(0, 4)
        .map(([p]) => p);
    }
    if (live?.scenario_protocol_mix?.length) {
      return live.scenario_protocol_mix.slice(0, 4).map((e) => e.protocol);
    }
    return [];
  })();

  // Subtle stat block — right-aligned values with a tiny uppercase
  // label. Keeps the row monochrome except for the vertical pill so
  // active-deployments scan-reads cleanly even with multiple rows.
  const stat = (label: string, value: React.ReactNode, tip?: string) => {
    const node = (
      <div style={{ display: 'flex', flexDirection: 'column', minWidth: 56 }}>
        <Text
          type="secondary"
          style={{ fontSize: 10, letterSpacing: 0.5, textTransform: 'uppercase' }}
        >
          {label}
        </Text>
        <Text style={{ color: '#e6eef7', fontSize: 14, fontWeight: 600, lineHeight: 1.2 }}>
          {value}
        </Text>
      </div>
    );
    return tip ? <Tooltip title={tip}>{node}</Tooltip> : node;
  };

  return (
    <List.Item
      actions={[
        <Button key="view" size="small" type="primary" ghost onClick={onView}>
          Open
        </Button>,
      ]}
    >
      <List.Item.Meta
        avatar={<PlayCircleOutlined style={{ fontSize: 26, color: '#52c41a' }} />}
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <Text strong style={{ fontSize: 14 }}>
              {deployment.scenario_name || 'Unnamed Scenario'}
            </Text>
            {v && (
              <Tag
                color={v.color}
                style={{ margin: 0, borderColor: 'transparent' }}
              >
                {v.label}
              </Tag>
            )}
            <Text type="secondary" style={{ fontSize: 12 }}>
              · {isPerpetual ? 'Perpetual' : 'Timed'}
              {' · '}
              {deployment.agent_name || 'Unknown agent'}
            </Text>
          </div>
        }
        description={
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            {/* Live metrics — neutral monochrome */}
            <div style={{ display: 'flex', gap: 28, alignItems: 'center', flexWrap: 'wrap' }}>
              {stat('PPS', formatPps(pps), 'Packets per second (live)')}
              {stat('Packets', formatNumber(packets), 'Total packets injected')}
              {stat('Uptime', formatElapsedTime(deployment.started_at))}
            </div>

            {/* Protocol mix — small neutral chips with a colored dot.
                Single-color visual weight, color survives as the dot. */}
            {protocols.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {protocols.map((p) => (
                  <span
                    key={p}
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: 6,
                      padding: '2px 8px', borderRadius: 10,
                      background: '#1a2940', border: '1px solid #2a3f54',
                      fontSize: 11, color: '#a8c0d4',
                    }}
                  >
                    <span style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: protocolColor(p),
                    }} />
                    {protocolLabel(p)}
                  </span>
                ))}
              </div>
            )}

            {/* Progress only for timed runs. Slim, no big strokeColor. */}
            {!isPerpetual && (
              <Progress
                percent={calculateProgress(deployment)}
                size="small"
                showInfo={false}
                strokeColor="#52c41a"
                trailColor="#1a2940"
                style={{ margin: 0, maxWidth: 400 }}
              />
            )}
          </Space>
        }
      />
    </List.Item>
  );
};


// ─── Breakdown panels ───────────────────────────────────────────────

interface VerticalMixCardProps {
  entries: { vertical: string; count: number }[];
  loading: boolean;
}

const VerticalMixCard: React.FC<VerticalMixCardProps> = ({ entries, loading }) => {
  const total = entries.reduce((a, b) => a + b.count, 0);
  return (
    <Card
      title={<Space><CompassOutlined /><span>Vertical Mix</span></Space>}
      size="small"
    >
      {loading ? <Spin /> : entries.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="No scenarios yet" />
      ) : (
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          {entries.map((e) => {
            const m = verticalMeta(e.vertical);
            const pct = total === 0 ? 0 : Math.round((e.count / total) * 100);
            return (
              <div key={e.vertical}>
                <div style={{
                  display: 'flex', justifyContent: 'space-between',
                  alignItems: 'center', marginBottom: 4, fontSize: 12,
                }}>
                  <Text style={{ color: m.color }}>{m.label}</Text>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {e.count} ({pct}%)
                  </Text>
                </div>
                <div style={{
                  height: 6, borderRadius: 3, background: '#1a1a2e',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    width: `${pct}%`, height: '100%',
                    background: m.color, transition: 'width 0.3s',
                  }} />
                </div>
              </div>
            );
          })}
        </Space>
      )}
    </Card>
  );
};

interface TopProtocolsCardProps {
  entries: { protocol: string; scenarios: number; devices: number }[];
  loading: boolean;
}

const TopProtocolsCard: React.FC<TopProtocolsCardProps> = ({ entries, loading }) => {
  const maxDevices = Math.max(1, ...entries.map((e) => e.devices));
  return (
    <Card
      title={<Space><ApiOutlined /><span>Top OT Protocols</span></Space>}
      size="small"
    >
      {loading ? <Spin /> : entries.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="No protocols in use" />
      ) : (
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          {entries.map((e) => {
            const color = protocolColor(e.protocol);
            const pct = Math.round((e.devices / maxDevices) * 100);
            return (
              <div key={e.protocol}>
                <div style={{
                  display: 'flex', justifyContent: 'space-between',
                  alignItems: 'center', marginBottom: 4, fontSize: 12,
                }}>
                  <Text style={{ color }}>{protocolLabel(e.protocol)}</Text>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {e.devices} device{e.devices === 1 ? '' : 's'}
                    {' · '}{e.scenarios} scenario{e.scenarios === 1 ? '' : 's'}
                  </Text>
                </div>
                <div style={{
                  height: 6, borderRadius: 3, background: '#1a1a2e',
                  overflow: 'hidden',
                }}>
                  <div style={{
                    width: `${pct}%`, height: '100%',
                    background: color, transition: 'width 0.3s',
                  }} />
                </div>
              </div>
            );
          })}
        </Space>
      )}
    </Card>
  );
};


// ─── Page ───────────────────────────────────────────────────────────

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { deployments, fetchDeployments } = useDeploymentsStore();
  const { liveTrafficEnabled } = useFeatures();

  // Per-user overview KPIs + breakdowns + recent scenarios. Refreshed
  // on focus + every 30 s so the dashboard stays current without
  // hammering the backend.
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats', 'overview'],
    queryFn: getOverviewStats,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
  });

  // Live deployment metrics — pps, packet count, protocol breakdown.
  // 3-second cadence matches the Live Traffic page. Only enabled when
  // the live-traffic feature flag is on.
  const { data: liveData } = useQuery({
    queryKey: ['dashboard', 'live'],
    queryFn: () => dashboardApi.getLive(),
    enabled: liveTrafficEnabled,
    refetchInterval: 3000,
  });

  useEffect(() => {
    if (!liveTrafficEnabled) return;
    fetchDeployments();
  }, [fetchDeployments, liveTrafficEnabled]);

  const runningDeployments = deployments.filter((d) =>
    ['running', 'starting'].includes(d.status),
  );

  const liveByScenario: Record<string, DashboardDeployment> = {};
  for (const d of liveData?.deployments ?? []) {
    liveByScenario[d.scenario_id] = d;
  }

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Hero */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
          <img
            src="/dashboard_logo.png"
            alt="PacketArch"
            style={{ width: 72, height: 72, objectFit: 'contain' }}
          />
          <div style={{ flex: 1 }}>
            <Title level={2} style={{ marginBottom: 2 }}>
              PacketArch
              <ContextualHelpIcon
                articleId="getting-started"
                tooltip="Getting started with PacketArch"
              />
            </Title>
            <Paragraph type="secondary" style={{ marginBottom: 0, fontSize: 13 }}>
              OT Traffic Simulation Platform — protocol-accurate industrial
              traffic for security testing, training, and tool validation.
            </Paragraph>
          </div>
          <Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/scenarios')}
            >
              New Scenario
            </Button>
            <Button
              icon={<AppstoreOutlined />}
              onClick={() => navigate('/studio')}
            >
              Studio
            </Button>
          </Space>
        </div>

        {/* KPI tiles */}
        <Spin spinning={statsLoading}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} lg={6}>
              <Card hoverable onClick={() => navigate('/scenarios')}>
                <Statistic
                  title="Scenarios"
                  value={stats?.scenarios ?? 0}
                  prefix={<AppstoreOutlined />}
                  valueStyle={{ color: '#049FD9' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Device Instances"
                  value={stats?.device_instances ?? 0}
                  prefix={<ThunderboltOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Protocols In Use"
                  value={stats?.protocols ?? 0}
                  prefix={<ApiOutlined />}
                  valueStyle={{ color: '#9C27B0' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <Card>
                <Statistic
                  title="Generated PCAPs"
                  value={stats?.pcaps ?? 0}
                  prefix={<FileTextOutlined />}
                  valueStyle={{ color: '#FBAB18' }}
                />
              </Card>
            </Col>
          </Row>
        </Spin>

        {/* Breakdowns */}
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <VerticalMixCard
              entries={stats?.vertical_mix ?? []}
              loading={statsLoading}
            />
          </Col>
          <Col xs={24} lg={12}>
            <TopProtocolsCard
              entries={stats?.top_protocols ?? []}
              loading={statsLoading}
            />
          </Col>
        </Row>

        {/* Active Deployments */}
        {liveTrafficEnabled && runningDeployments.length > 0 && (
          <Card
            title={
              <Space>
                <SyncOutlined spin style={{ color: '#52c41a' }} />
                <span>Active Deployments ({runningDeployments.length})</span>
              </Space>
            }
            extra={
              <Button size="small" onClick={() => navigate('/live-traffic')}>
                Open Live Traffic →
              </Button>
            }
          >
            <List
              dataSource={runningDeployments}
              renderItem={(deployment) => (
                <ActiveDeploymentRow
                  deployment={deployment}
                  live={liveByScenario[deployment.scenario_id]}
                  onView={() =>
                    navigate(`/studio?scenario=${deployment.scenario_id}`)
                  }
                />
              )}
            />
          </Card>
        )}

        {/* Recent scenarios + Tips */}
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={16}>
            <Card
              title={
                <Space>
                  <ClockCircleOutlined />
                  <span>Recently Updated Scenarios</span>
                </Space>
              }
              extra={
                <Button size="small" type="link" onClick={() => navigate('/scenarios')}>
                  View all
                </Button>
              }
            >
              {statsLoading ? (
                <Spin />
              ) : (stats?.recent_scenarios?.length ?? 0) === 0 ? (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    <Space direction="vertical" size={4}>
                      <Text type="secondary">No scenarios yet</Text>
                      <Button
                        type="primary"
                        size="small"
                        icon={<PlusOutlined />}
                        onClick={() => navigate('/scenarios')}
                      >
                        Create your first scenario
                      </Button>
                    </Space>
                  }
                />
              ) : (
                <List
                  dataSource={stats?.recent_scenarios ?? []}
                  renderItem={(s) => {
                    const v = s.vertical ? verticalMeta(s.vertical) : null;
                    return (
                      <List.Item
                        actions={[
                          <Button
                            key="open"
                            size="small"
                            onClick={() => navigate(`/studio?scenario=${s.id}`)}
                          >
                            Open
                          </Button>,
                        ]}
                      >
                        <List.Item.Meta
                          title={
                            <Space>
                              <Text strong>{s.name}</Text>
                              {v && (
                                <Tag color={v.color} style={{ margin: 0 }}>
                                  {v.label}
                                </Tag>
                              )}
                            </Space>
                          }
                          description={
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {s.device_count} device{s.device_count === 1 ? '' : 's'}
                              {' · '}{s.flow_count} flow{s.flow_count === 1 ? '' : 's'}
                              {' · '}{formatRelativeTime(s.updated_at)}
                            </Text>
                          }
                        />
                      </List.Item>
                    );
                  }}
                />
              )}
            </Card>
          </Col>
          <Col xs={24} lg={8}>
            <Card
              title={<Space><BulbOutlined /><span>Tips & Shortcuts</span></Space>}
              size="small"
            >
              <Space direction="vertical" size={10} style={{ width: '100%' }}>
                <div>
                  <Text strong style={{ fontSize: 13 }}>Generate from a description</Text>
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      In the Studio, open the AI panel and describe the plant in plain English — PacketArch builds the topology, vendors, and flows.
                    </Text>
                  </div>
                </div>
                <div>
                  <Text strong style={{ fontSize: 13 }}>Group canvas by zone</Text>
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      Press <Text code>G</Text> on the canvas to cycle group views. By-Zone lays out Purdue bands (L0 bottom, L4 top).
                    </Text>
                  </div>
                </div>
                <div>
                  <Text strong style={{ fontSize: 13 }}>Download a scenario report</Text>
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      Every scenario card has a one-click PDF report with the full IP plan, device inventory, flows, and conduits.
                    </Text>
                  </div>
                </div>
                <Button
                  type="default"
                  icon={<RocketOutlined />}
                  block
                  onClick={() => navigate('/help')}
                >
                  Open Help Center
                </Button>
              </Space>
            </Card>
          </Col>
        </Row>
      </Space>
    </div>
  );
};

export default DashboardPage;
