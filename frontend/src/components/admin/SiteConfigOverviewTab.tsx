/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Site config overview — one-glance status of every major subsystem with
 * deep-links to the specific Settings tabs that own the edit flows.
 *
 * Aggregation-only; this component never writes. For edits the user clicks
 * "Configure →" which switches the parent <Tabs> to the subsystem's tab.
 */

import React, { useEffect, useState } from 'react';
import {
  Card,
  Typography,
  Space,
  Tag,
  Button,
  Row,
  Col,
  Skeleton,
  Alert,
  Divider,
} from 'antd';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  StopOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import {
  siteConfigApi,
  type SiteConfigResponse,
  type SubsystemStatus,
} from '../../api/siteConfig';

const { Title, Text, Paragraph } = Typography;

const STATUS_META: Record<
  SubsystemStatus,
  { color: string; icon: React.ReactNode; label: string }
> = {
  ok: { color: 'green', icon: <CheckCircleOutlined />, label: 'OK' },
  needs_attention: {
    color: 'orange',
    icon: <ExclamationCircleOutlined />,
    label: 'Needs attention',
  },
  disabled: { color: 'default', icon: <StopOutlined />, label: 'Disabled' },
  unknown: {
    color: 'default',
    icon: <QuestionCircleOutlined />,
    label: 'Unknown',
  },
};

interface SiteConfigOverviewTabProps {
  /** Called when user clicks "Configure" on a subsystem card.
   *  Passes the tab key the parent <Tabs> should switch to. */
  onSelectTab: (key: string) => void;
}

const SiteConfigOverviewTab: React.FC<SiteConfigOverviewTabProps> = ({
  onSelectTab,
}) => {
  const [data, setData] = useState<SiteConfigResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    siteConfigApi
      .get()
      .then(setData)
      .catch(() => setError('Could not load site configuration.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  if (loading && !data) return <Skeleton active paragraph={{ rows: 8 }} />;
  if (error) return <Alert type="error" message={error} showIcon />;
  if (!data) return null;

  const attentionCount = data.subsystems.filter(
    (s) => s.status === 'needs_attention',
  ).length;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {/* Product / license summary */}
      <Card size="small">
        <Row gutter={[16, 8]}>
          <Col xs={24} md={12}>
            <Title level={4} style={{ margin: 0 }}>
              {data.product.name} v{data.product.version}
            </Title>
            <Text type="secondary">
              Maintained by {data.product.owner_name} &lt;
              {data.product.owner_email}&gt;
            </Text>
          </Col>
          <Col xs={24} md={12} style={{ textAlign: 'right' }}>
            <Space size="small">
              <Tag color="blue">{data.product.license_id}</Tag>
              <Tag color={data.features.ai_enabled ? 'cyan' : 'default'}>
                AI {data.features.ai_enabled ? 'enabled' : 'disabled'}
              </Tag>
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={load}
                loading={loading}
              >
                Refresh
              </Button>
            </Space>
            <div style={{ marginTop: 4 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {data.product.acknowledgments_on_current_version} user acknowledgment(s) on{' '}
                {data.product.acknowledgment_document} v
                {data.product.acknowledgment_version}
              </Text>
            </div>
          </Col>
        </Row>
      </Card>

      {attentionCount > 0 && (
        <Alert
          type="warning"
          showIcon
          message={`${attentionCount} subsystem${attentionCount === 1 ? '' : 's'} need${
            attentionCount === 1 ? 's' : ''
          } attention`}
          description="See the cards below. Click Configure to jump to the relevant settings tab."
        />
      )}

      {/* Subsystem cards */}
      <Row gutter={[16, 16]}>
        {data.subsystems.map((sub) => {
          const meta = STATUS_META[sub.status];
          return (
            <Col key={sub.key} xs={24} md={12}>
              <Card
                size="small"
                styles={{ body: { padding: 16 } }}
                title={
                  <Space>
                    <Text strong>{sub.label}</Text>
                    <Tag color={meta.color} icon={meta.icon}>
                      {meta.label}
                    </Tag>
                  </Space>
                }
                extra={
                  sub.key === 'licensing' ? null : (
                    <Button
                      type="link"
                      size="small"
                      onClick={() => onSelectTab(sub.key)}
                    >
                      Configure →
                    </Button>
                  )
                }
              >
                <Paragraph style={{ marginBottom: 8 }}>{sub.summary}</Paragraph>
                {Object.keys(sub.detail).length > 0 && (
                  <>
                    <Divider style={{ margin: '8px 0' }} />
                    <Space direction="vertical" size={2} style={{ width: '100%' }}>
                      {Object.entries(sub.detail).map(([k, v]) => (
                        <div
                          key={k}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            fontSize: 12,
                          }}
                        >
                          <Text type="secondary">{k}</Text>
                          <Text code style={{ fontSize: 11 }}>
                            {v === null || v === ''
                              ? '—'
                              : typeof v === 'boolean'
                                ? v
                                  ? 'true'
                                  : 'false'
                                : String(v)}
                          </Text>
                        </div>
                      ))}
                    </Space>
                  </>
                )}
              </Card>
            </Col>
          );
        })}
      </Row>
    </Space>
  );
};

export default SiteConfigOverviewTab;
