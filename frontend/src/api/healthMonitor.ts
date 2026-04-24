/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Health Monitor API Client
 * Endpoints for agent health monitoring, events, and configuration
 */

import apiClient from './client';

export interface HealthEvent {
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
}

export interface HealthEventsResponse {
  events: HealthEvent[];
  total: number;
  unacknowledged_count: number;
  counts_by_severity: { info: number; warning: number; critical: number };
}

export interface AgentHealthDetail {
  status: 'healthy' | 'warning' | 'critical' | 'offline';
  heartbeat_ok: boolean;
  resource_ok: boolean;
  stalled_scenarios: string[];
  recent_recoveries: number;
}

export interface HealthStatusResponse {
  agents: Record<string, AgentHealthDetail>;
  summary: { healthy: number; warning: number; critical: number; offline: number };
  auto_recovery_enabled: boolean;
  auto_redeploy_on_reconnect: boolean;
  monitoring_active: boolean;
}

export interface HealthMonitorConfig {
  check_interval_seconds: number;
  heartbeat_timeout_seconds: number;
  stall_detection_seconds: number;
  stall_grace_period_seconds: number;
  resource_warning_threshold: number;
  resource_critical_threshold: number;
  resource_sustained_seconds: number;
  max_recovery_attempts_per_hour: number;
  recovery_cooldown_seconds: number;
  auto_recovery_enabled: boolean;
  auto_redeploy_on_reconnect: boolean;
}

export interface DashboardHealthData {
  agent_statuses: Record<string, 'healthy' | 'warning' | 'critical' | 'offline'>;
  recent_events: HealthEvent[];
  unacknowledged_count: number;
}

const PREFIX = '/api/v1/health-monitor';

export const healthMonitorApi = {
  async getEvents(limit = 50, offset = 0, severity?: string): Promise<HealthEventsResponse> {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (severity) params.append('severity', severity);
    const res = await apiClient.get<HealthEventsResponse>(`${PREFIX}/events?${params}`);
    return res.data;
  },

  async getStatus(): Promise<HealthStatusResponse> {
    const res = await apiClient.get<HealthStatusResponse>(`${PREFIX}/status`);
    return res.data;
  },

  async acknowledgeEvent(eventId: string): Promise<void> {
    await apiClient.post(`${PREFIX}/events/${eventId}/acknowledge`);
  },

  async getConfig(): Promise<HealthMonitorConfig> {
    const res = await apiClient.get<HealthMonitorConfig>(`${PREFIX}/config`);
    return res.data;
  },

  async updateConfig(config: Partial<HealthMonitorConfig>): Promise<HealthMonitorConfig> {
    const res = await apiClient.put<HealthMonitorConfig>(`${PREFIX}/config`, config);
    return res.data;
  },

  async clearEvents(): Promise<void> {
    await apiClient.delete(`${PREFIX}/events`);
  },
};
