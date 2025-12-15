/**
 * Core TypeScript types for PacketArch
 */

// Authentication types
export interface User {
  id: string;
  username: string;
  email: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  last_login: string | null;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

// Settings types
export interface SystemSetting {
  id: string;
  key: string;
  value: string | null;
  is_secret: boolean;
  category: string | null;
  description: string | null;
  updated_at: string;
}

export interface SettingsResponse {
  api_tokens: SystemSetting[];
  network: SystemSetting[];
  system: SystemSetting[];
}

// Device types
export type DeviceType =
  | 'plc'
  | 'hmi'
  | 'rtu'
  | 'drive'
  | 'sensor'
  | 'relay'
  | 'ews'
  | 'historian';

// Protocol types
export type ProtocolType =
  | 'modbus_tcp'
  | 'ethernet_ip'
  | 'profinet'
  | 'opc_ua'
  | 'dnp3'
  | 'iec104'
  | 'bacnet';

// Vertical types
export type VerticalType =
  | 'manufacturing'
  | 'water_wastewater'
  | 'energy_power'
  | 'oil_gas';

// Zone types
export type ZoneType =
  | 'plant_floor'
  | 'dmz'
  | 'corporate'
  | 'remote';

// Network configuration
export interface NetworkConfig {
  macAddress: string;
  ipAddress: string;
  subnetMask: string;
  gateway?: string;
  vlanId?: number;
  hostname?: string;
}

// Timing configuration
export interface TimingConfig {
  intervalMs: number;
  jitterMs: number;
  burstSize?: number;
  burstIntervalMs?: number;
}

// Device in a scenario
export interface ScenarioDevice {
  id: string;
  profileId?: string;
  name: string;
  type: DeviceType;
  role?: string;
  position: { x: number; y: number };
  zoneId?: string;
  network: NetworkConfig;
  protocols: ProtocolType[];
  timing?: TimingConfig;
  vendor?: string;
  fingerprintModel?: string;
  // CVE vulnerability simulation
  vulnerableCve?: string;
  vulnerabilityOverride?: {
    modbus_identity_override?: Record<string, unknown>;
    ethernet_ip_identity_override?: Record<string, unknown>;
    profinet_identity_override?: Record<string, unknown>;
    s7_identity_override?: Record<string, unknown>;
  };
}

// Flow between devices
export interface ScenarioFlow {
  id: string;
  name: string;
  sourceDeviceId: string;
  targetDeviceId: string;
  protocol: ProtocolType;
  protocolConfig: Record<string, unknown>;
  timing: TimingConfig;
  phases: {
    startup: boolean;
    steadyState: boolean;
    maintenance: boolean;
    shutdown: boolean;
  };
}

// Zone/group in a scenario
export interface ScenarioZone {
  id: string;
  name: string;
  type: 'vertical' | 'network' | 'vlan' | 'logical';
  position: { x: number; y: number };
  dimensions: { width: number; height: number };
  color?: string;
  network?: {
    subnet: string;
    vlanId?: number;
    gateway?: string;
  };
  deviceIds: string[];
}

// Phase definition
export interface Phase {
  id: string;
  name: 'startup' | 'steady-state' | 'maintenance' | 'shutdown' | 'custom';
  displayName: string;
  startOffsetMs: number;
  durationMs: number;
  intensity: number;
  color: string;
}

// Full scenario definition
export interface Scenario {
  id: string;
  name: string;
  description?: string;
  vertical?: VerticalType;
  totalDurationMs: number;
  devices: Record<string, ScenarioDevice>;
  flows: Record<string, ScenarioFlow>;
  zones: Record<string, ScenarioZone>;
  phases: Phase[];
  createdAt: string;
  updatedAt: string;
}

// API response types
export interface MessageResponse {
  message: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// Device Profile types (library templates)
export interface TimingModel {
  polling_interval_ms: number;
  jitter_min_ms: number;
  jitter_max_ms: number;
  jitter_type: 'uniform' | 'gaussian' | 'exponential';
  burst_enabled: boolean;
  burst_size?: number;
  burst_interval_ms?: number;
}

export interface VendorFingerprint {
  vendor_family: string;
  oui_prefix: string;
  oui_variants?: string[];
  response_time_min_ms: number;
  response_time_max_ms: number;
  firmware_patterns?: string[];
}

export interface PayloadTemplate {
  name: string;
  protocol: ProtocolType;
  function_code?: number;
  data_type?: string;
  start_address?: number;
  quantity?: number;
  description?: string;
}

export interface DeviceProfile {
  id: string;
  name: string;
  device_type: DeviceType | string;
  role: string | null;
  description: string | null;
  supported_protocols: ProtocolType[] | null;
  timing_model: TimingModel | null;
  payload_templates: PayloadTemplate[] | null;
  behavior_model: Record<string, unknown> | null;
  vendor_fingerprint: VendorFingerprint | null;
  vertical_hints: VerticalType[] | null;
  is_builtin: boolean;
  created_at: string;
}

export interface DeviceProfileCreate {
  name: string;
  device_type: string;
  role?: string;
  description?: string;
  supported_protocols?: ProtocolType[];
  timing_model?: TimingModel;
  payload_templates?: PayloadTemplate[];
  behavior_model?: Record<string, unknown>;
  vendor_fingerprint?: VendorFingerprint;
  vertical_hints?: VerticalType[];
}

export interface DeviceProfileUpdate extends Partial<DeviceProfileCreate> {}

// Protocol Template types
export interface ProtocolTemplate {
  id: string;
  protocol: ProtocolType | string;
  name: string;
  vertical: VerticalType | null;
  config_schema: Record<string, unknown> | null;
  default_config: Record<string, unknown> | null;
  is_builtin: boolean;
  created_at: string;
}

// CVE Vulnerability types
export type CVESeverity = 'critical' | 'high' | 'medium' | 'low';

export interface CVEVulnerability {
  id: string;
  cve_id: string;
  title: string;
  description: string;
  severity: CVESeverity;
  cvss_score: number;
  vendor: string;
  product_family: string;
  affected_models: string[];
  affected_firmware_min: string | null;
  affected_firmware_max: string;
  fixed_firmware_version: string | null;
  cyber_vision_detectable: boolean;
  advisory_url: string | null;
  is_builtin: boolean;
}

export interface VulnerableFingerprintVariant {
  id: string;
  cve_vulnerability_id: string;
  cve_id: string;
  firmware_version: string;
  display_name: string;
  modbus_identity_override: Record<string, unknown> | null;
  ethernet_ip_identity_override: Record<string, unknown> | null;
  profinet_identity_override: Record<string, unknown> | null;
  s7_identity_override: Record<string, unknown> | null;
  is_builtin: boolean;
}

// External Communication types
export type ExternalEventType = 'c2_beacon' | 'dns_tunnel' | 'http_exfil' | 'exploit' | 'port_scan';

export interface BeaconPattern {
  name: string;
  display_name: string;
  description: string;
  pattern_type: string;
  base_interval_ms: number;
  mitre_technique: string;
}

export interface ExploitPattern {
  name: string;
  display_name: string;
  description: string;
  target_protocol: string;
  target_port: number;
  mitre_technique: string;
  cve_reference: string | null;
}

export interface ExternalTemplate {
  id: string;
  name: string;
  description: string | null;
  anomaly_type: string;
  severity: string;
  external_target_type: string | null;
  external_protocol: string | null;
  external_port: number | null;
  external_ip_pool: string | null;
  mitre_technique: string | null;
  ids_trigger_patterns: string[] | null;
}

export interface ExternalCampaign {
  campaign_id: string;
  name: string;
  event_count: number;
  event_types: ExternalEventType[];
  internal_devices: string[];
  start_time_ms: number;
  duration_ms: number;
}

export interface CreateExternalCampaignRequest {
  name: string;
  internal_device_ips: string[];
  event_types: ExternalEventType[];
  start_time_ms?: number;
  duration_ms?: number;
  use_realistic_ips?: boolean;
  c2_pattern?: string;
  c2_protocol?: string;
  beacon_count?: number;
  exfil_data_size?: number;
  exploit_pattern?: string;
  scan_type?: string;
  scan_ot_ports?: boolean;
}
