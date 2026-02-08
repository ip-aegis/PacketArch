/**
 * Scenario API functions
 */

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

export interface ScenarioSummary {
  id: string;
  name: string;
  description: string | null;
  vertical: VerticalType | null;
  total_duration_ms: number;
  device_count: number;
  flow_count: number;
  zone_count: number;
  version: number;
  has_learned_patterns: boolean;
  protocols_enhanced: string[];
  readiness: ReadinessSummary;
  created_at: string;
  updated_at: string;
}

export interface ScenarioDetail extends ScenarioSummary {
  definition: Record<string, unknown>;
  addressing_config: Record<string, unknown> | null;
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

// Pattern integration types
export interface DevicePatternSuggestion {
  device_id: string;
  device_name: string;
  device_type: string;
  protocol: string;
  suggestions: {
    protocol_patterns: Array<{
      id: string;
      sample_count: number;
      confidence: number;
      has_function_codes: boolean;
      has_address_patterns: boolean;
      has_timing: boolean;
    }>;
    fingerprints: Array<{
      id: string;
      ip_address: string;
      vendor: string | null;
      role: string;
      has_tcp_signature: boolean;
      has_response_timings: boolean;
      confidence: number;
    }>;
    sequences: Array<{
      id: string;
      name: string;
      sequence_type: string;
      step_count: number;
      confidence: number;
    }>;
  };
}

export interface ScenarioPatternSuggestionsResponse {
  scenario_id: string;
  scenario_name: string;
  device_suggestions: DevicePatternSuggestion[];
  total_patterns_available: number;
}

export interface ApplyPatternsRequest {
  device_pattern_mappings: Array<{
    device_id: string;
    fingerprint_id?: string;
    pattern_id?: string;
    sequence_ids?: string[];
  }>;
  apply_timing?: boolean;
  apply_fingerprints?: boolean;
  apply_sequences?: boolean;
}

export interface ApplyPatternsResponse {
  scenario_id: string;
  devices_updated: number;
  patterns_applied: number;
  message: string;
}

// AI device naming types
export interface RegenerateNamesRequest {
  process_context: string;  // Required: e.g., "candy factory", "dairy processing"
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

const SCENARIOS_PREFIX = '/api/v1/scenarios';

export const scenariosApi = {
  /**
   * List scenarios with optional filters
   */
  async list(filters: ScenarioFilters = {}): Promise<PaginatedResponse<ScenarioSummary>> {
    const params = new URLSearchParams();

    if (filters.vertical) params.append('vertical', filters.vertical);
    if (filters.search) params.append('search', filters.search);
    if (filters.page) params.append('page', String(filters.page));
    if (filters.page_size) params.append('page_size', String(filters.page_size));

    const response = await apiClient.get<PaginatedResponse<ScenarioSummary>>(
      `${SCENARIOS_PREFIX}?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Get a single scenario by ID
   */
  async get(id: string): Promise<ScenarioDetail> {
    const response = await apiClient.get<ScenarioDetail>(`${SCENARIOS_PREFIX}/${id}`);
    return response.data;
  },

  /**
   * Create a new scenario
   */
  async create(data: ScenarioCreate): Promise<ScenarioDetail> {
    const response = await apiClient.post<ScenarioDetail>(SCENARIOS_PREFIX, data);
    return response.data;
  },

  /**
   * Update an existing scenario
   */
  async update(id: string, data: ScenarioUpdate): Promise<ScenarioDetail> {
    const response = await apiClient.patch<ScenarioDetail>(`${SCENARIOS_PREFIX}/${id}`, data);
    return response.data;
  },

  /**
   * Delete a scenario
   * @param id - Scenario ID
   * @param force - If true, force delete even if there are active deployments or generation jobs
   */
  async delete(id: string, force: boolean = false): Promise<void> {
    const params = force ? '?force=true' : '';
    await apiClient.delete(`${SCENARIOS_PREFIX}/${id}${params}`);
  },

  /**
   * Duplicate a scenario
   */
  async duplicate(id: string, newName?: string): Promise<ScenarioDetail> {
    const params = newName ? `?new_name=${encodeURIComponent(newName)}` : '';
    const response = await apiClient.post<ScenarioDetail>(`${SCENARIOS_PREFIX}/${id}/duplicate${params}`);
    return response.data;
  },

  /**
   * Export a scenario as JSON
   */
  async export(id: string): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>(`${SCENARIOS_PREFIX}/${id}/export`);
    return response.data;
  },

  /**
   * Import a scenario from JSON
   */
  async import(data: Record<string, unknown>): Promise<ScenarioDetail> {
    const response = await apiClient.post<ScenarioDetail>(`${SCENARIOS_PREFIX}/import`, data);
    return response.data;
  },

  /**
   * Bulk delete multiple scenarios
   */
  async bulkDelete(scenarioIds: string[]): Promise<{ deleted: number; message: string }> {
    const response = await apiClient.post<{ deleted: number; message: string }>(
      `${SCENARIOS_PREFIX}/bulk-delete`,
      { scenario_ids: scenarioIds }
    );
    return response.data;
  },

  /**
   * Validate a scenario before deployment
   */
  async validate(id: string): Promise<ScenarioValidationResponse> {
    const response = await apiClient.get<ScenarioValidationResponse>(
      `${SCENARIOS_PREFIX}/${id}/validate`
    );
    return response.data;
  },

  /**
   * Get pattern suggestions for all devices in a scenario
   */
  async getPatternSuggestions(id: string): Promise<ScenarioPatternSuggestionsResponse> {
    const response = await apiClient.get<ScenarioPatternSuggestionsResponse>(
      `${SCENARIOS_PREFIX}/${id}/pattern-suggestions`
    );
    return response.data;
  },

  /**
   * Apply learned patterns to devices in a scenario
   */
  async applyPatterns(id: string, request: ApplyPatternsRequest): Promise<ApplyPatternsResponse> {
    const response = await apiClient.post<ApplyPatternsResponse>(
      `${SCENARIOS_PREFIX}/${id}/apply-patterns`,
      request
    );
    return response.data;
  },

  /**
   * Regenerate device names using AI with user-provided process context
   */
  async regenerateDeviceNames(id: string, request: RegenerateNamesRequest): Promise<RegenerateNamesResponse> {
    const response = await apiClient.post<RegenerateNamesResponse>(
      `${SCENARIOS_PREFIX}/${id}/regenerate-names`,
      request
    );
    return response.data;
  },

  /**
   * Repair protocol assignments by removing protocols without fingerprint support.
   * This fixes protocol_identity_mismatch validation errors.
   */
  async repairProtocols(id: string): Promise<RepairProtocolsResponse> {
    const response = await apiClient.post<RepairProtocolsResponse>(
      `${SCENARIOS_PREFIX}/${id}/repair-protocols`
    );
    return response.data;
  },
};

export default scenariosApi;
