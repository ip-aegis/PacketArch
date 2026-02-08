/**
 * Templates API client
 */

import apiClient from './client';

export interface Vertical {
  id: string;
  name: string;
  template_count: number;
  templates: string[];
}

export interface TemplateSummary {
  vertical: string;
  name: string;
  display_name: string;
  description: string;
  device_count: number;
  protocols: string[];
}

export interface TemplateDetail {
  name: string;
  description: string;
  vertical: string;
  devices: Array<{
    type: string;
    vendor?: string;
    count: number;
    zone?: string;
    name?: string;
    name_pattern?: string;
    protocols?: string[];
    fingerprint_model?: string;
    role?: string;
    cve_ids?: string[];
  }>;
  flows: Array<{
    protocol: string;
    pattern: string;
    interval_ms: number;
    source_types?: string[];
    target_types?: string[];
    jitter_ms?: number;
    jitter_type?: string;
  }>;
  zones: Array<{
    id: string;
    name: string;
    level: number;
    subnet?: string;
    vlan?: number;
  }>;
  total_duration_ms: number;
}

export interface PhaseTemplate {
  id: string;
  name: string;
  description: string;
  duration_pct: number;
  traffic_multiplier: number;
  color: string;
  behaviors: string[];
}

export interface PhasePreset {
  name: string;
  display_name: string;
  phase_count: number;
  phases: string[];
}

export interface LearnedPatternOptions {
  timing?: boolean;
  fingerprints?: boolean;
  sequences?: boolean;
  function_codes?: boolean;
  address_patterns?: boolean;
}

export interface CreateFromTemplateRequest {
  vertical: string;
  template_name?: string;
  scenario_name: string;
  description?: string;
  phase_preset?: string;
  auto_assign_addresses?: boolean;
  total_duration_ms?: number;
  // Learned pattern options
  apply_learned_patterns?: boolean;
  learned_pattern_options?: LearnedPatternOptions;
  // AI device naming options
  use_ai_naming?: boolean;  // Default false - templates have meaningful built-in names
  process_context?: string; // User description for AI naming (e.g., "candy factory")
}

export interface CreateFromTemplateResponse {
  scenario_id: string;
  name: string;
  device_count: number;
  flow_count: number;
  zone_count: number;
  phase_count: number;
  learned_patterns_applied: boolean;
  protocols_enhanced: string[];
  ai_naming_applied?: boolean;  // True if AI naming was used
}

export const templatesApi = {
  /**
   * List available verticals
   */
  getVerticals: async (): Promise<Vertical[]> => {
    const response = await apiClient.get<Vertical[]>('/api/v1/templates/verticals');
    return response.data;
  },

  /**
   * List available templates
   */
  list: async (vertical?: string): Promise<TemplateSummary[]> => {
    const params = vertical ? { vertical } : {};
    const response = await apiClient.get<TemplateSummary[]>('/api/v1/templates/list', { params });
    return response.data;
  },

  /**
   * Get template details
   */
  getDetail: async (vertical: string, templateName: string): Promise<TemplateDetail> => {
    const response = await apiClient.get<TemplateDetail>(
      `/api/v1/templates/detail/${encodeURIComponent(vertical)}/${encodeURIComponent(templateName)}`
    );
    return response.data;
  },

  /**
   * List phase templates
   */
  getPhaseTemplates: async (): Promise<PhaseTemplate[]> => {
    const response = await apiClient.get<PhaseTemplate[]>('/api/v1/templates/phases');
    return response.data;
  },

  /**
   * List phase presets
   */
  getPhasePresets: async (): Promise<PhasePreset[]> => {
    const response = await apiClient.get<PhasePreset[]>('/api/v1/templates/phases/presets');
    return response.data;
  },

  /**
   * Create scenario from template
   */
  createFromTemplate: async (
    request: CreateFromTemplateRequest
  ): Promise<CreateFromTemplateResponse> => {
    const response = await apiClient.post<CreateFromTemplateResponse>('/api/v1/templates/create', request);
    return response.data;
  },
};

export default templatesApi;
