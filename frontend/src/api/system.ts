/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * System self-upgrade API (admin-only). Mirrors the agent update flow:
 * trigger an upgrade, then poll status — which survives the backend's own
 * restart because it's written to a shared volume by the updater container.
 */

import apiClient from './client';

export interface SystemVersion {
  current: string;
  latest: string | null;
  update_available: boolean;
  checked: boolean; // false when the release source (GitHub) was unreachable
}

export interface UpgradeStatus {
  schema?: number;
  upgrade_id?: string;
  from_version?: string;
  to_version?: string;
  // queued|preflight|backup|checkout|building|migrating|starting|verifying|
  // success|rolling_back|rolled_back|failed|idle
  phase: string;
  status: string; // running|success|failed|rolled_back|idle
  message: string;
  started_at?: string;
  updated_at?: string;
  finished_at?: string | null;
  backup_file?: string | null;
  error?: string | null;
}

const PREFIX = '/api/v1/system';

export const systemApi = {
  async getVersion(): Promise<SystemVersion> {
    const response = await apiClient.get<SystemVersion>(`${PREFIX}/version`);
    return response.data;
  },

  async triggerUpgrade(target?: string): Promise<UpgradeStatus> {
    const response = await apiClient.post<UpgradeStatus>(`${PREFIX}/upgrade`, {
      target: target ?? null,
    });
    return response.data;
  },

  async getUpgradeStatus(): Promise<UpgradeStatus> {
    const response = await apiClient.get<UpgradeStatus>(`${PREFIX}/upgrade-status`);
    return response.data;
  },

  async clearUpgradeStatus(): Promise<void> {
    await apiClient.delete(`${PREFIX}/upgrade-status`);
  },
};

export default systemApi;
