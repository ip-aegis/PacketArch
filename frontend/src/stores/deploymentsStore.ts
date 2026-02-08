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
import { extractErrorMessage } from '../utils/errorUtils';
import { createResourceSlice } from './createResourceStore';

// Adapter: the factory expects a standard CRUD api shape.
// start/stop are non-standard so we stub create/update (unused).
const crudApi = {
  list: deploymentsApi.list,
  get: deploymentsApi.get,
  create: deploymentsApi.start as any,
  update: (() => { throw new Error('not used'); }) as any,
  delete: deploymentsApi.remove,
};

const crud = createResourceSlice<UnifiedDeployment, DeploymentRequest, never>({
  resourceName: 'deployment',
  api: crudApi,
  listExtractor: (r) => r.items,
  itemsKey: 'deployments',
  selectedKey: 'activeDeployment',
});

interface DeploymentsState {
  deployments: UnifiedDeployment[];
  activeDeployment: UnifiedDeployment | null;
  logs: DeploymentLogsResponse | null;
  isLoading: boolean;
  error: string | null;
  pollingInterval: NodeJS.Timeout | null;

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

export const useDeploymentsStore = create<DeploymentsState>()((set, get) => {
  const { fetchAll, fetchOne, deleteOne, clearError } = crud(set, get);

  return {
    deployments: [],
    activeDeployment: null,
    logs: null,
    isLoading: false,
    error: null,
    pollingInterval: null,

    fetchDeployments: fetchAll,
    fetchDeployment: fetchOne,
    removeDeployment: deleteOne,
    clearError,

    startDeployment: async (data: DeploymentRequest) => {
      set({ isLoading: true, error: null });
      try {
        const deployment = await deploymentsApi.start(data);
        set((state) => ({
          deployments: [deployment, ...state.deployments],
          activeDeployment: deployment,
          isLoading: false,
        }));
        get().startPolling(data.scenario_id);
        return deployment;
      } catch (error: unknown) {
        const message = extractErrorMessage(error, 'Failed to start deployment');
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
      } catch (error: unknown) {
        const message = extractErrorMessage(error, 'Failed to stop deployment');
        set({ error: message, isLoading: false });
        throw error;
      }
    },

    fetchLogs: async (id: string, tail: number = 100) => {
      try {
        const logs = await deploymentsApi.getLogs(id, tail);
        set({ logs });
        return logs;
      } catch (error: unknown) {
        const message = extractErrorMessage(error, 'Failed to fetch logs');
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

        if (activeDeployment) {
          try {
            const updated = await fetchDeployment(activeDeployment.id);
            if (['stopped', 'failed'].includes(updated.status)) {
              stopPolling();
            }
          } catch {
            // Ignore errors during polling
          }
        } else if (scenarioId) {
          try {
            await fetchDeployments({ scenario_id: scenarioId });
          } catch {
            // Ignore errors during polling
          }
        }
      }, 3000);

      set({ pollingInterval: interval });
    },

    stopPolling: () => {
      const { pollingInterval } = get();
      if (pollingInterval) {
        clearInterval(pollingInterval);
        set({ pollingInterval: null });
      }
    },
  };
});

export default useDeploymentsStore;
