/**
 * CVE Vulnerability API client
 */

import { apiClient } from './client';
import type { CVEVulnerability, VulnerableFingerprintVariant, CVESeverity } from '../types';

// Response types
export interface CVEListResponse {
  cves: CVEVulnerability[];
  count: number;
  vendors: string[];
}

export interface CVEStatsResponse {
  total_cves: number;
  by_severity: Record<string, number>;
  by_vendor: Record<string, number>;
  cyber_vision_detectable: number;
}

export interface VulnerableVariantsResponse {
  variants: VulnerableFingerprintVariant[];
  count: number;
}

// API functions

/**
 * List CVE vulnerabilities with optional filters
 */
export async function listCVEs(options?: {
  vendor?: string;
  severity?: CVESeverity;
  product_family?: string;
  cyber_vision_only?: boolean;
}): Promise<CVEListResponse> {
  // Backend returns array directly, we wrap it to match expected format
  const response = await apiClient.get<CVEVulnerability[]>('/api/v1/cve/list', {
    params: options,
  });
  const cves = response.data;

  // Extract unique vendors from CVE data
  const vendors = [...new Set(cves.map((cve) => cve.vendor))];

  return {
    cves,
    count: cves.length,
    vendors,
  };
}

/**
 * Get details for a specific CVE
 */
export async function getCVEDetail(cveId: string): Promise<CVEVulnerability> {
  const response = await apiClient.get<CVEVulnerability>(
    `/api/v1/cve/detail/${encodeURIComponent(cveId)}`
  );
  return response.data;
}

/**
 * List available vendors with CVEs
 */
export async function listCVEVendors(): Promise<string[]> {
  const response = await apiClient.get<string[]>('/api/v1/cve/vendors');
  return response.data;
}

/**
 * Get critical/high severity CVEs
 */
export async function getCriticalCVEs(): Promise<CVEVulnerability[]> {
  const response = await apiClient.get<CVEVulnerability[]>('/api/v1/cve/critical');
  return response.data;
}

/**
 * Get CVE statistics
 */
export async function getCVEStats(): Promise<CVEStatsResponse> {
  const response = await apiClient.get<CVEStatsResponse>('/api/v1/cve/stats');
  return response.data;
}

/**
 * List vulnerable fingerprint variants
 */
export async function listVulnerableVariants(options?: {
  vendor?: string;
  cve_id?: string;
}): Promise<VulnerableVariantsResponse> {
  // Backend returns array directly, we wrap it to match expected format
  const response = await apiClient.get<VulnerableFingerprintVariant[]>('/api/v1/cve/variants', {
    params: options,
  });
  const variants = response.data;

  return {
    variants,
    count: variants.length,
  };
}

/**
 * Get vulnerable variants for a specific CVE
 */
export async function getVariantsForCVE(cveId: string): Promise<VulnerableFingerprintVariant[]> {
  const response = await apiClient.get<VulnerableVariantsResponse>('/api/v1/cve/variants', {
    params: { cve_id: cveId },
  });
  return response.data.variants;
}

/**
 * Get severity color for display
 */
export function getSeverityColor(severity: CVESeverity): string {
  switch (severity) {
    case 'critical':
      return '#ff4d4f'; // red
    case 'high':
      return '#fa8c16'; // orange
    case 'medium':
      return '#faad14'; // yellow
    case 'low':
      return '#52c41a'; // green
    default:
      return '#8c8c8c'; // gray
  }
}

/**
 * Format CVSS score for display
 */
export function formatCVSSScore(score: number): string {
  return score.toFixed(1);
}
