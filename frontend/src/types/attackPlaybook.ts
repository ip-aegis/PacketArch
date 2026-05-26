/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
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
  report?: AttackReport;
}

// ───────────────────────── After-action report ─────────────────────

export interface ActionReport {
  action_id: string;
  action_name: string;
  action_type: string;
  mitre_technique: string;
  expected_cv_detection: string;
  description: string;
  /** Epoch seconds when the action first fired. 0 if it never fired. */
  fired_at: number;
  /** Times the action ran (≥1 for repeating actions). 0 if it never fired. */
  fire_count: number;
  packets_emitted: number;
  /** Device IDs the action targeted. */
  targets_hit: string[];
  /** Protocol-specific indicators of compromise (target IPs, ports, etc.). */
  iocs: Record<string, unknown>;
}

export interface StageReport {
  stage_id: string;
  stage_name: string;
  color: string;
  description: string;
  planned_duration_s: number;
  /** Epoch seconds when the stage started. 0 if it never started. */
  started_at: number;
  /** Epoch seconds when the stage completed. null if still in progress. */
  completed_at: number | null;
  actual_duration_s: number;
  actions: ActionReport[];
  packets_emitted: number;
  mitre_tactics: string[];
  expected_cv_alerts: string[];
  status: 'pending' | 'in_progress' | 'completed' | 'skipped';
}

export interface AttackReport {
  playbook_id: string;
  playbook_name: string;
  mitre_software_id: string;
  severity: string;
  category: string;
  /** Epoch seconds when the attack started. */
  started_at: number;
  /** Epoch seconds when the attack ended, or null if still in progress. */
  completed_at: number | null;
  status: 'in_progress' | 'completed' | 'stopped' | 'failed';
  intensity: number;
  auto_advance: boolean;
  attacker_ip: string;
  target_device_count: number;
  stages: StageReport[];
  total_packets: number;
  total_actions: number;
  total_stages: number;
  stages_completed: number;
  techniques_used: string[];
  tactics_covered: string[];
  targets_hit: string[];
}

export interface AttackReportResponse {
  source: 'live' | 'history' | 'none';
  report: AttackReport | null;
}

export interface AttackHistoryResponse {
  count: number;
  history: AttackReport[];
}
