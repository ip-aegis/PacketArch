/**
 * Deployments API functions
 */

import { createCrudApi } from './createCrudApi';
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

const PREFIX = '/api/v1/deployments';

export interface DeploymentFilters {
  scenario_id?: string;
  docker_host_id?: string;
  agent_id?: string;
  status?: DeploymentStatus | string;
  deployment_type?: DeploymentType;
}

const crud = createCrudApi<UnifiedDeployment>({ prefix: PREFIX });

export const deploymentsApi = {
  get: crud.get,
  remove: crud.delete,

  async list(filters: DeploymentFilters = {}): Promise<DeploymentListResponse> {
    const response = await apiClient.get<DeploymentListResponse>(PREFIX, {
      params: {
        scenario_id: filters.scenario_id,
        docker_host_id: filters.docker_host_id,
        agent_id: filters.agent_id,
        status_filter: filters.status,
        deployment_type: filters.deployment_type,
      },
    });
    return response.data;
  },

  async start(data: DeploymentRequest): Promise<Deployment> {
    const response = await apiClient.post<Deployment>(PREFIX, data);
    return response.data;
  },

  async stop(id: string): Promise<Deployment> {
    const response = await apiClient.post<Deployment>(`${PREFIX}/${id}/stop`);
    return response.data;
  },

  async getLogs(id: string, tail: number = 100): Promise<DeploymentLogsResponse> {
    const response = await apiClient.get<DeploymentLogsResponse>(
      `${PREFIX}/${id}/logs`, { params: { tail } }
    );
    return response.data;
  },

  async listPcapFiles(id: string): Promise<{ deployment_id: string; files: string[]; error?: string }> {
    const response = await apiClient.get<{ deployment_id: string; files: string[]; error?: string }>(
      `${PREFIX}/${id}/pcap`
    );
    return response.data;
  },

  getPcapDownloadUrl(id: string, filename: string): string {
    return `${PREFIX}/${id}/pcap/${encodeURIComponent(filename)}`;
  },
};

export default deploymentsApi;
