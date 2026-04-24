/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Site configuration overview — aggregated status of every major subsystem,
 * used by the Settings > Overview tab to show what's configured and what
 * still needs attention.
 */

import apiClient from './client';

export type SubsystemStatus = 'ok' | 'needs_attention' | 'disabled' | 'unknown';

export interface ProductSummary {
  name: string;
  version: string;
  owner_name: string;
  owner_email: string;
  license_id: string;
  acknowledgment_document: string;
  acknowledgment_version: string;
  acknowledgments_on_current_version: number;
}

export interface FeaturesSummary {
  ai_enabled: boolean;
}

export interface Subsystem {
  key: string;            // matches the Settings tab key for deep-linking
  label: string;
  status: SubsystemStatus;
  summary: string;
  detail: Record<string, string | number | boolean | null>;
}

export interface SiteConfigResponse {
  generated_at: string;
  product: ProductSummary;
  features: FeaturesSummary;
  subsystems: Subsystem[];
}

const PREFIX = '/api/v1/admin/site-config';

export const siteConfigApi = {
  async get(): Promise<SiteConfigResponse> {
    const response = await apiClient.get<SiteConfigResponse>(PREFIX);
    return response.data;
  },
};

export default siteConfigApi;
