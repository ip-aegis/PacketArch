/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Local sensor lab API — app-managed (agent + CV sensor + virtual SPAN) labs
 * on the PacketArch host itself. Mirrors api/cml.ts.
 */

import apiClient from './client';

export interface LocalHostStatus {
  available: boolean;
  host_agent_seen: boolean;
  message: string;
}

export interface LocalLabBuildRequest {
  name: string;
  agent_name?: string | null;
}

export interface LocalLabBuildResponse {
  success: boolean;
  message: string;
  lab_id: string | null;
  slug: string | null;
  agent_id: string | null;
  agent_token: string | null;
  sensor_serial: string | null;
  state: string;
  warnings: string[];
}

export interface LocalLabResources {
  veth?: boolean;
  sensor_running?: boolean;
  agent_running?: boolean;
}

export interface LocalLabItem {
  lab_id: string;
  name: string;
  slug: string;
  state: string;
  status_detail: string | null;
  agent_id: string | null;
  agent_name: string | null;
  agent_status: string | null;
  sensor_serial: string | null;
  gen_if: string;
  mon_if: string;
  stage: string | null;
  percent: number | null;
  resources: LocalLabResources | null;
}

export const localSensorApi = {
  getHostStatus: async (): Promise<LocalHostStatus> => {
    const response = await apiClient.get<LocalHostStatus>('/api/v1/local-sensor/host-status');
    return response.data;
  },

  getLabs: async (): Promise<{ items: LocalLabItem[] }> => {
    const response = await apiClient.get<{ items: LocalLabItem[] }>('/api/v1/local-sensor/labs');
    return response.data;
  },

  getLab: async (labId: string): Promise<LocalLabItem> => {
    const response = await apiClient.get<LocalLabItem>(`/api/v1/local-sensor/${labId}`);
    return response.data;
  },

  build: async (request: LocalLabBuildRequest): Promise<LocalLabBuildResponse> => {
    const response = await apiClient.post<LocalLabBuildResponse>('/api/v1/local-sensor/build', request);
    return response.data;
  },

  teardown: async (labId: string): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post<{ success: boolean; message: string }>(
      `/api/v1/local-sensor/${labId}/teardown`,
    );
    return response.data;
  },
};

export default localSensorApi;
