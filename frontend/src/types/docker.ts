/**
 * Deployment types
 */

export interface NetworkInterface {
  name: string;
  mac_address: string | null;
  ip_addresses: string[];
  is_up: boolean;
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

/**
 * Agent deployment
 */
export interface UnifiedDeployment {
  id: string;
  scenario_id: string;
  scenario_name: string | null;
  agent_id: string | null;
  agent_name: string | null;
  network_interface: string;
  status: string;
  run_mode: RunMode;
  duration_ms: number | null;
  packets_injected: number;
  error_message: string | null;
  started_at: string | null;
  stopped_at: string | null;
  created_at: string;
  // Real-time attack state from agent (null if not available)
  attack: {
    playbook_id: string;
    playbook_name: string;
    is_active: boolean;
    is_paused: boolean;
    is_completed: boolean;
    current_stage: string;
    current_stage_name: string;
    current_stage_color: string;
    current_stage_index: number;
    stage_progress_pct: number;
    stage_remaining_s: number;
    stages_completed: number;
    total_stages: number;
    actions_completed: number;
    attack_packets_generated: number;
  } | null;
}

export interface DeploymentListResponse {
  items: UnifiedDeployment[];
  total: number;
}
