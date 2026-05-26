/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Stats API client for dashboard statistics
 */

import apiClient from './client';

const STATS_PREFIX = '/api/v1/stats';

export interface VerticalMixEntry {
  vertical: string;
  count: number;
}

export interface ProtocolUsageEntry {
  protocol: string;
  scenarios: number;
  devices: number;
}

export interface RecentScenarioEntry {
  id: string;
  name: string;
  vertical: string | null;
  device_count: number;
  flow_count: number;
  updated_at: string | null;
}

export interface OverviewStats {
  scenarios: number;
  /** Total device *instances* across the user's scenarios. */
  device_instances: number;
  protocols: number;
  pcaps: number;
  vertical_mix: VerticalMixEntry[];
  top_protocols: ProtocolUsageEntry[];
  recent_scenarios: RecentScenarioEntry[];
}

/**
 * Get overview statistics for the dashboard.
 */
export const getOverviewStats = async (): Promise<OverviewStats> => {
  const response = await apiClient.get<OverviewStats>(`${STATS_PREFIX}/overview`);
  return response.data;
};

export default {
  getOverviewStats,
};
