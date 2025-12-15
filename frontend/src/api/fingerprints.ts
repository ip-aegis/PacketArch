/**
 * Fingerprint API client
 */

import { apiClient } from './client';

// Types for fingerprint API responses
export interface VendorSummary {
  vendor: string;
  display_name: string;
  fingerprint_count: number;
  models: string[];
  oui_prefixes: string[];
}

export interface FingerprintSummary {
  vendor: string;
  vendor_family: string;
  model: string;
  firmware_version: string | null;
  protocols: string[];
}

export interface FingerprintDetail {
  vendor: string;
  vendor_family: string;
  model: string;
  firmware_version: string | null;
  oui_prefixes: string[];
  modbus_identity: Record<string, unknown> | null;
  ethernet_ip_identity: Record<string, unknown> | null;
  profinet_identity: Record<string, unknown> | null;
  tcp_stack: Record<string, unknown> | null;
  response_timing: Record<string, unknown> | null;
  error_behavior: Record<string, unknown> | null;
  protocol_quirks: Record<string, unknown> | null;
  is_builtin: boolean;
}

export interface FingerprintSuggestion {
  device_type: string;
  typical_vendors: string[];
  suggested_fingerprints: FingerprintSummary[];
  default_error_config: {
    exception_rate: number;
    timeout_rate: number;
  } | null;
}

export interface ErrorConfig {
  device_type: string;
  exception_rate: number;
  timeout_rate: number;
  retry_behavior: boolean;
  max_retries: number;
}

// API functions
export async function listVendors(): Promise<VendorSummary[]> {
  const response = await apiClient.get<VendorSummary[]>('/api/v1/fingerprints/vendors');
  return response.data;
}

export async function listFingerprints(vendor?: string): Promise<FingerprintSummary[]> {
  const params = vendor ? { vendor } : undefined;
  const response = await apiClient.get<FingerprintSummary[]>('/api/v1/fingerprints/list', { params });
  return response.data;
}

export async function getFingerprintDetail(vendor: string, model: string): Promise<FingerprintDetail> {
  const response = await apiClient.get<FingerprintDetail>(
    `/api/v1/fingerprints/detail/${encodeURIComponent(vendor)}/${encodeURIComponent(model)}`
  );
  return response.data;
}

export async function suggestFingerprint(deviceType: string, vendor?: string): Promise<FingerprintSuggestion> {
  const params = vendor ? { vendor } : undefined;
  const response = await apiClient.get<FingerprintSuggestion>(
    `/api/v1/fingerprints/suggest/${encodeURIComponent(deviceType)}`,
    { params }
  );
  return response.data;
}

export async function getVendorModels(vendor: string): Promise<string[]> {
  const response = await apiClient.get<string[]>(
    `/api/v1/fingerprints/models/${encodeURIComponent(vendor)}`
  );
  return response.data;
}

export async function getVendorOuis(vendor: string): Promise<string[]> {
  const response = await apiClient.get<string[]>(
    `/api/v1/fingerprints/oui/${encodeURIComponent(vendor)}`
  );
  return response.data;
}

export async function getErrorConfigs(): Promise<ErrorConfig[]> {
  const response = await apiClient.get<ErrorConfig[]>('/api/v1/fingerprints/error-configs');
  return response.data;
}

export async function getDeviceErrorConfig(deviceType: string): Promise<ErrorConfig> {
  const response = await apiClient.get<ErrorConfig>(
    `/api/v1/fingerprints/error-configs/${encodeURIComponent(deviceType)}`
  );
  return response.data;
}
