/**
 * Docker Hosts API functions
 */

import apiClient from './client';
import type {
  DockerHost,
  DockerHostCreate,
  DockerHostUpdate,
  DockerHostListResponse,
  DockerHostTestResult,
  DockerHostInterfaceList,
} from '../types/docker';

const DOCKER_HOSTS_PREFIX = '/api/v1/docker-hosts';

export const dockerHostsApi = {
  /**
   * List all Docker hosts
   */
  async list(): Promise<DockerHostListResponse> {
    const response = await apiClient.get<DockerHostListResponse>(DOCKER_HOSTS_PREFIX);
    return response.data;
  },

  /**
   * Get a single Docker host by ID
   */
  async get(id: string): Promise<DockerHost> {
    const response = await apiClient.get<DockerHost>(`${DOCKER_HOSTS_PREFIX}/${id}`);
    return response.data;
  },

  /**
   * Create a new Docker host
   */
  async create(data: DockerHostCreate): Promise<DockerHost> {
    const response = await apiClient.post<DockerHost>(DOCKER_HOSTS_PREFIX, data);
    return response.data;
  },

  /**
   * Update an existing Docker host
   */
  async update(id: string, data: DockerHostUpdate): Promise<DockerHost> {
    const response = await apiClient.put<DockerHost>(`${DOCKER_HOSTS_PREFIX}/${id}`, data);
    return response.data;
  },

  /**
   * Delete a Docker host
   */
  async delete(id: string): Promise<void> {
    await apiClient.delete(`${DOCKER_HOSTS_PREFIX}/${id}`);
  },

  /**
   * Test connection to a Docker host
   */
  async testConnection(id: string): Promise<DockerHostTestResult> {
    const response = await apiClient.post<DockerHostTestResult>(
      `${DOCKER_HOSTS_PREFIX}/${id}/test`
    );
    return response.data;
  },

  /**
   * List network interfaces on a Docker host
   */
  async listInterfaces(id: string): Promise<DockerHostInterfaceList> {
    const response = await apiClient.get<DockerHostInterfaceList>(
      `${DOCKER_HOSTS_PREFIX}/${id}/interfaces`
    );
    return response.data;
  },
};

export default dockerHostsApi;
