/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Scenario API functions
 */

import { createCrudApi } from './createCrudApi';
import apiClient from './client';
import type { PaginatedResponse, VerticalType } from '../types';

// Scenario types
export interface ReadinessCheck {
  name: string;
  passed: boolean;
  severity: 'error' | 'warning';
  message: string | null;
}

export interface ReadinessSummary {
  score: number;
  status: 'ready' | 'warnings' | 'not_ready';
  error_count: number;
  warning_count: number;
  checks: ReadinessCheck[];
}

export interface ScenarioModes {
  clean_demo_mode: boolean;
  broadcast_traffic_enabled: boolean;
  cell_isolation_mode: 'off' | 'conduit_gated' | 'strict_northbound' | string;
}

export interface ScenarioSummary {
  id: string;
  name: string;
  description: string | null;
  vertical: VerticalType | null;
  total_duration_ms: number;
  device_count: number;
  flow_count: number;
  version: number;
  readiness: ReadinessSummary;
  modes?: ScenarioModes;
  created_at: string;
  updated_at: string;
}

export interface ScenarioDetail extends ScenarioSummary {
  definition: Record<string, unknown>;
  addressing_config: Record<string, unknown> | null;
  user_id?: string;
}

export interface ScenarioCreate {
  name: string;
  description?: string;
  vertical?: VerticalType;
  total_duration_ms?: number;
  definition?: Record<string, unknown>;
  addressing_config?: Record<string, unknown>;
}

export interface ScenarioUpdate extends Partial<ScenarioCreate> {}

export interface ValidationWarning {
  code: string;
  severity: 'warning' | 'error';
  message: string;
  details: string | null;
}

export interface ScenarioValidationResponse {
  scenario_id: string;
  is_valid: boolean;
  warnings: ValidationWarning[];
  device_count: number;
  flow_count: number;
  protocols_used: string[];
}

export interface ScenarioFilters {
  vertical?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

// AI device naming types
export interface RegenerateNamesRequest {
  process_context: string;  // Required: e.g., "candy factory", "dairy processing"
  descriptive_names?: boolean;  // Opt-in demo-friendly labels overlaid on site rail
}

export interface RegenerateNamesResponse {
  scenario_id: string;
  devices_renamed: number;
  message: string;
}

// Protocol repair types
export interface RepairProtocolsResponse {
  scenario_id: string;
  devices_fixed: number;
  protocols_removed: Array<{
    device_id: string;
    device_name: string;
    removed: string[];
    remaining: string[];
  }>;
  message: string;
}

const PREFIX = '/api/v1/scenarios';

export const scenariosApi = {
  ...createCrudApi<ScenarioDetail, ScenarioCreate, ScenarioUpdate>({
    prefix: PREFIX,
  }),

  async list(filters: ScenarioFilters = {}): Promise<PaginatedResponse<ScenarioSummary>> {
    const response = await apiClient.get<PaginatedResponse<ScenarioSummary>>(PREFIX, {
      params: {
        vertical: filters.vertical,
        search: filters.search,
        page: filters.page,
        page_size: filters.page_size,
      },
    });
    return response.data;
  },

  async delete(id: string, force: boolean = false): Promise<void> {
    const params = force ? '?force=true' : '';
    await apiClient.delete(`${PREFIX}/${id}${params}`);
  },

  async duplicate(id: string, newName?: string): Promise<ScenarioDetail> {
    const params = newName ? `?new_name=${encodeURIComponent(newName)}` : '';
    const response = await apiClient.post<ScenarioDetail>(`${PREFIX}/${id}/duplicate${params}`);
    return response.data;
  },

  async export(id: string): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>(`${PREFIX}/${id}/export`);
    return response.data;
  },

  /**
   * Download a print-ready PDF report for a scenario.
   * Triggers a browser download via a temporary anchor — no return value.
   */
  async downloadReport(id: string, name: string): Promise<void> {
    const response = await apiClient.get(`${PREFIX}/${id}/report.pdf`, {
      responseType: 'blob',
    });
    const blob = new Blob([response.data as BlobPart], {
      type: 'application/pdf',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const safe = (name || 'scenario').replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 60);
    a.href = url;
    a.download = `${safe}-${id.slice(0, 8)}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  async import(data: Record<string, unknown>): Promise<ScenarioDetail> {
    const response = await apiClient.post<ScenarioDetail>(`${PREFIX}/import`, data);
    return response.data;
  },

  async importPortable(data: Record<string, unknown>): Promise<ScenarioDetail> {
    const response = await apiClient.post<ScenarioDetail>(
      `${PREFIX}/import/portable`,
      data,
    );
    return response.data;
  },

  async bulkDelete(scenarioIds: string[]): Promise<{ deleted: number; message: string }> {
    const response = await apiClient.post<{ deleted: number; message: string }>(
      `${PREFIX}/bulk-delete`,
      { scenario_ids: scenarioIds }
    );
    return response.data;
  },

  async validate(id: string): Promise<ScenarioValidationResponse> {
    const response = await apiClient.get<ScenarioValidationResponse>(
      `${PREFIX}/${id}/validate`
    );
    return response.data;
  },

  async regenerateDeviceNames(id: string, request: RegenerateNamesRequest): Promise<RegenerateNamesResponse> {
    const response = await apiClient.post<RegenerateNamesResponse>(
      `${PREFIX}/${id}/regenerate-names`,
      request
    );
    return response.data;
  },

  async repairProtocols(id: string): Promise<RepairProtocolsResponse> {
    const response = await apiClient.post<RepairProtocolsResponse>(
      `${PREFIX}/${id}/repair-protocols`
    );
    return response.data;
  },

  async previewCellIsolationStrict(id: string): Promise<CellIsolationPreviewResponse> {
    const response = await apiClient.get<CellIsolationPreviewResponse>(
      `${PREFIX}/${id}/cell-isolation/preview-strict`
    );
    return response.data;
  },

  async applyCellIsolationStrict(id: string): Promise<ApplyStrictResponse> {
    const response = await apiClient.post<ApplyStrictResponse>(
      `${PREFIX}/${id}/cell-isolation/apply-strict`
    );
    return response.data;
  },
};

export interface CellIsolationItem {
  id: string;
  name: string;
  source_zone?: string | null;
  target_zone?: string | null;
  protocol?: string | null;
  allowed_protocols?: string[] | null;
}

export interface CellIsolationPreviewResponse {
  flows: CellIsolationItem[];
  conduits: CellIsolationItem[];
}

export interface ApplyStrictResponse {
  scenario_id: string;
  version_snapshot_id: string | null;
  removed_flow_ids: string[];
  removed_conduit_ids: string[];
  new_flow_count: number;
  new_conduit_count: number;
}

export default scenariosApi;
