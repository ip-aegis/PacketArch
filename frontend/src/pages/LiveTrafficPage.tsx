/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Live Traffic — the runtime view of the platform, split out from the Agents
 * hub (which now covers infrastructure only: fleet, labs, topology). Embeds the
 * existing prop-less page components as tabs so nothing is duplicated.
 *
 *   Live Dashboard — real-time agent/deployment telemetry (was /live-traffic)
 *   Deployments    — scenario deployment history + controls (was /deployments)
 */

import React, { useState } from 'react';
import { Tabs, Typography } from 'antd';
import type { TabsProps } from 'antd';
import { BarChartOutlined, RocketOutlined } from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';

import LiveTrafficDashboardPage from './LiveTrafficDashboardPage';
import DeploymentsPage from './DeploymentsPage';

const { Title } = Typography;

const LiveTrafficPage: React.FC = () => {
  // Deep-linkable tab via ?tab=, matching the AgentsHub / SettingsPage convention.
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') || 'dashboard';
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
      key: 'dashboard',
      label: (
        <span>
          <BarChartOutlined /> Live Dashboard
        </span>
      ),
      children: <LiveTrafficDashboardPage />,
    },
    {
      key: 'deployments',
      label: (
        <span>
          <RocketOutlined /> Deployments
        </span>
      ),
      children: <DeploymentsPage />,
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginTop: 0 }}>
        Live Traffic
      </Title>
      <Tabs activeKey={activeKey} onChange={onChange} items={items} destroyInactiveTabPane />
    </div>
  );
};

export default LiveTrafficPage;
