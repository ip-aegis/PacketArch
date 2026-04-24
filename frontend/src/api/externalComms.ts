/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * External Communications API client
 *
 * Handles C2 beaconing, data exfiltration, exploit attempts,
 * and reconnaissance traffic generation for IDS testing.
 */

import { apiClient } from './client';
import type {
  BeaconPattern,
  ExploitPattern,
  ExternalTemplate,
  ExternalCampaign,
  CreateExternalCampaignRequest,
  ExternalEventType,
} from '../types';

// Response types
export interface ExternalCommTypesResponse {
  beacon_patterns: BeaconPattern[];
  exploit_patterns: ExploitPattern[];
  external_templates: ExternalTemplate[];
}

export interface IPPoolInfo {
  range?: string;
  description: string;
  purpose?: string;
  warning?: string;
}

export interface IPPoolsResponse {
  test_net_1: IPPoolInfo;
  test_net_2: IPPoolInfo;
  test_net_3: IPPoolInfo;
  realistic: IPPoolInfo;
}

export interface CreateExternalCampaignResponse {
  success: boolean;
  campaign_id: string;
  name: string;
  event_count: number;
  event_types: ExternalEventType[];
  internal_devices: string[];
  start_time_ms: number;
  duration_ms: number;
}

// API functions

/**
 * Get available external communication types (beacon patterns, exploits, templates)
 */
export async function getExternalCommTypes(): Promise<ExternalCommTypesResponse> {
  const response = await apiClient.get<ExternalCommTypesResponse>(
    '/api/v1/anomalies/external/types'
  );
  return response.data;
}

/**
 * List external communication templates
 */
export async function listExternalTemplates(options?: {
  target_type?: string;
}): Promise<ExternalTemplate[]> {
  const response = await apiClient.get<ExternalTemplate[]>(
    '/api/v1/anomalies/external/templates',
    { params: options }
  );
  return response.data;
}

/**
 * Get external IP pool information
 */
export async function getIPPools(): Promise<IPPoolsResponse> {
  const response = await apiClient.get<IPPoolsResponse>(
    '/api/v1/anomalies/external/ip-pools'
  );
  return response.data;
}

/**
 * Create an external communication campaign for a scenario
 */
export async function createExternalCampaign(
  scenarioId: string,
  request: CreateExternalCampaignRequest
): Promise<CreateExternalCampaignResponse> {
  const response = await apiClient.post<CreateExternalCampaignResponse>(
    `/api/v1/anomalies/external/campaigns/${encodeURIComponent(scenarioId)}`,
    request
  );
  return response.data;
}

/**
 * List external campaigns for a scenario
 */
export async function listExternalCampaigns(
  scenarioId: string
): Promise<ExternalCampaign[]> {
  const response = await apiClient.get<ExternalCampaign[]>(
    `/api/v1/anomalies/external/campaigns/${encodeURIComponent(scenarioId)}`
  );
  return response.data;
}

/**
 * Delete an external campaign
 */
export async function deleteExternalCampaign(
  scenarioId: string,
  campaignId: string
): Promise<{ success: boolean; deleted: string }> {
  const response = await apiClient.delete<{ success: boolean; deleted: string }>(
    `/api/v1/anomalies/external/campaigns/${encodeURIComponent(scenarioId)}/${encodeURIComponent(campaignId)}`
  );
  return response.data;
}

// Helper functions

/**
 * Get display name for event type
 */
export function getEventTypeDisplayName(eventType: ExternalEventType): string {
  const names: Record<ExternalEventType, string> = {
    c2_beacon: 'C2 Beaconing',
    dns_tunnel: 'DNS Tunneling',
    http_exfil: 'HTTP Exfiltration',
    exploit: 'Exploit Attempt',
    port_scan: 'Port Scan',
  };
  return names[eventType] || eventType;
}

/**
 * Get color for event type
 */
export function getEventTypeColor(eventType: ExternalEventType): string {
  const colors: Record<ExternalEventType, string> = {
    c2_beacon: '#722ed1', // purple
    dns_tunnel: '#13c2c2', // cyan
    http_exfil: '#fa8c16', // orange
    exploit: '#f5222d', // red
    port_scan: '#1890ff', // blue
  };
  return colors[eventType] || '#8c8c8c';
}

/**
 * Get MITRE ATT&CK technique URL
 */
export function getMITREUrl(technique: string): string {
  // ICS techniques start with T0xxx, Enterprise with Txxx
  if (technique.startsWith('T0')) {
    return `https://attack.mitre.org/techniques/${technique}/`;
  }
  return `https://attack.mitre.org/techniques/${technique}/`;
}

/**
 * Format duration for display
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`;
  return `${(ms / 3600000).toFixed(1)}h`;
}
