/**
 * Traffic Agents API Client
 * Manages WebSocket-based remote traffic generation agents
 */

import { createCrudApi } from './createCrudApi';
import apiClient from './client';
import type {
  TrafficAgent,
  TrafficAgentWithToken,
  AgentCreate,
  AgentUpdate,
  AgentListResponse,
  AgentConnectionInfo,
  AgentInterfacesResponse,
  AgentDeployment,
  DeploymentCreate,
  AgentUpdateStatus,
} from '../types/agent';

const PREFIX = '/api/v1/agents';

export const agentsApi = {
  ...createCrudApi<TrafficAgent, AgentCreate, AgentUpdate>({
    prefix: PREFIX,
    updateMethod: 'put',
  }),

  async list(page = 1, pageSize = 50, status?: string): Promise<AgentListResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (status) {
      params.append('status_filter', status);
    }
    const response = await apiClient.get<AgentListResponse>(`${PREFIX}?${params}`);
    return response.data;
  },

  async create(data: AgentCreate): Promise<TrafficAgentWithToken> {
    const response = await apiClient.post<TrafficAgentWithToken>(PREFIX, data);
    return response.data;
  },

  async regenerateToken(id: string): Promise<TrafficAgentWithToken> {
    const response = await apiClient.post<TrafficAgentWithToken>(`${PREFIX}/${id}/token`);
    return response.data;
  },

  async getConnection(id: string): Promise<AgentConnectionInfo> {
    const response = await apiClient.get<AgentConnectionInfo>(`${PREFIX}/${id}/connection`);
    return response.data;
  },

  async getInterfaces(id: string): Promise<AgentInterfacesResponse> {
    const response = await apiClient.get<AgentInterfacesResponse>(`${PREFIX}/${id}/interfaces`);
    return response.data;
  },

  async deploy(agentId: string, data: DeploymentCreate): Promise<AgentDeployment> {
    const response = await apiClient.post<AgentDeployment>(`${PREFIX}/${agentId}/deploy`, data);
    return response.data;
  },

  async stopDeployment(agentId: string, scenarioId: string): Promise<void> {
    await apiClient.delete(`${PREFIX}/${agentId}/deploy/${scenarioId}`);
  },

  async listDeployments(agentId: string, activeOnly = true): Promise<AgentDeployment[]> {
    const params = new URLSearchParams({ active_only: activeOnly.toString() });
    const response = await apiClient.get<AgentDeployment[]>(
      `${PREFIX}/${agentId}/deployments?${params}`
    );
    return response.data;
  },

  async listConnected(): Promise<AgentConnectionInfo[]> {
    const response = await apiClient.get<AgentConnectionInfo[]>(`${PREFIX}/connected`);
    return response.data;
  },

  async buildImage(): Promise<{ status: string; message: string; version?: string; started_at?: string }> {
    const response = await apiClient.post<{ status: string; message: string; version?: string; started_at?: string }>(`${PREFIX}/build-image`);
    return response.data;
  },

  async getBuildStatus(): Promise<{
    status: 'idle' | 'building' | 'complete' | 'failed';
    stage?: string;
    message: string;
    version?: string;
    error?: string;
    started_at?: string;
    completed_at?: string;
  }> {
    const response = await apiClient.get<{
      status: 'idle' | 'building' | 'complete' | 'failed';
      stage?: string;
      message: string;
      version?: string;
      error?: string;
      started_at?: string;
      completed_at?: string;
    }>(`${PREFIX}/build-status`);
    return response.data;
  },

  async getImageStatus(): Promise<{ available: boolean; path?: string; size?: number; modified?: string }> {
    const response = await apiClient.get<{ available: boolean; path?: string; size?: number; modified?: string }>(`${PREFIX}/image-status`);
    return response.data;
  },

  async triggerUpdate(agentId: string): Promise<{ message: string; target_version?: string }> {
    const response = await apiClient.post<{ message: string; target_version?: string }>(`${PREFIX}/${agentId}/update`);
    return response.data;
  },

  async getUpdateStatus(agentId: string): Promise<AgentUpdateStatus> {
    const response = await apiClient.get<AgentUpdateStatus>(`${PREFIX}/${agentId}/update-status`);
    return response.data;
  },

  async clearUpdateStatus(agentId: string): Promise<void> {
    await apiClient.delete(`${PREFIX}/${agentId}/update-status`);
  },

  async getLogs(agentId: string, lines = 100): Promise<{ agent_id: string; logs: string[]; count: number }> {
    const params = new URLSearchParams({ lines: lines.toString() });
    const response = await apiClient.get<{ agent_id: string; logs: string[]; count: number }>(
      `${PREFIX}/${agentId}/logs?${params}`
    );
    return response.data;
  },

  async pingTest(agentId: string): Promise<{
    agent_id: string;
    status: string;
    round_trip_ms: number;
    server_to_agent_ms: number;
    agent_to_server_ms: number;
  }> {
    const response = await apiClient.post<{
      agent_id: string;
      status: string;
      round_trip_ms: number;
      server_to_agent_ms: number;
      agent_to_server_ms: number;
    }>(`${PREFIX}/${agentId}/ping`);
    return response.data;
  },
};

export default agentsApi;
