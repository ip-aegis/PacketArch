/**
 * AI Scenario Generation API client
 *
 * Used by the AI Scenario Creation Wizard
 */

import apiClient from './client';

export interface AIScenarioGenerateRequest {
  name: string;
  vertical: string;
  description: string;
  vendors?: string[] | null;
  protocols?: string[] | null;
  duration_ms?: number;
  // Device count options
  total_device_count?: number | null;  // AI decides mix, user specifies total
  device_counts?: Record<string, number> | null;  // User specifies per-type counts
}

export interface AIScenarioPreviewDevice {
  device_id: string;
  name: string;
  device_type: string;
  vendor?: string;
  ip_address?: string;
  protocols: string[];
}

export interface AIScenarioPreviewFlow {
  flow_id: string;
  source_device_id: string;
  destination_device_id: string;
  protocol: string;
  description: string;
}

export interface AIScenarioPreviewResponse {
  preview_id: string;
  name: string;
  vertical: string;
  description: string;
  devices: AIScenarioPreviewDevice[];
  flows: AIScenarioPreviewFlow[];
  device_count: number;
  flow_count: number;
  protocols_used: string[];
  vendors_used: string[];
  zones: Array<{ name: string; device_ids: string[] }>;
  // AI enhancement metadata
  ai_enhanced: boolean;
  ai_features: string[];
  design_rationale?: string | null;
}

export interface AIScenarioCreateResponse {
  success: boolean;
  scenario_id: string;
  name: string;
  device_count: number;
  flow_count: number;
}

export const aiScenarioApi = {
  /**
   * Generate a scenario preview from natural language description
   */
  generatePreview: async (
    request: AIScenarioGenerateRequest
  ): Promise<AIScenarioPreviewResponse> => {
    const response = await apiClient.post<AIScenarioPreviewResponse>(
      '/api/v1/ai/scenarios/generate-preview',
      request
    );
    return response.data;
  },

  /**
   * Create an actual scenario from a validated preview
   */
  createFromPreview: async (previewId: string): Promise<AIScenarioCreateResponse> => {
    const response = await apiClient.post<AIScenarioCreateResponse>(
      '/api/v1/ai/scenarios/create-from-preview',
      { preview_id: previewId }
    );
    return response.data;
  },
};

export default aiScenarioApi;
