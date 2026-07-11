/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Agents hub — the single operations home for remote/local traffic agents,
 * labs, deployments, and live traffic. Consolidates what previously lived in
 * scattered Settings tabs and standalone pages by EMBEDDING the existing
 * prop-less components, so nothing is duplicated or lost (additive).
 *
 *   Agents        — traffic-agent fleet (lifted from Settings → Traffic Agents)
 *   Topology      — live agent → SPAN → sensor flow visualization
 *   Local Labs    — on-box agent + CV sensor labs
 *   Modeling Labs — CML build/deploy
 *
 * The runtime view (Live Dashboard + Deployments) lives on its own page,
 * /live-traffic, so this hub stays focused on infrastructure.
 */

import React, { useEffect, useState } from 'react';
import { Tabs, Typography, Row, Col, Card, Statistic } from 'antd';
import type { TabsProps } from 'antd';
import {
  CloudServerOutlined,
  ApiOutlined,
  ClusterOutlined,
  WifiOutlined,
  PartitionOutlined,
} from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';

import AgentsTab from '../components/admin/AgentsTab';
import AgentTopology from '../components/agents/AgentTopology';
import LocalLabsTab from '../components/agents/LocalLabsTab';
import CmlTab from '../components/admin/CmlTab';
import { agentsApi } from '../api/agents';
import { localSensorApi } from '../api/localSensor';

const { Title } = Typography;

const statCardStyle: React.CSSProperties = {
  background: '#1a1a2e',
  border: '1px solid #2d2d52',
};

/** Compact fleet summary across all agent kinds + local labs. Best-effort:
 *  failures leave the counts at zero rather than breaking the hub. */
const FleetStatRow: React.FC = () => {
  const [stats, setStats] = useState({ total: 0, online: 0, localLabs: 0, cmlLabs: 0 });

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [agentsResp, labsResp] = await Promise.all([
          agentsApi.list(1, 100).catch(() => ({ agents: [] as Array<{ status: string; cml_lab_id?: string | null }> })),
          localSensorApi.getLabs().catch(() => ({ items: [] })),
        ]);
        const agents = (agentsResp as { agents: Array<{ status: string; cml_lab_id?: string | null }> }).agents || [];
        if (cancelled) return;
        setStats({
          total: agents.length,
          online: agents.filter((a) => a.status === 'online').length,
          localLabs: labsResp.items.length,
          cmlLabs: agents.filter((a) => a.cml_lab_id).length,
        });
      } catch {
        /* leave zeros */
      }
    };
    load();
    const t = setInterval(load, 10000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  return (
    <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
      <Col xs={12} lg={6}>
        <Card style={statCardStyle} size="small">
          <Statistic title="Agents" value={stats.total} prefix={<ApiOutlined />} valueStyle={{ color: '#1890ff' }} />
        </Card>
      </Col>
      <Col xs={12} lg={6}>
        <Card style={statCardStyle} size="small">
          <Statistic title="Online" value={stats.online} prefix={<WifiOutlined />} valueStyle={{ color: '#52c41a' }} />
        </Card>
      </Col>
      <Col xs={12} lg={6}>
        <Card style={statCardStyle} size="small">
          <Statistic title="Local Labs" value={stats.localLabs} prefix={<CloudServerOutlined />} valueStyle={{ color: '#13c2c2' }} />
        </Card>
      </Col>
      <Col xs={12} lg={6}>
        <Card style={statCardStyle} size="small">
          <Statistic title="CML Labs" value={stats.cmlLabs} prefix={<ClusterOutlined />} valueStyle={{ color: '#722ed1' }} />
        </Card>
      </Col>
    </Row>
  );
};

const AgentsHubPage: React.FC = () => {
  // Deep-linkable tab via ?tab=, matching the SettingsPage convention.
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') || 'agents';
  const [activeKey, setActiveKey] = useState(initialTab);

  const onChange = (key: string) => {
    setActiveKey(key);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('tab', key);
      return next;
    });
  };

  const items: TabsProps['items'] = [
    {
      key: 'agents',
      label: (
        <span>
          <ApiOutlined /> Agents
        </span>
      ),
      children: <AgentsTab />,
    },
    {
      key: 'topology',
      label: (
        <span>
          <PartitionOutlined /> Topology
        </span>
      ),
      children: <AgentTopology />,
    },
    {
      key: 'local-labs',
      label: (
        <span>
          <CloudServerOutlined /> Local Labs
        </span>
      ),
      children: <LocalLabsTab />,
    },
    {
      key: 'cml',
      label: (
        <span>
          <ClusterOutlined /> Modeling Labs
        </span>
      ),
      children: <CmlTab />,
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginTop: 0 }}>
        Agents
      </Title>
      <FleetStatRow />
      <Tabs activeKey={activeKey} onChange={onChange} items={items} destroyInactiveTabPane />
    </div>
  );
};

export default AgentsHubPage;
