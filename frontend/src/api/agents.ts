/**
 * Traffic Agents API Client
 * Manages WebSocket-based remote traffic generation agents
 */

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

const AGENTS_PREFIX = '/api/v1/agents';

export const agentsApi = {
  /**
   * List all agents with pagination
   */
  async list(page = 1, pageSize = 50, status?: string): Promise<AgentListResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (status) {
      params.append('status_filter', status);
    }
    const response = await apiClient.get<AgentListResponse>(`${AGENTS_PREFIX}?${params}`);
    return response.data;
  },

  /**
   * Create a new agent and get its authentication token
   */
  async create(data: AgentCreate): Promise<TrafficAgentWithToken> {
    const response = await apiClient.post<TrafficAgentWithToken>(AGENTS_PREFIX, data);
    return response.data;
  },

  /**
   * Get agent details
   */
  async get(id: string): Promise<TrafficAgent> {
    const response = await apiClient.get<TrafficAgent>(`${AGENTS_PREFIX}/${id}`);
    return response.data;
  },

  /**
   * Update an agent
   */
  async update(id: string, data: AgentUpdate): Promise<TrafficAgent> {
    const response = await apiClient.put<TrafficAgent>(`${AGENTS_PREFIX}/${id}`, data);
    return response.data;
  },

  /**
   * Delete an agent
   */
  async delete(id: string): Promise<void> {
    await apiClient.delete(`${AGENTS_PREFIX}/${id}`);
  },

  /**
   * Regenerate agent authentication token
   */
  async regenerateToken(id: string): Promise<TrafficAgentWithToken> {
    const response = await apiClient.post<TrafficAgentWithToken>(`${AGENTS_PREFIX}/${id}/token`);
    return response.data;
  },

  /**
   * Get real-time connection info for a connected agent
   */
  async getConnection(id: string): Promise<AgentConnectionInfo> {
    const response = await apiClient.get<AgentConnectionInfo>(`${AGENTS_PREFIX}/${id}/connection`);
    return response.data;
  },

  /**
   * Get network interfaces from a connected agent
   */
  async getInterfaces(id: string): Promise<AgentInterfacesResponse> {
    const response = await apiClient.get<AgentInterfacesResponse>(`${AGENTS_PREFIX}/${id}/interfaces`);
    return response.data;
  },

  /**
   * Deploy a scenario to an agent
   */
  async deploy(agentId: string, data: DeploymentCreate): Promise<AgentDeployment> {
    const response = await apiClient.post<AgentDeployment>(`${AGENTS_PREFIX}/${agentId}/deploy`, data);
    return response.data;
  },

  /**
   * Stop a deployment
   */
  async stopDeployment(agentId: string, scenarioId: string): Promise<void> {
    await apiClient.delete(`${AGENTS_PREFIX}/${agentId}/deploy/${scenarioId}`);
  },

  /**
   * List deployments for an agent
   */
  async listDeployments(agentId: string, activeOnly = true): Promise<AgentDeployment[]> {
    const params = new URLSearchParams({ active_only: activeOnly.toString() });
    const response = await apiClient.get<AgentDeployment[]>(
      `${AGENTS_PREFIX}/${agentId}/deployments?${params}`
    );
    return response.data;
  },

  /**
   * List all currently connected agents
   */
  async listConnected(): Promise<AgentConnectionInfo[]> {
    const response = await apiClient.get<AgentConnectionInfo[]>(`${AGENTS_PREFIX}/connected`);
    return response.data;
  },

  /**
   * Build the agent Docker image and save it for distribution
   */
  async buildImage(): Promise<{ status: string; message: string; version?: string; started_at?: string }> {
    const response = await apiClient.post<{ status: string; message: string; version?: string; started_at?: string }>(`${AGENTS_PREFIX}/build-image`);
    return response.data;
  },

  /**
   * Get the current build status
   */
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
    }>(`${AGENTS_PREFIX}/build-status`);
    return response.data;
  },

  /**
   * Check if the agent image is available for download
   */
  async getImageStatus(): Promise<{ available: boolean; path?: string; size?: number; modified?: string }> {
    const response = await apiClient.get<{ available: boolean; path?: string; size?: number; modified?: string }>(`${AGENTS_PREFIX}/image-status`);
    return response.data;
  },

  /**
   * Trigger an update on a connected agent
   */
  async triggerUpdate(agentId: string): Promise<{ message: string; target_version?: string }> {
    const response = await apiClient.post<{ message: string; target_version?: string }>(`${AGENTS_PREFIX}/${agentId}/update`);
    return response.data;
  },

  /**
   * Get the current update status for an agent
   */
  async getUpdateStatus(agentId: string): Promise<AgentUpdateStatus> {
    const response = await apiClient.get<AgentUpdateStatus>(`${AGENTS_PREFIX}/${agentId}/update-status`);
    return response.data;
  },

  /**
   * Clear the update status for an agent (after user acknowledges)
   */
  async clearUpdateStatus(agentId: string): Promise<void> {
    await apiClient.delete(`${AGENTS_PREFIX}/${agentId}/update-status`);
  },

  /**
   * Get recent logs from a connected agent
   */
  async getLogs(agentId: string, lines = 100): Promise<{ agent_id: string; logs: string[]; count: number }> {
    const params = new URLSearchParams({ lines: lines.toString() });
    const response = await apiClient.get<{ agent_id: string; logs: string[]; count: number }>(
      `${AGENTS_PREFIX}/${agentId}/logs?${params}`
    );
    return response.data;
  },

  /**
   * Test connectivity to an agent and measure latency
   */
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
    }>(`${AGENTS_PREFIX}/${agentId}/ping`);
    return response.data;
  },
};

export default agentsApi;
