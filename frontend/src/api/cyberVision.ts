/**
 * Cyber Vision API functions
 */

import apiClient from './client';

// CV Device type
export interface CVDevice {
  id: string;
  name: string;
  ip: string | null;
  mac: string | null;
  vendor: string | null;
  model: string | null;
  firmware: string | null;
  category: string | null;
  risk_score: number | null;
  first_seen: string | null;
  last_seen: string | null;
  group_name: string | null;
}

// CV Vulnerability type
export interface CVVulnerability {
  id: string;
  cve_id: string;
  title: string;
  severity: string;
  cvss_score: number | null;
  affected_device_count: number;
  description: string | null;
}

// CV Connection status
export interface CVConnectionStatus {
  connected: boolean;
  message: string;
  version: string | null;
  center_name: string | null;
}

// CV Test connection request
export interface CVTestConnectionRequest {
  url: string;
  api_token: string;
  verify_ssl: boolean;
}

// CV Test connection response
export interface CVTestConnectionResponse {
  success: boolean;
  message: string;
  version: string | null;
}

// CV Settings
export interface CVSettings {
  cyber_vision_url: string;
  cyber_vision_api_token_set: boolean;
  cyber_vision_verify_ssl: boolean;
}

// CV Settings update
export interface CVSettingsUpdate {
  cyber_vision_url?: string;
  cyber_vision_api_token?: string;
  cyber_vision_verify_ssl?: boolean;
}

// Matched device in comparison
export interface MatchedDevice {
  scenario_device: Record<string, unknown>;
  cv_device: CVDevice;
  confidence: number;
  match_type: string;
}

// Comparison insight
export interface ComparisonInsight {
  category: string;
  severity: string;
  message: string;
  affected_devices: string[];
}

// Comparison result
export interface CVComparisonResult {
  scenario_id: string;
  scenario_name: string;
  scenario_device_count: number;
  cv_device_count: number;
  matched_devices: MatchedDevice[];
  scenario_only: Record<string, unknown>[];
  cv_only: CVDevice[];
  match_rate: number;
  insights: ComparisonInsight[];
}

// List response types
export interface CVDeviceListResponse {
  items: CVDevice[];
  total: number;
}

export interface CVVulnerabilityListResponse {
  items: CVVulnerability[];
  total: number;
}

// CV Preset
export interface CVPreset {
  id: string;
  label: string;
}

export interface CVPresetListResponse {
  items: CVPreset[];
}

// Enrichment types
export interface CVDevicePropertyMapping {
  cv_device_id: string;
  cv_device_mac?: string;
  cv_device_ip?: string;
  device_label?: string;  // Set the device name/label in CV
  properties: Record<string, string>;
}

export interface CVEnrichmentRequest {
  device_mappings: CVDevicePropertyMapping[];
  skip_existing?: boolean;
}

export interface CVEnrichmentDeviceResult {
  cv_device_id: string;
  status: 'success' | 'failed';
  properties_added: string[];
  error?: string;
}

export interface CVEnrichmentResult {
  success_count: number;
  failed_count: number;
  total_properties_added: number;
  results: CVEnrichmentDeviceResult[];
}

// Cyber Vision API
export const cyberVisionApi = {
  // Get CV settings
  getSettings: async (): Promise<CVSettings> => {
    const response = await apiClient.get<CVSettings>('/api/v1/cyber-vision/settings');
    return response.data;
  },

  // Update CV settings
  updateSettings: async (settings: CVSettingsUpdate): Promise<CVSettings> => {
    const response = await apiClient.put<CVSettings>('/api/v1/cyber-vision/settings', settings);
    return response.data;
  },

  // Get connection status
  getStatus: async (): Promise<CVConnectionStatus> => {
    const response = await apiClient.get<CVConnectionStatus>('/api/v1/cyber-vision/status');
    return response.data;
  },

  // Test connection with provided credentials
  testConnection: async (request: CVTestConnectionRequest): Promise<CVTestConnectionResponse> => {
    const response = await apiClient.post<CVTestConnectionResponse>(
      '/api/v1/cyber-vision/test-connection',
      request
    );
    return response.data;
  },

  // Get CV devices
  getDevices: async (params?: {
    limit?: number;
    offset?: number;
    search?: string;
  }): Promise<CVDeviceListResponse> => {
    const response = await apiClient.get<CVDeviceListResponse>('/api/v1/cyber-vision/devices', {
      params,
    });
    return response.data;
  },

  // Get single CV device
  getDevice: async (deviceId: string): Promise<CVDevice> => {
    const response = await apiClient.get<CVDevice>(`/api/v1/cyber-vision/devices/${deviceId}`);
    return response.data;
  },

  // Get CV vulnerabilities
  getVulnerabilities: async (params?: {
    limit?: number;
    offset?: number;
    severity?: string;
  }): Promise<CVVulnerabilityListResponse> => {
    const response = await apiClient.get<CVVulnerabilityListResponse>(
      '/api/v1/cyber-vision/vulnerabilities',
      { params }
    );
    return response.data;
  },

  // Get CV presets
  getPresets: async (): Promise<CVPresetListResponse> => {
    const response = await apiClient.get<CVPresetListResponse>('/api/v1/cyber-vision/presets');
    return response.data;
  },

  // Compare scenario with CV devices
  compareScenario: async (scenarioId: string, presetId?: string): Promise<CVComparisonResult> => {
    const params = presetId ? { preset_id: presetId } : undefined;
    const response = await apiClient.post<CVComparisonResult>(
      `/api/v1/cyber-vision/compare/${scenarioId}`,
      null,
      { params }
    );
    return response.data;
  },

  // Enrich CV devices with PacketArch data
  enrichDevices: async (request: CVEnrichmentRequest): Promise<CVEnrichmentResult> => {
    const response = await apiClient.post<CVEnrichmentResult>(
      '/api/v1/cyber-vision/enrich',
      request
    );
    return response.data;
  },
};

export default cyberVisionApi;
