/**
 * Docker host and deployment types
 */

// Docker Host types
export interface DockerHost {
  id: string;
  name: string;
  description: string | null;
  docker_api_url: string;
  tls_enabled: boolean;
  has_certificates: boolean;
  default_interface: string | null;
  is_active: boolean;
  last_connected_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DockerHostCreate {
  name: string;
  description?: string;
  docker_api_url: string;
  tls_enabled?: boolean;
  ca_cert?: string;
  client_cert?: string;
  client_key?: string;
  default_interface?: string;
  is_active?: boolean;
}

export interface DockerHostUpdate {
  name?: string;
  description?: string;
  docker_api_url?: string;
  tls_enabled?: boolean;
  ca_cert?: string;
  client_cert?: string;
  client_key?: string;
  default_interface?: string;
  is_active?: boolean;
}

export interface DockerHostListResponse {
  items: DockerHost[];
  total: number;
}

export interface DockerHostTestResult {
  success: boolean;
  message: string;
  docker_version: string | null;
  api_version: string | null;
  latency_ms: number | null;
}

export interface NetworkInterface {
  name: string;
  mac_address: string | null;
  ip_addresses: string[];
  is_up: boolean;
}

export interface DockerHostInterfaceList {
  host_id: string;
  host_name: string;
  interfaces: NetworkInterface[];
}

// Deployment types
export type DeploymentStatus =
  | 'pending'
  | 'starting'
  | 'running'
  | 'stopping'
  | 'stopped'
  | 'failed';

export type RunMode = 'timed' | 'perpetual';

export type DeploymentType = 'docker' | 'agent';

export interface Deployment {
  id: string;
  scenario_id: string;
  scenario_name: string | null;
  docker_host_id: string;
  docker_host_name: string | null;
  container_id: string | null;
  container_name: string | null;
  network_interface: string;
  status: DeploymentStatus;
  run_mode: RunMode;
  duration_ms: number | null;
  packets_injected: number;
  error_message: string | null;
  started_at: string | null;
  stopped_at: string | null;
  created_at: string;
}

/**
 * Unified deployment that can represent both Docker and Agent deployments
 */
export interface UnifiedDeployment {
  id: string;
  deployment_type: DeploymentType;
  scenario_id: string;
  scenario_name: string | null;
  // Docker-specific fields (null for agent deployments)
  docker_host_id: string | null;
  docker_host_name: string | null;
  container_id: string | null;
  container_name: string | null;
  // Agent-specific fields (null for docker deployments)
  agent_id: string | null;
  agent_name: string | null;
  // Common fields
  network_interface: string;
  status: string;  // Can be DeploymentStatus or agent state
  run_mode: RunMode;
  duration_ms: number | null;
  packets_injected: number;
  error_message: string | null;
  started_at: string | null;
  stopped_at: string | null;
  created_at: string;
}

export interface DeploymentRequest {
  scenario_id: string;
  docker_host_id: string;
  network_interface: string;
  run_mode: RunMode;
  duration_ms?: number;  // Optional for perpetual mode
}

export interface DeploymentListResponse {
  items: UnifiedDeployment[];
  total: number;
}

export interface DeploymentLogsResponse {
  deployment_id: string;
  container_id: string | null;
  logs: string;
  timestamp: string;
}
