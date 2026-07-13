/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import apiClient from './client';

export interface MimicStatus {
  enabled: boolean;
  host_agent_available: boolean;
  message: string;
}

export interface MimicCell {
  cell_slug: string;
  name: string;
  lab_slug: string | null;
  devices: string[];
  state: string;
  message: string;
}

export interface MimicClientBinding {
  protocol: string;
  target_device?: string | null;
  target_ip?: string;
  port: number;
  unit_id: number;
  interval_s: number;
  read_holding: number;
  read_coils: number;
  identity: boolean;
}

export interface MimicPersona {
  device_id: string;
  scenario_id: string;
  name: string;
  template_id: string;
  firmware_version?: string | null;
  process_model_id?: string | null;
  protocols: Record<string, unknown>[];
  clients: MimicClientBinding[];
  step_interval_ms: number;
}

export interface MimicPreset {
  key: string;
  name: string;
  description: string;
  personas: MimicPersona[];
}

export interface DeployCellRequest {
  lab_slug: string;
  cell_name: string;
  personas: MimicPersona[];
}

export interface DeployCellResponse {
  cell_slug: string;
  request_id: string;
  containers: string[];
}

export interface MimicTemplate {
  id: string;
  vendor: string;
  model_name: string;
  device_type: string;
  protocols: string[];
}

export interface AuthorDevice {
  key: string;
  name: string;
  template_id: string;
  protocol: string | null;
  process_model_id: string | null;
}

export interface AuthorRelationship {
  source: string;
  target: string;
}

export interface AuthorCellRequest {
  lab_slug: string;
  cell_name: string;
  devices: AuthorDevice[];
  relationships: AuthorRelationship[];
}

export const mimicApi = {
  getStatus: async (): Promise<MimicStatus> => {
    const response = await apiClient.get<MimicStatus>('/api/v1/mimic/status');
    return response.data;
  },
  getCells: async (): Promise<{ items: MimicCell[] }> => {
    const response = await apiClient.get<{ items: MimicCell[] }>('/api/v1/mimic/cells');
    return response.data;
  },
  getPresets: async (): Promise<{ items: MimicPreset[] }> => {
    const response = await apiClient.get<{ items: MimicPreset[] }>('/api/v1/mimic/presets');
    return response.data;
  },
  getTemplates: async (): Promise<{ items: MimicTemplate[] }> => {
    const response = await apiClient.get<{ items: MimicTemplate[] }>('/api/v1/mimic/templates');
    return response.data;
  },
  getProcessModels: async (): Promise<{ models: string[] }> => {
    const response = await apiClient.get<{ models: string[] }>('/api/v1/mimic/process-models');
    return response.data;
  },
  deploy: async (request: DeployCellRequest): Promise<DeployCellResponse> => {
    const response = await apiClient.post<DeployCellResponse>('/api/v1/mimic/cells', request);
    return response.data;
  },
  author: async (request: AuthorCellRequest): Promise<DeployCellResponse> => {
    const response = await apiClient.post<DeployCellResponse>('/api/v1/mimic/cells/author', request);
    return response.data;
  },
  teardown: async (cellSlug: string): Promise<{ request_id: string }> => {
    const response = await apiClient.delete<{ request_id: string }>(`/api/v1/mimic/cells/${cellSlug}`);
    return response.data;
  },
};

export default mimicApi;
