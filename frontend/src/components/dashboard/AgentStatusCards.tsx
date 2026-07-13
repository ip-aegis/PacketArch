/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React from 'react';
import { Card, Progress, Space, Typography, Tag } from 'antd';
import { CloudServerOutlined, DesktopOutlined } from '@ant-design/icons';
import type { DashboardAgent, DashboardHostStats } from '../../api/dashboard';
import { formatPacketRate } from '../../utils/formatUtils';

const { Text } = Typography;

type HealthStatus = 'healthy' | 'warning' | 'critical' | 'offline';

interface AgentStatusCardsProps {
  agents: DashboardAgent[];
  healthStatuses?: Record<string, HealthStatus>;
  host?: DashboardHostStats | null;
}

const HEALTH_TAG_CONFIG: Record<string, { color: string; label: string }> = {
  healthy: { color: 'green', label: 'Healthy' },
  warning: { color: 'orange', label: 'Warning' },
  critical: { color: 'red', label: 'Critical' },
  offline: { color: 'default', label: 'Offline' },
};

const OUTER_CARD_STYLE: React.CSSProperties = {
  background: '#1a1a2e',
  border: '1px solid #2d2d52',
};

// Nested inside the host card — slightly darker so the grouping reads.
const INNER_CARD_STYLE: React.CSSProperties = {
  background: '#12122b',
  border: '1px solid #2d2d52',
  flex: '0 0 auto',
};

const healthTag = (agent: DashboardAgent, healthStatuses?: Record<string, HealthStatus>) => {
  const status = healthStatuses?.[agent.agent_id];
  const cfg = status
    ? HEALTH_TAG_CONFIG[status]
    : agent.is_online
      ? HEALTH_TAG_CONFIG.healthy
      : HEALTH_TAG_CONFIG.offline;
  return (
    <Tag color={cfg.color} style={{ marginLeft: 'auto', marginRight: 0 }}>
      {cfg.label}
    </Tag>
  );
};

/** Per-agent activity line. Zone agents in a multi-sensor topology carry the
 * lab (veth + sensor) while the single core conductor does all injection, so
 * an agent with no deployment is healthy-idle, not broken — say "standby". */
const activityLine = (agent: DashboardAgent) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
    <Text type="secondary" style={{ fontSize: 12 }}>
      {agent.active_deployments > 0
        ? `${agent.active_deployments} deployment${agent.active_deployments !== 1 ? 's' : ''}`
        : 'standby'}
    </Text>
    {agent.active_deployments > 0 && (
      <Text style={{ fontSize: 12, color: '#1890ff' }}>
        {formatPacketRate(agent.total_packets_per_second)} pkt/s
      </Text>
    )}
  </div>
);

/** Compact card for a local-lab agent — no CPU/RAM bars; the host gauge above
 * covers all of them (they share the PacketArch host). */
const LocalAgentCard: React.FC<{
  agent: DashboardAgent;
  healthStatuses?: Record<string, HealthStatus>;
}> = ({ agent, healthStatuses }) => (
  <Card
    size="small"
    style={{
      ...INNER_CARD_STYLE,
      width: 230,
      ...(agent.is_conductor ? { borderColor: '#d4a017' } : {}),
    }}
  >
    <Space direction="vertical" size={6} style={{ width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <CloudServerOutlined style={{ color: agent.is_online ? '#52c41a' : '#ff4d4f' }} />
        <Text
          strong
          style={{ color: '#fff', fontSize: 13, flex: 1, minWidth: 0 }}
          ellipsis={{ tooltip: agent.agent_name }}
        >
          {agent.agent_name}
        </Text>
        {healthTag(agent, healthStatuses)}
      </div>
      {agent.is_conductor && (
        <Tag color="gold" style={{ marginRight: 0, alignSelf: 'flex-start' }}>
          Conductor
        </Tag>
      )}
      {activityLine(agent)}
    </Space>
  </Card>
);

/** Local agents grouped by topology: the conductor leads its group, zone
 * agents follow; non-topology labs land in a "Standalone" bucket. */
const groupLocalAgents = (agents: DashboardAgent[]) => {
  const groups = new Map<string, { label: string; agents: DashboardAgent[] }>();
  for (const agent of agents) {
    const key = agent.group_key ?? '_standalone';
    const label = agent.group_label
      ?? (agent.group_key ? `Topology ${agent.group_key}` : 'Standalone Labs');
    const g = groups.get(key) ?? { label, agents: [] };
    g.agents.push(agent);
    groups.set(key, g);
  }
  const sorted = [...groups.entries()].sort(([a], [b]) =>
    a === '_standalone' ? 1 : b === '_standalone' ? -1 : a.localeCompare(b),
  );
  for (const [, g] of sorted) {
    g.agents.sort((x, y) =>
      Number(y.is_conductor ?? false) - Number(x.is_conductor ?? false)
      || x.agent_name.localeCompare(y.agent_name),
    );
  }
  return sorted;
};

/** The local section: one host-wide CPU/RAM gauge with every local agent's
 * card nested inside it — they all run on (and share) the PacketArch host. */
const LocalHostSection: React.FC<{
  agents: DashboardAgent[];
  healthStatuses?: Record<string, HealthStatus>;
  host?: DashboardHostStats | null;
}> = ({ agents, healthStatuses, host }) => (
  <Card size="small" style={OUTER_CARD_STYLE}>
    <Space direction="vertical" size={10} style={{ width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <DesktopOutlined style={{ color: '#1890ff' }} />
        <Text strong style={{ color: '#fff' }}>PacketArch Host</Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {agents.length} local agent{agents.length !== 1 ? 's' : ''}
          {host ? ` · ${host.cores} cores` : ''}
        </Text>
      </div>

      {host && (
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 220px', minWidth: 180 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>System CPU</Text>
            <Progress
              percent={Math.round(host.cpu_percent)}
              size="small"
              strokeColor={host.cpu_percent > 80 ? '#ff4d4f' : '#1890ff'}
              trailColor="#2d2d52"
            />
          </div>
          <div style={{ flex: '1 1 220px', minWidth: 180 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              System Memory · {host.memory_used_gb} / {host.memory_total_gb} GB
            </Text>
            <Progress
              percent={Math.round(host.memory_percent)}
              size="small"
              strokeColor={host.memory_percent > 80 ? '#ff4d4f' : '#722ed1'}
              trailColor="#2d2d52"
            />
          </div>
        </div>
      )}

      {groupLocalAgents(agents).map(([key, group]) => (
        <div key={key}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>{group.label}</Text>
            <Text type="secondary" style={{ fontSize: 11 }}>
              · {group.agents.length} agent{group.agents.length !== 1 ? 's' : ''}
            </Text>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {group.agents.map((agent) => (
              <LocalAgentCard key={agent.agent_id} agent={agent} healthStatuses={healthStatuses} />
            ))}
          </div>
        </div>
      ))}
    </Space>
  </Card>
);

/** Full card for a remote (CML/manual) agent — it has its own CPU/RAM. */
const RemoteAgentCard: React.FC<{
  agent: DashboardAgent;
  healthStatuses?: Record<string, HealthStatus>;
}> = ({ agent, healthStatuses }) => (
  <Card size="small" style={{ ...OUTER_CARD_STYLE, width: 260, flex: '0 0 auto' }}>
    <Space direction="vertical" size={8} style={{ width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <CloudServerOutlined style={{ color: agent.is_online ? '#52c41a' : '#ff4d4f' }} />
        <Text
          strong
          style={{ color: '#fff', flex: 1, minWidth: 0 }}
          ellipsis={{ tooltip: agent.agent_name }}
        >
          {agent.agent_name}
        </Text>
        {healthTag(agent, healthStatuses)}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Tag style={{ marginRight: 0 }}>{agent.kind === 'cml' ? 'CML' : 'Remote'}</Tag>
        {agent.hostname && (
          <Text type="secondary" style={{ fontSize: 12 }} ellipsis={{ tooltip: agent.hostname }}>
            {agent.hostname}
          </Text>
        )}
      </div>

      <div>
        <Text type="secondary" style={{ fontSize: 12 }}>CPU</Text>
        <Progress
          percent={Math.round(agent.cpu_percent)}
          size="small"
          strokeColor={agent.cpu_percent > 80 ? '#ff4d4f' : '#1890ff'}
          trailColor="#2d2d52"
        />
      </div>

      <div>
        <Text type="secondary" style={{ fontSize: 12 }}>Memory</Text>
        <Progress
          percent={Math.round(agent.memory_percent)}
          size="small"
          strokeColor={agent.memory_percent > 80 ? '#ff4d4f' : '#722ed1'}
          trailColor="#2d2d52"
        />
      </div>

      {activityLine(agent)}
    </Space>
  </Card>
);

const AgentStatusCards: React.FC<AgentStatusCardsProps> = ({ agents, healthStatuses, host }) => {
  if (agents.length === 0) return null;

  const local = agents.filter((a) => a.kind === 'local');
  const remote = agents.filter((a) => a.kind !== 'local');

  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      {local.length > 0 && (
        <LocalHostSection agents={local} healthStatuses={healthStatuses} host={host} />
      )}

      {remote.length > 0 && (
        <div>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
            Remote Agents
          </Text>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
            {remote.map((agent) => (
              <RemoteAgentCard key={agent.agent_id} agent={agent} healthStatuses={healthStatuses} />
            ))}
          </div>
        </div>
      )}
    </Space>
  );
};

export default AgentStatusCards;
