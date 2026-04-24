/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Stats API client for dashboard statistics
 */

import apiClient from './client';

export interface OverviewStats {
  scenarios: number;
  devices: number;
  protocols: number;
  pcaps: number;
}

/**
 * Get overview statistics for the dashboard
 */
export const getOverviewStats = async (): Promise<OverviewStats> => {
  const response = await apiClient.get<OverviewStats>('/stats/overview');
  return response.data;
};

export default {
  getOverviewStats,
};
