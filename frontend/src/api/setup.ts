/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * First-run setup wizard API client. Three endpoints under /api/v1/setup,
 * all reachable without authentication while the wizard is open. After the
 * wizard completes, /complete and /test-ai-key return 410 Gone.
 */

import apiClient from './client';

export interface SetupStatus {
  setup_complete: boolean;
  build_variant: 'full' | 'pcap-only';
  ai_supported: boolean;
  live_traffic_supported: boolean;
}

export interface AdminAccountInput {
  username: string;
  password: string;
  email?: string | null;
}

export interface SiteIdentityInput {
  name: string;
  fqdn: string;
  timezone: string;
}

export interface AICapabilityInput {
  enabled: boolean;
  anthropic_api_key?: string | null;
}

export interface CyberVisionCapabilityInput {
  enabled: boolean;
  url?: string | null;
  api_token?: string | null;
  verify_ssl: boolean;
}

export interface SetupCompleteRequest {
  admin: AdminAccountInput;
  site: SiteIdentityInput;
  ai: AICapabilityInput;
  cyber_vision: CyberVisionCapabilityInput;
  accept_acknowledgment: boolean;
}

export interface SetupCompleteResponse {
  setup_complete: boolean;
  access_token: string;
  refresh_token: string;
}

export interface TestAIKeyResponse {
  valid: boolean;
  error: string | null;
}

const PREFIX = '/api/v1/setup';

export const setupApi = {
  async getStatus(): Promise<SetupStatus> {
    const { data } = await apiClient.get<SetupStatus>(`${PREFIX}/status`);
    return data;
  },

  async complete(payload: SetupCompleteRequest): Promise<SetupCompleteResponse> {
    const { data } = await apiClient.post<SetupCompleteResponse>(
      `${PREFIX}/complete`,
      payload,
    );
    return data;
  },

  async testAIKey(anthropicApiKey: string): Promise<TestAIKeyResponse> {
    const { data } = await apiClient.post<TestAIKeyResponse>(
      `${PREFIX}/test-ai-key`,
      { anthropic_api_key: anthropicApiKey },
    );
    return data;
  },
};

export default setupApi;
