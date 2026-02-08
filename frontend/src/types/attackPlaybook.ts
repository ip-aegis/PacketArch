/**
 * TypeScript types for the live attack simulation system.
 */

export interface AttackAction {
  action_id: string;
  name: string;
  action_type: string;
  parameters: Record<string, unknown>;
  target_selector: string;
  mitre_technique: string;
  description: string;
  expected_cv_detection: string;
  repeat_count: number;
}

export interface KillChainStage {
  stage_id: string;
  name: string;
  duration_seconds: number;
  actions: AttackAction[];
  color: string;
  description: string;
  expected_cv_alerts: string[];
  mitre_tactics: string[];
}

export interface AttackPlaybook {
  playbook_id: string;
  name: string;
  description: string;
  mitre_software_id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: 'apt' | 'insider' | 'reconnaissance';
  stages: KillChainStage[];
  required_protocols: string[];
  industry_verticals: string[];
  reference_url: string;
  total_duration_seconds: number;
}

export interface AttackPlaybookSummary {
  playbook_id: string;
  name: string;
  description: string;
  severity: string;
  category: string;
  stage_count: number;
  total_duration_seconds: number;
  required_protocols: string[];
  industry_verticals: string[];
  mitre_software_id: string;
}

export interface AttackPlaybookConfig {
  playbook_id: string;
  target_device_ids?: string[];
  stage_overrides?: Record<string, Record<string, unknown>>;
  auto_advance?: boolean;
  start_mode?: 'with_deployment' | 'manual';
  intensity?: number;
}

export interface AttackState {
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
}
