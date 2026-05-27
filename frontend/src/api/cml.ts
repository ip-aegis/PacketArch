/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Cisco Modeling Labs (CML) API functions
 */

import apiClient from './client';

export interface CMLSettings {
  cml_url: string;
  cml_username: string;
  cml_password_set: boolean;
  cml_verify_ssl: boolean;
  cml_packetarch_server_url: string;
}

export interface CMLSettingsUpdate {
  cml_url?: string;
  cml_username?: string;
  cml_password?: string;
  cml_verify_ssl?: boolean;
  cml_packetarch_server_url?: string;
}

export interface CMLConnectionStatus {
  connected: boolean;
  message: string;
  version: string | null;
}

export interface CMLTestConnectionRequest {
  url: string;
  username: string;
  password: string;
  verify_ssl: boolean;
}

export interface CMLTestConnectionResponse {
  success: boolean;
  message: string;
  version: string | null;
}

export interface CMLLab {
  id: string;
  title: string;
  state: string;
  node_count: number;
  owner: string | null;
}

export interface CMLInterface {
  id: string;
  label: string;
  slot: number | null;
  is_connected: boolean;
}

export interface CMLNode {
  id: string;
  label: string;
  node_definition: string;
  state: string;
  is_infrastructure: boolean;
  interfaces: CMLInterface[];
}

export interface CMLDataAttachment {
  target_node_id: string;
  slot: number;
}

export interface CMLDeployRequest {
  lab_id: string;
  agent_name: string;
  data_attachment?: CMLDataAttachment | null;
  start_node?: boolean;
  cpus?: number;
  ram_mb?: number;
}

export interface CMLDeployResponse {
  success: boolean;
  message: string;
  agent_id: string | null;
  agent_token: string | null;
  lab_id: string;
  node_id: string | null;
  node_label: string | null;
  data_wired: boolean;
  mgmt_wired: boolean;
  started: boolean;
  warnings: string[];
}

export interface CMLUndeployRequest {
  agent_id: string;
  remove_cml_node?: boolean;
  deactivate_agent?: boolean;
}

export interface CMLUndeployResponse {
  success: boolean;
  message: string;
  cml_node_removed: boolean;
  agent_deactivated: boolean;
}

export interface CMLLabBuildRequest {
  lab_name: string;
  agent_name: string;
  sensor_compose: string;
  sensor_serial?: string | null;
  start_lab?: boolean;
  agent_cpus?: number;
  agent_ram_mb?: number;
  sensor_cpus?: number;
  sensor_ram_mb?: number;
}

export interface CMLLabBuildResponse {
  success: boolean;
  message: string;
  lab_id: string | null;
  agent_id: string | null;
  agent_token: string | null;
  agent_node_id: string | null;
  switch_node_id: string | null;
  sensor_node_id: string | null;
  sensor_serial: string | null;
  started: boolean;
  warnings: string[];
}

export interface CMLTeardownLabRequest {
  lab_id: string;
  agent_id?: string | null;
}

export interface CMLDeploymentItem {
  agent_id: string;
  agent_name: string;
  status: string;
  is_active: boolean;
  cml_lab_id: string | null;
  cml_node_id: string | null;
  cml_node_label: string | null;
}

export const cmlApi = {
  getSettings: async (): Promise<CMLSettings> => {
    const response = await apiClient.get<CMLSettings>('/api/v1/cml/settings');
    return response.data;
  },

  updateSettings: async (settings: CMLSettingsUpdate): Promise<CMLSettings> => {
    const response = await apiClient.put<CMLSettings>('/api/v1/cml/settings', settings);
    return response.data;
  },

  getStatus: async (): Promise<CMLConnectionStatus> => {
    const response = await apiClient.get<CMLConnectionStatus>('/api/v1/cml/status');
    return response.data;
  },

  testConnection: async (request: CMLTestConnectionRequest): Promise<CMLTestConnectionResponse> => {
    const response = await apiClient.post<CMLTestConnectionResponse>('/api/v1/cml/test-connection', request);
    return response.data;
  },

  getLabs: async (): Promise<{ items: CMLLab[] }> => {
    const response = await apiClient.get<{ items: CMLLab[] }>('/api/v1/cml/labs');
    return response.data;
  },

  getLabNodes: async (labId: string): Promise<{ items: CMLNode[] }> => {
    const response = await apiClient.get<{ items: CMLNode[] }>(`/api/v1/cml/labs/${labId}/nodes`);
    return response.data;
  },

  deploy: async (request: CMLDeployRequest): Promise<CMLDeployResponse> => {
    const response = await apiClient.post<CMLDeployResponse>('/api/v1/cml/deploy', request);
    return response.data;
  },

  undeploy: async (request: CMLUndeployRequest): Promise<CMLUndeployResponse> => {
    const response = await apiClient.post<CMLUndeployResponse>('/api/v1/cml/undeploy', request);
    return response.data;
  },

  getDeployments: async (): Promise<{ items: CMLDeploymentItem[] }> => {
    const response = await apiClient.get<{ items: CMLDeploymentItem[] }>('/api/v1/cml/deployments');
    return response.data;
  },

  buildLab: async (request: CMLLabBuildRequest): Promise<CMLLabBuildResponse> => {
    const response = await apiClient.post<CMLLabBuildResponse>('/api/v1/cml/build-lab', request);
    return response.data;
  },

  teardownLab: async (request: CMLTeardownLabRequest): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post<{ success: boolean; message: string }>('/api/v1/cml/teardown-lab', request);
    return response.data;
  },
};

export default cmlApi;
