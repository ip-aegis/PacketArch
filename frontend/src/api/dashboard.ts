/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import apiClient from './client';

export interface DashboardProtocolStats {
  packets: number;
  bytes: number;
  flow_count: number;
  pps?: number;
}

export interface DashboardTimeSeriesPoint {
  t: string;
  pps: number;
  bps: number;
}

export interface DashboardAttackState {
  playbook_id: string;
  playbook_name: string;
  is_active: boolean;
  is_paused: boolean;
  is_completed: boolean;
  current_stage: string;
  current_stage_name: string;
  current_stage_color: string;
  current_stage_index: number;
  stage_progress_pct: number;
  stage_remaining_s: number;
  stages_completed: number;
  total_stages: number;
  actions_completed: number;
  attack_packets_generated: number;
}

export interface DashboardDeployment {
  scenario_id: string;
  scenario_name: string | null;
  agent_id: string;
  agent_name: string;
  state: string;
  packets_sent: number;
  bytes_sent: number;
  flow_count: number;
  packets_per_second: number;
  bytes_per_second: number;
  uptime_seconds: number;
  protocol_breakdown: Record<string, DashboardProtocolStats> | null;
  attack: DashboardAttackState | null;
  time_series: DashboardTimeSeriesPoint[];
  scenario_modes?: {
    clean_demo_mode: boolean;
    broadcast_traffic_enabled: boolean;
    cell_isolation_mode: string;
  };
  /** Cyber Vision provisioning summary (null when not provisioned). */
  cyber_vision?: {
    status: 'not_started' | 'preset_created' | 'polling' | 'groups_created' | 'error';
    preset_label: string | null;
    subnet: string | null;
    group_count: number;
    device_count: number;
  } | null;
  /** Industry vertical from the scenario definition. */
  vertical?: string | null;
  /** Static protocol mix derived from the scenario's device fleet —
   *  used as a fallback when the agent hasn't reported a live
   *  protocol_breakdown yet. */
  scenario_protocol_mix?: Array<{ protocol: string; device_count: number }>;
}

export interface DashboardAgent {
  agent_id: string;
  agent_name: string;
  hostname: string | null;
  cpu_percent: number;
  memory_percent: number;
  is_online: boolean;
  active_deployments: number;
  total_packets_per_second: number;
  total_bytes_per_second: number;
  /** 'local' = local sensor lab on the PacketArch host; 'cml'/'manual' = remote. */
  kind?: 'local' | 'cml' | 'manual';
  /** Local-lab agents only: the lab's name (e.g. topo-824d17b0-core). */
  lab_name?: string | null;
  /** Topology group (scenario short-id) this lab belongs to, if any. */
  group_key?: string | null;
  /** Scenario name for the topology group, for the group header. */
  group_label?: string | null;
  /** True for the core lab's agent — the single injector for its topology. */
  is_conductor?: boolean;
}

/** Host-wide CPU/RAM — one gauge shared by every local agent. */
export interface DashboardHostStats {
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  cores: number;
}

export interface DashboardAggregate {
  total_packets_per_second: number;
  total_bytes_per_second: number;
  active_deployments: number;
  connected_agents: number;
  total_packets_sent: number;
  total_bytes_sent: number;
}

export interface DashboardHealthData {
  agent_statuses: Record<string, 'healthy' | 'warning' | 'critical' | 'offline'>;
  recent_events: Array<{
    id: string;
    timestamp: string;
    event_type: string;
    severity: 'info' | 'warning' | 'critical';
    agent_id: string;
    agent_name: string;
    scenario_id: string | null;
    message: string;
    details: Record<string, unknown>;
    acknowledged: boolean;
  }>;
  unacknowledged_count: number;
}

export interface LiveDashboardData {
  aggregate: DashboardAggregate;
  agents: DashboardAgent[];
  deployments: DashboardDeployment[];
  health?: DashboardHealthData;
  host?: DashboardHostStats | null;
}

const DASHBOARD_PREFIX = '/api/v1/dashboard';

export const dashboardApi = {
  async getLive(): Promise<LiveDashboardData> {
    const response = await apiClient.get<LiveDashboardData>(`${DASHBOARD_PREFIX}/live`);
    return response.data;
  },
};
