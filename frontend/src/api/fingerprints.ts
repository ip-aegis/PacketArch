/**
 * Fingerprinting Library API client
 */

import { apiClient } from './client';

// ========== Protocol Types ==========

export interface ProtocolInfo {
  id: string;
  name: string;
  category: string;
  port: number | null;
  layer: string;
  has_identity_builder: boolean;
  description: string;
}

export interface ProtocolDetail extends ProtocolInfo {
  identity_fields: string[] | null;
  typical_devices: string[];
  typical_vendors: string[];
}

// ========== Vendor Types ==========

export interface VendorComplete {
  id: string;
  display_name: string;
  oui_prefixes: string[];
  device_types: string[];
  protocols: string[];
  fingerprint_count: number;
}

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

// ========== Stats Types ==========

export interface FingerprintStats {
  total_protocols: number;
  total_vendors: number;
  total_oui_prefixes: number;
  total_fingerprints: number;
  total_device_types: number;
  identity_builders: number;
  protocols_by_category: Record<string, number>;
  // New template-based stats
  total_device_templates: number;
  total_firmware_variants: number;
  total_cves: number;
}

// ========== Device Template Types ==========

export interface FirmwareVariant {
  version: string;
  release_date: string;
  is_latest: boolean;
  is_default: boolean;
  cves: string[];
  notes: string | null;
}

export interface DeviceTemplateSummary {
  id: string;
  vendor: string;
  vendor_family: string;
  model: string;
  model_name: string;
  device_type: string;
  description: string;
  supported_protocols: string[];
  firmware_count: number;
  vulnerable_firmware_count: number;
  has_cves: boolean;
}

export interface DeviceTemplateDetail {
  id: string;
  vendor: string;
  vendor_family: string;
  model: string;
  model_name: string;
  device_type: string;
  description: string;
  oui_prefixes: string[];
  tcp_stack: Record<string, unknown>;
  response_timing: Record<string, unknown>;
  error_behavior: Record<string, unknown>;
  supported_protocols: string[];
  firmware_variants: FirmwareVariant[];
  instance_rules: {
    serial_format: string;
    station_name_pattern: string;
    vendor_short: string;
    model_short: string;
  } | null;
  modbus_identity: Record<string, unknown> | null;
  ethernet_ip_identity: Record<string, unknown> | null;
  profinet_identity: Record<string, unknown> | null;
  s7_identity: Record<string, unknown> | null;
  bacnet_identity: Record<string, unknown> | null;
  snmp_identity: Record<string, unknown> | null;
  protocol_quirks: Record<string, unknown>;
  is_builtin: boolean;
}

export interface GenerateInstanceRequest {
  template_id: string;
  firmware_version?: string;
  station_name?: string;
  serial_number?: string;
  mac_address?: string;
  ip_address?: string;
  location?: string;
  sequence?: number;
}

export interface DeviceInstance {
  template_id: string;
  firmware_version: string;
  serial_number: string;
  station_name: string;
  mac_address: string;
  ip_address: string;
  cves: string[];
  merged_identities: Record<string, Record<string, unknown>>;
}

// ========== API Functions ==========

/**
 * List all supported protocols
 */
export async function listProtocols(category?: string): Promise<ProtocolInfo[]> {
  const response = await apiClient.get<ProtocolInfo[]>('/api/v1/fingerprints/protocols', {
    params: category ? { category } : undefined,
  });
  return response.data;
}

/**
 * Get detailed protocol information
 */
export async function getProtocolDetail(protocolId: string): Promise<ProtocolDetail> {
  const response = await apiClient.get<ProtocolDetail>(
    `/api/v1/fingerprints/protocols/${encodeURIComponent(protocolId)}`
  );
  return response.data;
}

/**
 * List all vendors with complete OUI data
 */
export async function listVendorsComplete(deviceType?: string): Promise<VendorComplete[]> {
  const response = await apiClient.get<VendorComplete[]>('/api/v1/fingerprints/vendors/complete', {
    params: deviceType ? { device_type: deviceType } : undefined,
  });
  return response.data;
}

/**
 * Get fingerprinting library statistics
 */
export async function getStats(): Promise<FingerprintStats> {
  const response = await apiClient.get<FingerprintStats>('/api/v1/fingerprints/stats');
  return response.data;
}

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

// ========== Device Template API Functions ==========

/**
 * List all device templates
 */
export async function listDeviceTemplates(params?: {
  vendor?: string;
  device_type?: string;
  has_cves?: boolean;
}): Promise<DeviceTemplateSummary[]> {
  const response = await apiClient.get<DeviceTemplateSummary[]>(
    '/api/v1/fingerprints/device-templates',
    { params }
  );
  return response.data;
}

/**
 * Get detailed device template information
 */
export async function getDeviceTemplateDetail(templateId: string): Promise<DeviceTemplateDetail> {
  const response = await apiClient.get<DeviceTemplateDetail>(
    `/api/v1/fingerprints/device-templates/${encodeURIComponent(templateId)}`
  );
  return response.data;
}

/**
 * List firmware variants for a device template
 */
export async function listTemplateFirmwares(
  templateId: string,
  vulnerableOnly?: boolean
): Promise<FirmwareVariant[]> {
  const response = await apiClient.get<FirmwareVariant[]>(
    `/api/v1/fingerprints/device-templates/${encodeURIComponent(templateId)}/firmwares`,
    { params: vulnerableOnly ? { vulnerable_only: true } : undefined }
  );
  return response.data;
}

/**
 * Generate a device instance from a template
 */
export async function generateDeviceInstance(
  request: GenerateInstanceRequest
): Promise<DeviceInstance> {
  const response = await apiClient.post<DeviceInstance>(
    '/api/v1/fingerprints/device-templates/instance',
    request
  );
  return response.data;
}

// ========== Utility Functions ==========

/**
 * Protocol category colors
 */
export const protocolCategoryColors: Record<string, string> = {
  'Core Industrial': '#049FD9',     // Cisco blue
  'SCADA/Utility': '#FF7043',       // Orange
  'Power/Energy': '#FBAB18',        // Yellow
  'Building Automation': '#00BCD4', // Cyan
  'Network Management': '#9C27B0',  // Purple
  'Vendor-Specific': '#6CC04A',     // Green
  'DCS Systems': '#E91E63',         // Pink
  'Specialized': '#607D8B',         // Gray
};

/**
 * Get color for protocol category
 */
export function getCategoryColor(category: string): string {
  return protocolCategoryColors[category] || '#8c8c8c';
}

/**
 * Format protocol port for display
 */
export function formatPort(port: number | null, layer: string): string {
  if (port === null) {
    return layer === 'Layer2' ? 'Layer 2' : 'N/A';
  }
  return String(port);
}

/**
 * Vendor category mapping for grouping
 */
export const vendorCategories: Record<string, string[]> = {
  'Industrial Automation': ['siemens', 'rockwell', 'schneider', 'abb', 'emerson', 'honeywell', 'ge', 'omron', 'mitsubishi', 'beckhoff', 'b_and_r', 'phoenix_contact', 'wago'],
  'Building Automation': ['johnson_controls', 'tridium', 'trane', 'carrier', 'delta_controls', 'distech', 'carel', 'automated_logic'],
  'Transportation/ITS': ['econolite', 'mccain', 'wavetronix', 'flir', 'daktronics', 'kapsch', 'qfree', 'axis', 'pelco'],
  'Power/Protection': ['sel', 'basler', 'beckwith'],
  'Network': ['cisco', 'hirschmann', 'moxa', 'advantech'],
  'Sensors/Instrumentation': ['sick', 'turck', 'ifm', 'endress_hauser', 'yokogawa'],
};

/**
 * Get vendor category
 */
export function getVendorCategory(vendorId: string): string {
  for (const [category, vendors] of Object.entries(vendorCategories)) {
    if (vendors.includes(vendorId)) {
      return category;
    }
  }
  return 'Other';
}

// ========== Palette API ==========

export interface PaletteDeviceResponse {
  id: string;
  name: string;
  device_type: string;
  role: string | null;
  description: string | null;
  supported_protocols: string[] | null;
  timing_model: Record<string, unknown> | null;
  vendor_fingerprint: Record<string, string> | null;
  vertical_hints: string[] | null;
  is_builtin: boolean;
  template_id: string | null;
  created_at: string | null;
}

export interface PaletteDeviceListResponse {
  items: PaletteDeviceResponse[];
  total: number;
}

export async function listPaletteDevices(params?: {
  device_type?: string;
  protocol?: string;
  vertical?: string;
  search?: string;
  page_size?: number;
}): Promise<PaletteDeviceListResponse> {
  const response = await apiClient.get<PaletteDeviceListResponse>(
    '/api/v1/fingerprints/palette',
    { params },
  );
  return response.data;
}
