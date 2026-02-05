/**
 * Deployments API functions
 */

import apiClient from './client';
import type {
  Deployment,
  UnifiedDeployment,
  DeploymentRequest,
  DeploymentListResponse,
  DeploymentLogsResponse,
  DeploymentStatus,
  DeploymentType,
} from '../types/docker';

const DEPLOYMENTS_PREFIX = '/api/v1/deployments';

export interface DeploymentFilters {
  scenario_id?: string;
  docker_host_id?: string;
  agent_id?: string;
  status?: DeploymentStatus | string;
  deployment_type?: DeploymentType;
}

export const deploymentsApi = {
  /**
   * List all deployments (Docker and Agent) with optional filters
   */
  async list(filters: DeploymentFilters = {}): Promise<DeploymentListResponse> {
    const params = new URLSearchParams();

    if (filters.scenario_id) params.append('scenario_id', filters.scenario_id);
    if (filters.docker_host_id) params.append('docker_host_id', filters.docker_host_id);
    if (filters.agent_id) params.append('agent_id', filters.agent_id);
    if (filters.status) params.append('status_filter', filters.status);
    if (filters.deployment_type) params.append('deployment_type', filters.deployment_type);

    const url = params.toString()
      ? `${DEPLOYMENTS_PREFIX}?${params.toString()}`
      : DEPLOYMENTS_PREFIX;
    const response = await apiClient.get<DeploymentListResponse>(url);
    return response.data;
  },

  /**
   * Get a single deployment by ID
   */
  async get(id: string): Promise<UnifiedDeployment> {
    const response = await apiClient.get<UnifiedDeployment>(`${DEPLOYMENTS_PREFIX}/${id}`);
    return response.data;
  },

  /**
   * Start a new deployment
   */
  async start(data: DeploymentRequest): Promise<Deployment> {
    const response = await apiClient.post<Deployment>(DEPLOYMENTS_PREFIX, data);
    return response.data;
  },

  /**
   * Stop a running deployment
   */
  async stop(id: string): Promise<Deployment> {
    const response = await apiClient.post<Deployment>(`${DEPLOYMENTS_PREFIX}/${id}/stop`);
    return response.data;
  },

  /**
   * Remove a deployment
   */
  async remove(id: string): Promise<void> {
    await apiClient.delete(`${DEPLOYMENTS_PREFIX}/${id}`);
  },

  /**
   * Get deployment logs
   */
  async getLogs(id: string, tail: number = 100): Promise<DeploymentLogsResponse> {
    const response = await apiClient.get<DeploymentLogsResponse>(
      `${DEPLOYMENTS_PREFIX}/${id}/logs?tail=${tail}`
    );
    return response.data;
  },

  /**
   * List available PCAP files from a deployment
   */
  async listPcapFiles(id: string): Promise<{ deployment_id: string; files: string[]; error?: string }> {
    const response = await apiClient.get<{ deployment_id: string; files: string[]; error?: string }>(
      `${DEPLOYMENTS_PREFIX}/${id}/pcap`
    );
    return response.data;
  },

  /**
   * Get PCAP download URL
   */
  getPcapDownloadUrl(id: string, filename: string): string {
    return `${DEPLOYMENTS_PREFIX}/${id}/pcap/${encodeURIComponent(filename)}`;
  },
};

export default deploymentsApi;
