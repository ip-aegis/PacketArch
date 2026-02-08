/**
 * Docker hosts state management with Zustand
 */

import { create } from 'zustand';
import type {
  DockerHost,
  DockerHostCreate,
  DockerHostUpdate,
  DockerHostTestResult,
  DockerHostInterfaceList,
} from '../types/docker';
import { dockerHostsApi } from '../api/dockerHosts';
import { extractErrorMessage } from '../utils/errorUtils';
import { createResourceSlice } from './createResourceStore';

const crud = createResourceSlice<DockerHost, DockerHostCreate, DockerHostUpdate>({
  resourceName: 'Docker host',
  api: dockerHostsApi,
  listExtractor: (r) => r.items,
  itemsKey: 'hosts',
  selectedKey: 'selectedHost',
});

interface DockerHostsState {
  hosts: DockerHost[];
  selectedHost: DockerHost | null;
  interfaces: DockerHostInterfaceList | null;
  isLoading: boolean;
  error: string | null;

  fetchHosts: () => Promise<void>;
  fetchHost: (id: string) => Promise<DockerHost>;
  createHost: (data: DockerHostCreate) => Promise<DockerHost>;
  updateHost: (id: string, data: DockerHostUpdate) => Promise<DockerHost>;
  deleteHost: (id: string) => Promise<void>;
  testConnection: (id: string) => Promise<DockerHostTestResult>;
  fetchInterfaces: (id: string) => Promise<DockerHostInterfaceList>;
  setSelectedHost: (host: DockerHost | null) => void;
  clearError: () => void;
}

export const useDockerHostsStore = create<DockerHostsState>()((set, get) => {
  const { fetchAll, fetchOne, createOne, updateOne, deleteOne, clearError } = crud(set, get);

  return {
    hosts: [],
    selectedHost: null,
    interfaces: null,
    isLoading: false,
    error: null,

    fetchHosts: fetchAll,
    fetchHost: fetchOne,
    createHost: createOne,
    updateHost: updateOne,
    deleteHost: deleteOne,
    clearError,

    setSelectedHost: (host: DockerHost | null) => {
      set({ selectedHost: host, interfaces: null });
    },

    testConnection: async (id: string) => {
      try {
        const result = await dockerHostsApi.testConnection(id);
        if (result.success) {
          await get().fetchHosts();
        }
        return result;
      } catch (error: unknown) {
        const message = extractErrorMessage(error, 'Connection test failed');
        return {
          success: false,
          message,
          docker_version: null,
          api_version: null,
          latency_ms: null,
        };
      }
    },

    fetchInterfaces: async (id: string) => {
      set({ isLoading: true, error: null });
      try {
        const interfaces = await dockerHostsApi.listInterfaces(id);
        set({ interfaces, isLoading: false });
        return interfaces;
      } catch (error: unknown) {
        const message = extractErrorMessage(error, 'Failed to fetch interfaces');
        set({ error: message, isLoading: false });
        throw error;
      }
    },
  };
});

export default useDockerHostsStore;
