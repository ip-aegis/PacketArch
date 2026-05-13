/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * AI Scenario Generation API client
 *
 * Used by the AI Scenario Creation Wizard
 */

import apiClient, { getAccessToken } from './client';

export interface AIScenarioGenerateRequest {
  name: string;
  vertical: string;
  description: string;
  vendors?: string[] | null;
  protocols?: string[] | null;
  duration_ms?: number;
  // Device count options
  total_device_count?: number | null;  // AI decides mix, user specifies total
  device_counts?: Record<string, number> | null;  // User specifies per-type counts
  // CVE vulnerability option
  include_vulnerable_devices?: boolean;
  // Default Purdue cell isolation mode for the generated scenario
  cell_isolation_mode?: 'off' | 'conduit_gated' | 'strict_northbound';
}

export interface AIScenarioPreviewDevice {
  device_id: string;
  name: string;
  device_type: string;
  vendor?: string;
  ip_address?: string;
  protocols: string[];
  // CVE vulnerability info
  cve_ids?: string[];
  is_vulnerable?: boolean;
}

export interface AIScenarioPreviewFlow {
  flow_id: string;
  source_device_id: string;
  destination_device_id: string;
  protocol: string;
  description: string;
}

export interface AIScenarioPreviewResponse {
  preview_id: string;
  name: string;
  vertical: string;
  description: string;
  devices: AIScenarioPreviewDevice[];
  flows: AIScenarioPreviewFlow[];
  device_count: number;
  flow_count: number;
  protocols_used: string[];
  vendors_used: string[];
  zones: Array<{ name: string; device_ids: string[] }>;
  // AI enhancement metadata
  ai_enhanced: boolean;
  ai_features: string[];
  design_rationale?: string | null;
  // CVE vulnerability stats
  vulnerable_device_count?: number;
  cve_ids_used?: string[];
}

export interface AIScenarioCreateResponse {
  success: boolean;
  scenario_id: string;
  name: string;
  device_count: number;
  flow_count: number;
}

// ---- Streaming event types ----

export interface ScenarioStreamPhaseEvent {
  type: 'phase';
  step: number;
  total: number;
  message: string;
}

export interface ScenarioStreamDoneEvent {
  type: 'done';
  preview: AIScenarioPreviewResponse;
}

export interface ScenarioStreamErrorEvent {
  type: 'error';
  message: string;
}

export type ScenarioStreamEvent =
  | ScenarioStreamPhaseEvent
  | ScenarioStreamDoneEvent
  | ScenarioStreamErrorEvent;

export interface ScenarioStreamCallbacks {
  onPhase?: (event: ScenarioStreamPhaseEvent) => void;
  onDone?: (event: ScenarioStreamDoneEvent) => void;
  onError?: (event: ScenarioStreamErrorEvent) => void;
}

export const aiScenarioApi = {
  /**
   * Generate a scenario preview from natural language description
   */
  generatePreview: async (
    request: AIScenarioGenerateRequest
  ): Promise<AIScenarioPreviewResponse> => {
    const response = await apiClient.post<AIScenarioPreviewResponse>(
      '/api/v1/ai/scenarios/generate-preview',
      request
    );
    return response.data;
  },

  /**
   * Generate a scenario preview with streaming progress events (SSE).
   * Uses the same Fetch + ReadableStream pattern as ai.ts:sendMessageStream.
   */
  generatePreviewStream: async (
    request: AIScenarioGenerateRequest,
    callbacks: ScenarioStreamCallbacks,
    abortSignal?: AbortSignal,
  ): Promise<void> => {
    const token = getAccessToken();
    const baseUrl = apiClient.defaults.baseURL || '';
    const url = `${baseUrl}/api/v1/ai/scenarios/generate-preview-stream`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
      },
      body: JSON.stringify(request),
      signal: abortSignal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Stream request failed: ${response.status} ${errorText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is not readable');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE events (data: {...}\n\n)
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const eventStr of events) {
          if (!eventStr.trim()) continue;

          const dataMatch = eventStr.match(/^data: (.+)$/m);
          if (!dataMatch) continue;

          try {
            const event = JSON.parse(dataMatch[1]) as ScenarioStreamEvent;

            switch (event.type) {
              case 'phase':
                callbacks.onPhase?.(event);
                break;
              case 'done':
                callbacks.onDone?.(event);
                break;
              case 'error':
                callbacks.onError?.(event);
                break;
            }
          } catch (parseError) {
            console.warn('Failed to parse SSE event:', eventStr, parseError);
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  /**
   * Create an actual scenario from a validated preview
   */
  createFromPreview: async (previewId: string): Promise<AIScenarioCreateResponse> => {
    const response = await apiClient.post<AIScenarioCreateResponse>(
      '/api/v1/ai/scenarios/create-from-preview',
      { preview_id: previewId }
    );
    return response.data;
  },
};

export default aiScenarioApi;
