/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * AI Usage / Cost API client.
 *
 * Wraps the /api/v1/admin/ai-usage endpoints. All endpoints require
 * admin auth; the apiClient attaches the bearer token automatically.
 */

import apiClient from './client';

const PREFIX = '/api/v1/admin/ai-usage';

export type UsageRange = '24h' | '7d' | '30d' | 'all';

export interface UsageTotals {
  call_count: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_write_tokens: number;
  total_cost_usd: number;
  unpriced_call_count: number;
  error_count: number;
}

export interface GroupedTotals {
  key: string;
  call_count: number;
  input_tokens: number;
  output_tokens: number;
  total_cost_usd: number;
}

export interface UsageSummaryResponse {
  range: UsageRange;
  since: string | null;
  overall: UsageTotals;
  by_provider: GroupedTotals[];
  by_model: GroupedTotals[];
  by_feature: GroupedTotals[];
  by_user: GroupedTotals[];
}

export interface UsageEvent {
  id: string;
  created_at: string;
  user_email: string | null;
  user_id: string | null;
  scenario_id: string | null;
  feature: string;
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_write_tokens: number;
  total_cost_usd: number | null;
  latency_ms: number | null;
  error: string | null;
}

export interface UsageEventsResponse {
  items: UsageEvent[];
  total: number;
}

export interface EventsQuery {
  range?: UsageRange;
  feature?: string;
  provider?: string;
  user_id?: string;
  limit?: number;
  offset?: number;
}

export const aiUsageApi = {
  async summary(range: UsageRange = '7d'): Promise<UsageSummaryResponse> {
    const { data } = await apiClient.get<UsageSummaryResponse>(
      `${PREFIX}/summary`,
      { params: { range } },
    );
    return data;
  },

  async events(query: EventsQuery = {}): Promise<UsageEventsResponse> {
    const { data } = await apiClient.get<UsageEventsResponse>(
      `${PREFIX}/events`,
      { params: query },
    );
    return data;
  },
};
