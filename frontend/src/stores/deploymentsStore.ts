/**
 * Deployments state management with Zustand
 */

import { create } from 'zustand';
import type {
  Deployment,
  UnifiedDeployment,
  DeploymentRequest,
  DeploymentLogsResponse,
} from '../types/docker';
import { deploymentsApi, type DeploymentFilters } from '../api/deployments';

interface DeploymentsState {
  deployments: UnifiedDeployment[];
  activeDeployment: UnifiedDeployment | null;
  logs: DeploymentLogsResponse | null;
  isLoading: boolean;
  error: string | null;
  pollingInterval: NodeJS.Timeout | null;

  // Actions
  fetchDeployments: (filters?: DeploymentFilters) => Promise<void>;
  fetchDeployment: (id: string) => Promise<UnifiedDeployment>;
  startDeployment: (data: DeploymentRequest) => Promise<Deployment>;
  stopDeployment: (id: string) => Promise<Deployment>;
  removeDeployment: (id: string) => Promise<void>;
  fetchLogs: (id: string, tail?: number) => Promise<DeploymentLogsResponse>;
  setActiveDeployment: (deployment: UnifiedDeployment | null) => void;
  startPolling: (scenarioId?: string) => void;
  stopPolling: () => void;
  clearError: () => void;
}

export const useDeploymentsStore = create<DeploymentsState>()((set, get) => ({
  deployments: [],
  activeDeployment: null,
  logs: null,
  isLoading: false,
  error: null,
  pollingInterval: null,

  fetchDeployments: async (filters?: DeploymentFilters) => {
    set({ isLoading: true, error: null });
    try {
      const response = await deploymentsApi.list(filters);
      set({ deployments: response.items, isLoading: false });
    } catch (error: any) {
      const message =
        error.response?.data?.detail || error.message || 'Failed to fetch deployments';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  fetchDeployment: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const deployment = await deploymentsApi.get(id);
      // Update in list
      set((state) => ({
        deployments: state.deployments.map((d) => (d.id === id ? deployment : d)),
        activeDeployment:
          state.activeDeployment?.id === id ? deployment : state.activeDeployment,
        isLoading: false,
      }));
      return deployment;
    } catch (error: any) {
      const message =
        error.response?.data?.detail || error.message || 'Failed to fetch deployment';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  startDeployment: async (data: DeploymentRequest) => {
    set({ isLoading: true, error: null });
    try {
      const deployment = await deploymentsApi.start(data);
      set((state) => ({
        deployments: [deployment, ...state.deployments],
        activeDeployment: deployment,
        isLoading: false,
      }));
      // Start polling for status updates
      get().startPolling(data.scenario_id);
      return deployment;
    } catch (error: any) {
      let message = 'Failed to start deployment';
      const detail = error.response?.data?.detail;
      if (typeof detail === 'string') {
        message = detail;
      } else if (Array.isArray(detail)) {
        // Pydantic validation errors come as an array
        message = detail.map((e: any) => e.msg || e.message || String(e)).join(', ');
      } else if (error.message) {
        message = error.message;
      }
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  stopDeployment: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const deployment = await deploymentsApi.stop(id);
      set((state) => ({
        deployments: state.deployments.map((d) => (d.id === id ? deployment : d)),
        activeDeployment:
          state.activeDeployment?.id === id ? deployment : state.activeDeployment,
        isLoading: false,
      }));
      return deployment;
    } catch (error: any) {
      const message =
        error.response?.data?.detail || error.message || 'Failed to stop deployment';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  removeDeployment: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      await deploymentsApi.remove(id);
      set((state) => ({
        deployments: state.deployments.filter((d) => d.id !== id),
        activeDeployment: state.activeDeployment?.id === id ? null : state.activeDeployment,
        isLoading: false,
      }));
    } catch (error: any) {
      const message =
        error.response?.data?.detail || error.message || 'Failed to remove deployment';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  fetchLogs: async (id: string, tail: number = 100) => {
    try {
      const logs = await deploymentsApi.getLogs(id, tail);
      set({ logs });
      return logs;
    } catch (error: any) {
      const message =
        error.response?.data?.detail || error.message || 'Failed to fetch logs';
      set({ error: message });
      throw error;
    }
  },

  setActiveDeployment: (deployment: UnifiedDeployment | null) => {
    set({ activeDeployment: deployment, logs: null });
  },

  startPolling: (scenarioId?: string) => {
    const { pollingInterval } = get();
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }

    const interval = setInterval(async () => {
      const { activeDeployment, fetchDeployment, fetchDeployments, stopPolling } = get();

      // If we have an active deployment, poll its status
      if (activeDeployment) {
        try {
          const updated = await fetchDeployment(activeDeployment.id);
          // Stop polling if deployment is no longer running
          if (['stopped', 'failed'].includes(updated.status)) {
            stopPolling();
          }
        } catch {
          // Ignore errors during polling
        }
      } else if (scenarioId) {
        // Otherwise refresh the full list for this scenario
        try {
          await fetchDeployments({ scenario_id: scenarioId });
        } catch {
          // Ignore errors during polling
        }
      }
    }, 3000); // Poll every 3 seconds

    set({ pollingInterval: interval });
  },

  stopPolling: () => {
    const { pollingInterval } = get();
    if (pollingInterval) {
      clearInterval(pollingInterval);
      set({ pollingInterval: null });
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));

export default useDeploymentsStore;
