/**
 * Docker Hosts API functions
 */

import { createCrudApi } from './createCrudApi';
import apiClient from './client';
import type {
  DockerHost,
  DockerHostCreate,
  DockerHostUpdate,
  DockerHostListResponse,
  DockerHostTestResult,
  DockerHostInterfaceList,
} from '../types/docker';

const PREFIX = '/api/v1/docker-hosts';

export const dockerHostsApi = {
  ...createCrudApi<DockerHost, DockerHostCreate, DockerHostUpdate>({
    prefix: PREFIX,
    updateMethod: 'put',
  }),

  async list(): Promise<DockerHostListResponse> {
    const response = await apiClient.get<DockerHostListResponse>(PREFIX);
    return response.data;
  },

  async testConnection(id: string): Promise<DockerHostTestResult> {
    const response = await apiClient.post<DockerHostTestResult>(`${PREFIX}/${id}/test`);
    return response.data;
  },

  async listInterfaces(id: string): Promise<DockerHostInterfaceList> {
    const response = await apiClient.get<DockerHostInterfaceList>(`${PREFIX}/${id}/interfaces`);
    return response.data;
  },
};

export default dockerHostsApi;
