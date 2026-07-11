/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Multi-sensor topology ("Advanced Deployment") API — provisions one Local
 * Sensor Lab per zone + a core, with L1-aware per-segment traffic injection.
 */

import apiClient from './client';

export interface TopologyPreflight {
  scenario_id: string;
  sensor_count: number;
  ram_estimate_gb: number;
  spans: string[];
  switches: number;
  has_core: boolean;
  flow_plans: number;
}

export interface TopologyIssue {
  code: string;
  message: string;
  subject_id?: string | null;
}

export interface TopologyPreview {
  valid: boolean;
  errors: TopologyIssue[];
  warnings: TopologyIssue[];
  switches: Record<string, Record<string, unknown>>;
  core: Record<string, unknown> | null;
  links: Array<Record<string, unknown>>;
  spans: Array<Record<string, unknown>>;
  flow_plans: Record<string, unknown>;
}

export interface TopologyMember {
  span_id: string;
  role: string;
  lab_id: string;
  slug?: string | null;
  agent_id?: string | null;
  agent_token?: string | null;
  gen_if?: string | null;
  sensor_serial?: string | null;
}

export interface TopologyProvisionResult {
  scenario_id: string;
  sensor_count: number;
  ram_estimate_gb: number;
  members: TopologyMember[];
  span_interface_map: Record<string, string>;
}

export interface TopologyDeployment {
  scenario_id: string;
  sensor_count: number;
  members: Array<Record<string, unknown>>;
  torn_down?: Array<Record<string, unknown>> | null;
}

const base = (id: string) => `/api/v1/scenarios/${id}/topology`;

export const topologyApi = {
  preview: async (scenarioId: string): Promise<TopologyPreview> =>
    (await apiClient.post(`${base(scenarioId)}/preview`)).data,

  preflight: async (scenarioId: string): Promise<TopologyPreflight> =>
    (await apiClient.get(`${base(scenarioId)}/preflight`)).data,

  deploy: async (scenarioId: string): Promise<TopologyProvisionResult> =>
    (await apiClient.post(`${base(scenarioId)}/deploy`)).data,

  deployment: async (scenarioId: string): Promise<TopologyDeployment> =>
    (await apiClient.get(`${base(scenarioId)}/deployment`)).data,

  teardown: async (scenarioId: string): Promise<TopologyDeployment> =>
    (await apiClient.post(`${base(scenarioId)}/teardown`)).data,
};

export default topologyApi;
