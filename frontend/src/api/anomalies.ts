/**
 * Anomaly API client
 */

import { apiClient } from './client';

// Types for anomaly API responses
export interface AnomalyTemplate {
  id: string;
  name: string;
  description: string | null;
  category: string;
  severity: string;
  anomaly_type: string;
  target_protocols: string[] | null;
  target_device_types: string[] | null;
  injection_probability: number;
  injection_mode: string;
  parameters: Record<string, unknown> | null;
  tags: string[] | null;
  is_builtin: boolean;
}

export interface AnomalyTemplateList {
  templates: AnomalyTemplate[];
  count: number;
  categories: string[];
}

export interface SuggestedAnomaly {
  template_id: string;
  name: string;
  category: string;
  severity: string;
  relevance_score: number;
  reasons: string[];
}

export interface ScenarioAnomalySuggestion {
  scenario_id: string;
  vertical: string;
  protocols: string[];
  device_types: string[];
  template_suggestions: Record<string, string[]>[];
  suggestions: SuggestedAnomaly[];
}

export interface AnomalyCampaign {
  id: string;
  name: string;
  start_time_ms: number;
  duration_ms: number | null;
  target_flow_ids: string[] | null;
  anomaly_types: string[];
  templates: Array<{
    id: string;
    name: string;
    type: string;
    category: string;
    severity: string;
    parameters: Record<string, unknown> | null;
  }>;
}

export interface CreateCampaignRequest {
  name: string;
  anomaly_types: string[];
  start_time_ms: number;
  duration_ms?: number;
  target_flow_ids?: string[];
}

export interface CreateCampaignResponse {
  success: boolean;
  campaign_id: string;
  name: string;
  anomaly_count: number;
  templates: Array<Record<string, unknown>>;
}

export interface VerticalAnomalies {
  vertical: string;
  template_name: string;
  suggested_anomalies: Record<string, string[]>;
  pcap_learning_hints: Array<{
    protocol: string;
    flow_type: string;
    priority: string;
    description?: string;
  }>;
}

// API functions
export async function listAnomalyTemplates(options?: {
  category?: string;
  severity?: string;
  protocol?: string;
}): Promise<AnomalyTemplateList> {
  const response = await apiClient.get<AnomalyTemplateList>('/api/v1/anomalies/templates', {
    params: options,
  });
  return response.data;
}

export async function getAnomalyTemplate(templateId: string): Promise<AnomalyTemplate> {
  const response = await apiClient.get<AnomalyTemplate>(
    `/api/v1/anomalies/templates/${encodeURIComponent(templateId)}`
  );
  return response.data;
}

export async function suggestAnomalies(
  scenarioId: string,
  maxSuggestions?: number
): Promise<ScenarioAnomalySuggestion> {
  const params = maxSuggestions ? { max_suggestions: maxSuggestions } : undefined;
  const response = await apiClient.get<ScenarioAnomalySuggestion>(
    `/api/v1/anomalies/suggest/${encodeURIComponent(scenarioId)}`,
    { params }
  );
  return response.data;
}

export async function getVerticalAnomalies(
  vertical: string,
  templateName?: string
): Promise<VerticalAnomalies> {
  const params = templateName ? { template_name: templateName } : undefined;
  const response = await apiClient.get<VerticalAnomalies>(
    `/api/v1/anomalies/vertical/${encodeURIComponent(vertical)}`,
    { params }
  );
  return response.data;
}

export async function createCampaign(
  scenarioId: string,
  request: CreateCampaignRequest
): Promise<CreateCampaignResponse> {
  const response = await apiClient.post<CreateCampaignResponse>(
    `/api/v1/anomalies/campaigns/${encodeURIComponent(scenarioId)}`,
    request
  );
  return response.data;
}

export async function listCampaigns(scenarioId: string): Promise<AnomalyCampaign[]> {
  const response = await apiClient.get<AnomalyCampaign[]>(
    `/api/v1/anomalies/campaigns/${encodeURIComponent(scenarioId)}`
  );
  return response.data;
}

export async function deleteCampaign(
  scenarioId: string,
  campaignId: string
): Promise<{ success: boolean; deleted: string }> {
  const response = await apiClient.delete<{ success: boolean; deleted: string }>(
    `/api/v1/anomalies/campaigns/${encodeURIComponent(scenarioId)}/${encodeURIComponent(campaignId)}`
  );
  return response.data;
}
