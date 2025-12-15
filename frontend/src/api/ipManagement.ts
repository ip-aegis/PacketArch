/**
 * IP Management API functions
 */

import apiClient from './client';

export interface IPRangeAllocation {
  id: string;
  scenario_id: string;
  scenario_name: string;
  range_index: number;
  cidr_range: string;
  next_host_offset: number;
  created_at: string;
}

export interface IPRangeListResponse {
  items: IPRangeAllocation[];
  total: number;
  available_ranges: number[];
}

export interface NextIPResponse {
  ip_address: string;
  subnet_mask: string;
  gateway: string;
  cidr: string;
}

export interface ScenarioIPInfo {
  scenario_id: string;
  scenario_name: string;
  cidr_range: string;
  range_index: number;
  devices_with_ips: number;
  next_available_ip: string;
  gateway: string;
}

const IP_MANAGEMENT_PREFIX = '/api/v1/ip-management';

export const ipManagementApi = {
  /**
   * List all IP range allocations
   */
  async listAllocations(): Promise<IPRangeListResponse> {
    const response = await apiClient.get<IPRangeListResponse>(IP_MANAGEMENT_PREFIX);
    return response.data;
  },

  /**
   * Get IP info for a specific scenario
   */
  async getScenarioIPInfo(scenarioId: string): Promise<ScenarioIPInfo> {
    const response = await apiClient.get<ScenarioIPInfo>(
      `${IP_MANAGEMENT_PREFIX}/scenario/${scenarioId}`
    );
    return response.data;
  },

  /**
   * Get next available IP for a scenario (also increments the offset)
   */
  async getNextIP(scenarioId: string): Promise<NextIPResponse> {
    const response = await apiClient.get<NextIPResponse>(
      `${IP_MANAGEMENT_PREFIX}/scenario/${scenarioId}/next-ip`
    );
    return response.data;
  },
};

export default ipManagementApi;
