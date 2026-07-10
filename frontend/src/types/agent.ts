/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Traffic Agent Types
 * WebSocket-based remote traffic generation agents
 */

export interface TrafficAgent {
  id: string;
  name: string;
  description: string | null;
  default_interface: string | null;
  status: 'online' | 'offline';
  version: string | null;
  hostname: string | null;
  platform: string | null;
  is_active: boolean;
  last_seen: string | null;
  first_connected_at: string | null;
  // Agent "kind" linkage — set when provisioned via CML or a local sensor lab.
  cml_lab_id?: string | null;
  cml_node_id?: string | null;
  cml_node_label?: string | null;
  local_lab_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TrafficAgentWithToken extends TrafficAgent {
  token: string;
}

export interface AgentCreate {
  name: string;
  description?: string;
  default_interface?: string;
}

export interface AgentUpdate {
  name?: string;
  description?: string;
  default_interface?: string;
  is_active?: boolean;
}

export interface AgentListResponse {
  agents: TrafficAgent[];
  total: number;
  page: number;
  page_size: number;
  standard_version: string | null;
}

export interface AgentConnectionInfo {
  agent_id: string;
  connected_at: string;
  last_heartbeat: string;
  hostname: string | null;
  platform: string | null;
  version: string | null;
  cpu_percent: number;
  memory_percent: number;
  running_scenarios: string[];
}

export interface AgentInterfaceAddress {
  type: 'ipv4' | 'ipv6';
  address: string;
  netmask: string | null;
}

export interface AgentInterface {
  name: string;
  mac: string | null;
  addresses: AgentInterfaceAddress[];
  error?: string;
}

export interface AgentInterfacesResponse {
  agent_id: string;
  interfaces: AgentInterface[];
}

export interface AgentDeployment {
  id: string;
  agent_id: string;
  scenario_id: string;
  state: 'starting' | 'running' | 'stopping' | 'stopped' | 'error' | 'disconnected';
  interface: string | null;
  packets_sent: number;
  error_message: string | null;
  started_at: string;
  stopped_at: string | null;
}

export interface DeploymentCreate {
  scenario_id: string;
  interface?: string;
  adaptive_config?: Record<string, unknown>;
  attack_playbook?: Record<string, unknown>;
  /** Optional per-run override of Purdue cell isolation: {mode, applies_to_levels?}. */
  cell_isolation_override?: Record<string, unknown>;
  /** Create a Cyber Vision preset + zone groups for this scenario at deploy time. */
  provision_cyber_vision?: boolean;
}

/**
 * Deploy a scenario to a brand-new, dedicated Local Sensor Lab — the sensor
 * is auto-provisioned via the Cyber Vision API and the scenario deploys
 * automatically once the new agent comes online.
 */
export interface DeployNewLabRequest {
  scenario_id: string;
  lab_name: string;
  agent_name?: string | null;
  adaptive_config?: Record<string, unknown>;
  attack_playbook?: Record<string, unknown>;
  cell_isolation_override?: Record<string, unknown>;
  provision_cyber_vision?: boolean;
}

export interface DeployNewLabResponse {
  success: boolean;
  message: string;
  lab_id: string | null;
  slug: string | null;
  agent_id: string | null;
  agent_token: string | null;
  sensor_serial: string | null;
  state: string;
}

/**
 * Status of an in-progress agent update
 */
export interface AgentUpdateStatus {
  agent_id: string;
  status: 'idle' | 'initiated' | 'downloading' | 'loading' | 'restarting' | 'complete' | 'failed' | 'timeout' | 'error';
  progress: number | null;
  message: string;
  target_version: string | null;
  initiated_at: string | null;
  completed_at: string | null;
  error: string | null;
}
