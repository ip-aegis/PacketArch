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

interface DockerHostsState {
  hosts: DockerHost[];
  selectedHost: DockerHost | null;
  interfaces: DockerHostInterfaceList | null;
  isLoading: boolean;
  error: string | null;

  // Actions
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

// Helper to extract error message from various error formats
const extractErrorMessage = (error: any, fallback: string): string => {
  const detail = error.response?.data?.detail;

  // Handle Pydantic validation errors (array of error objects)
  if (Array.isArray(detail)) {
    return detail.map((err: any) => err.msg || JSON.stringify(err)).join('; ');
  }

  // Handle string detail
  if (typeof detail === 'string') {
    return detail;
  }

  // Handle object with message
  if (detail?.msg) {
    return detail.msg;
  }

  // Fallback to error message
  return error.message || fallback;
};

export const useDockerHostsStore = create<DockerHostsState>()((set, get) => ({
  hosts: [],
  selectedHost: null,
  interfaces: null,
  isLoading: false,
  error: null,

  fetchHosts: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await dockerHostsApi.list();
      set({ hosts: response.items, isLoading: false });
    } catch (error: any) {
      const message = extractErrorMessage(error, 'Failed to fetch Docker hosts');
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  fetchHost: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const host = await dockerHostsApi.get(id);
      set({ selectedHost: host, isLoading: false });
      return host;
    } catch (error: any) {
      const message = extractErrorMessage(error, 'Failed to fetch Docker host');
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  createHost: async (data: DockerHostCreate) => {
    set({ isLoading: true, error: null });
    try {
      const host = await dockerHostsApi.create(data);
      set((state) => ({
        hosts: [...state.hosts, host],
        isLoading: false,
      }));
      return host;
    } catch (error: any) {
      const message = extractErrorMessage(error, 'Failed to create Docker host');
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  updateHost: async (id: string, data: DockerHostUpdate) => {
    set({ isLoading: true, error: null });
    try {
      const host = await dockerHostsApi.update(id, data);
      set((state) => ({
        hosts: state.hosts.map((h) => (h.id === id ? host : h)),
        selectedHost: state.selectedHost?.id === id ? host : state.selectedHost,
        isLoading: false,
      }));
      return host;
    } catch (error: any) {
      const message = extractErrorMessage(error, 'Failed to update Docker host');
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  deleteHost: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      await dockerHostsApi.delete(id);
      set((state) => ({
        hosts: state.hosts.filter((h) => h.id !== id),
        selectedHost: state.selectedHost?.id === id ? null : state.selectedHost,
        isLoading: false,
      }));
    } catch (error: any) {
      const message = extractErrorMessage(error, 'Failed to delete Docker host');
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  testConnection: async (id: string) => {
    try {
      const result = await dockerHostsApi.testConnection(id);
      // Refresh host to get updated last_connected_at
      if (result.success) {
        await get().fetchHosts();
      }
      return result;
    } catch (error: any) {
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
    } catch (error: any) {
      const message = extractErrorMessage(error, 'Failed to fetch interfaces');
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  setSelectedHost: (host: DockerHost | null) => {
    set({ selectedHost: host, interfaces: null });
  },

  clearError: () => {
    set({ error: null });
  },
}));

export default useDockerHostsStore;
