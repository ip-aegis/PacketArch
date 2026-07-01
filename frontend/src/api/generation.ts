/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * API client for PCAP generation endpoints
 */

import { apiClient } from './client';

const GENERATION_PREFIX = '/api/v1/generation';

export interface GenerationArtifact {
  /** 'combined' (the regular PCAP), 'baseline' (attack removed), or 'attack' (attack only). */
  kind: 'combined' | 'baseline' | 'attack';
  filename: string;
  packets: number;
  size_bytes: number;
}

export interface GenerationJob {
  job_id: string;
  scenario_id: string;
  scenario_name?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  total_duration_ms: number;
  packets_generated: number;
  file_size_bytes: number;
  output_path?: string;
  /** Present for attack-export runs: one entry per PCAP file produced. */
  artifacts?: GenerationArtifact[] | null;
  error_message?: string;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
}

export interface JobListResponse {
  jobs: GenerationJob[];
  total: number;
}

export interface StartGenerationRequest {
  scenario_id: string;
  duration_override_ms?: number;
  output_format?: string;
  filename_prefix?: string;
  /** Optional attack playbook id (e.g. 'havex_like') to bake into the PCAP. */
  attack_playbook_id?: string | null;
  /** Optional attack overrides: intensity, stage_overrides, warmup_ms, start_mode. */
  attack_config?: Record<string, unknown> | null;
  /** Optional AdaptiveConfig dict — enables timing drift and schedules. */
  adaptive_config?: Record<string, unknown> | null;
  /** Optional per-run override for Purdue cell isolation: {mode, applies_to_levels?}. */
  cell_isolation_override?: Record<string, unknown> | null;
  /** When true (with a playbook set), also emit baseline-only + attack-only PCAPs. */
  export_attack_pcap?: boolean;
}

export const generationApi = {
  /**
   * List generation jobs with optional filtering
   */
  async listJobs(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<JobListResponse> {
    const { data } = await apiClient.get<JobListResponse>(GENERATION_PREFIX, { params });
    return data;
  },

  /**
   * Start a new PCAP generation job
   */
  async startGeneration(request: StartGenerationRequest): Promise<GenerationJob> {
    const { data } = await apiClient.post<GenerationJob>(GENERATION_PREFIX, request);
    return data;
  },

  /**
   * Get status of a specific generation job
   */
  async getJobStatus(jobId: string): Promise<GenerationJob> {
    const { data } = await apiClient.get<GenerationJob>(`${GENERATION_PREFIX}/${jobId}`);
    return data;
  },

  /**
   * Cancel a running generation job
   */
  async cancelJob(jobId: string): Promise<void> {
    await apiClient.delete(`${GENERATION_PREFIX}/${jobId}`);
  },

  /**
   * Delete a job record from history
   */
  async deleteJob(jobId: string): Promise<void> {
    await apiClient.delete(`${GENERATION_PREFIX}/${jobId}/delete`);
  },

  /**
   * Get the download URL for a completed PCAP file
   */
  getDownloadUrl(jobId: string): string {
    return `${GENERATION_PREFIX}/${jobId}/download`;
  },

  /**
   * Download a PCAP file (triggers browser download).
   *
   * @param artifact Which file to fetch for attack-export runs:
   *   'combined' (default), 'baseline', or 'attack'.
   */
  async downloadPcap(
    jobId: string,
    filename?: string,
    artifact?: 'combined' | 'baseline' | 'attack',
  ): Promise<void> {
    const response = await apiClient.get(`${GENERATION_PREFIX}/${jobId}/download`, {
      responseType: 'blob',
      params: artifact ? { artifact } : undefined,
    });

    // Create download link
    const blob = new Blob([response.data], { type: 'application/vnd.tcpdump.pcap' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || `pcap_${jobId.substring(0, 8)}.pcap`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },

  /**
   * Get list of supported protocols
   */
  async getSupportedProtocols(): Promise<string[]> {
    const { data } = await apiClient.get<{ protocols: string[] }>(`${GENERATION_PREFIX}/protocols/supported`);
    return data.protocols;
  },
};

export default generationApi;
