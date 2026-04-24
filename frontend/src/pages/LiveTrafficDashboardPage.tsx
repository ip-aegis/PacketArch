/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React, { useEffect, useCallback } from 'react';
import { Typography, Space, Spin, Alert, Tag } from 'antd';
import { SyncOutlined } from '@ant-design/icons';
import { useLiveDashboardStore } from '../stores/liveDashboardStore';
import { healthMonitorApi } from '../api/healthMonitor';
import AggregateStatsRow from '../components/dashboard/AggregateStatsRow';
import AgentStatusCards from '../components/dashboard/AgentStatusCards';
import DeploymentCard from '../components/dashboard/DeploymentCard';
import EmptyDashboard from '../components/dashboard/EmptyDashboard';
import HealthEventsFeed from '../components/dashboard/HealthEventsFeed';

const { Title, Text } = Typography;

const LiveTrafficDashboardPage: React.FC = () => {
  const { data, isLoading, error, lastUpdated, startPolling, stopPolling, fetchDashboard } = useLiveDashboardStore();

  useEffect(() => {
    startPolling(3000);
    return () => stopPolling();
  }, [startPolling, stopPolling]);

  const secondsAgo = lastUpdated ? Math.round((Date.now() - lastUpdated) / 1000) : null;

  const handleAcknowledgeEvent = useCallback(async (eventId: string) => {
    try {
      await healthMonitorApi.acknowledgeEvent(eventId);
      // Trigger a dashboard refresh to update the events list
      fetchDashboard();
    } catch {
      // Silently ignore — event will disappear on next poll
    }
  }, [fetchDashboard]);

  return (
    <div>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Title level={2} style={{ marginBottom: 0 }}>Live Traffic</Title>
          <Space>
            {data && data.aggregate.active_deployments > 0 && (
              <Tag icon={<SyncOutlined spin />} color="green">Live</Tag>
            )}
            {secondsAgo !== null && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                Updated {secondsAgo < 2 ? 'just now' : `${secondsAgo}s ago`}
              </Text>
            )}
          </Space>
        </div>

        {/* Error state */}
        {error && <Alert type="error" message={error} showIcon closable />}

        {/* Loading state (first load only) */}
        {isLoading && !data && (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin size="large" />
          </div>
        )}

        {/* Dashboard content */}
        {data && (
          <>
            {/* Aggregate Stats */}
            <AggregateStatsRow aggregate={data.aggregate} />

            {/* Health Events */}
            {data.health && (
              <div>
                <HealthEventsFeed
                  health={data.health}
                  onAcknowledge={handleAcknowledgeEvent}
                />
              </div>
            )}

            {/* Agent Cards */}
            {data.agents.length > 0 && (
              <div>
                <Text type="secondary" style={{ fontSize: 13, marginBottom: 8, display: 'block' }}>
                  Connected Agents
                </Text>
                <AgentStatusCards
                  agents={data.agents}
                  healthStatuses={data.health?.agent_statuses}
                />
              </div>
            )}

            {/* Deployment Cards or Empty State */}
            {data.deployments.length > 0 ? (
              <div>
                <Text type="secondary" style={{ fontSize: 13, marginBottom: 8, display: 'block' }}>
                  Active Deployments
                </Text>
                <Space direction="vertical" size={16} style={{ width: '100%' }}>
                  {data.deployments.map((deployment) => (
                    <DeploymentCard key={deployment.scenario_id} deployment={deployment} />
                  ))}
                </Space>
              </div>
            ) : (
              <EmptyDashboard />
            )}
          </>
        )}
      </Space>
    </div>
  );
};

export default LiveTrafficDashboardPage;
