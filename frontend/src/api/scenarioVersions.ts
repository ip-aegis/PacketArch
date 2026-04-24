/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Scenario Versions API client
 */

import apiClient from './client';

export interface VersionSummary {
  id: string;
  version_number: number;
  name: string;
  label: string | null;
  source: string; // "manual" | "auto" | "rollback"
  device_count: number;
  flow_count: number;
  created_at: string;
  created_by: string | null;
}

export interface VersionDetail extends VersionSummary {
  description: string | null;
  definition: Record<string, unknown>;
  addressing_config: Record<string, unknown> | null;
  total_duration_ms: number;
}

export interface VersionListResponse {
  items: VersionSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface DiffEntry {
  category: string;
  change_type: string; // "added" | "removed" | "modified"
  item_id: string | null;
  item_name: string | null;
  details: Record<string, unknown> | null;
}

export interface VersionDiffResponse {
  scenario_id: string;
  base_version: number;
  compare_version: number;
  changes: DiffEntry[];
  summary: Record<string, number>;
}

export interface RollbackResponse {
  scenario_id: string;
  rolled_back_to_version: number;
  new_version_number: number;
  message: string;
}

const prefix = (scenarioId: string) =>
  `/api/v1/scenarios/${scenarioId}/versions`;

export const scenarioVersionsApi = {
  async list(scenarioId: string, page = 1, pageSize = 20): Promise<VersionListResponse> {
    const response = await apiClient.get<VersionListResponse>(
      `${prefix(scenarioId)}`,
      { params: { page, page_size: pageSize } }
    );
    return response.data;
  },

  async create(scenarioId: string, label?: string): Promise<VersionSummary> {
    const response = await apiClient.post<VersionSummary>(
      prefix(scenarioId),
      label ? { label } : {}
    );
    return response.data;
  },

  async get(scenarioId: string, versionId: string): Promise<VersionDetail> {
    const response = await apiClient.get<VersionDetail>(
      `${prefix(scenarioId)}/${versionId}`
    );
    return response.data;
  },

  async updateLabel(
    scenarioId: string,
    versionId: string,
    label: string | null
  ): Promise<VersionSummary> {
    const response = await apiClient.patch<VersionSummary>(
      `${prefix(scenarioId)}/${versionId}`,
      { label }
    );
    return response.data;
  },

  async delete(scenarioId: string, versionId: string): Promise<void> {
    await apiClient.delete(`${prefix(scenarioId)}/${versionId}`);
  },

  async diff(
    scenarioId: string,
    baseVersion: number,
    compareVersion: number
  ): Promise<VersionDiffResponse> {
    const response = await apiClient.get<VersionDiffResponse>(
      `${prefix(scenarioId)}/diff`,
      { params: { base: baseVersion, compare: compareVersion } }
    );
    return response.data;
  },

  async summarizeDiff(
    scenarioId: string,
    baseVersion: number,
    compareVersion: number
  ): Promise<{ summary: string }> {
    const response = await apiClient.post<{ summary: string }>(
      `${prefix(scenarioId)}/diff-summary`,
      null,
      { params: { base: baseVersion, compare: compareVersion } }
    );
    return response.data;
  },

  async rollback(
    scenarioId: string,
    versionNumber: number
  ): Promise<RollbackResponse> {
    const response = await apiClient.post<RollbackResponse>(
      `${prefix(scenarioId)}/rollback`,
      null,
      { params: { version: versionNumber } }
    );
    return response.data;
  },
};
