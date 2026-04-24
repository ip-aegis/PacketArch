/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Deployments state management with Zustand
 */

import { create } from 'zustand';
import type { UnifiedDeployment } from '../types/docker';
import { deploymentsApi, type DeploymentFilters } from '../api/deployments';
import { extractErrorMessage } from '../utils/errorUtils';

interface DeploymentsState {
  deployments: UnifiedDeployment[];
  activeDeployment: UnifiedDeployment | null;
  isLoading: boolean;
  error: string | null;

  fetchDeployments: (filters?: DeploymentFilters) => Promise<void>;
  removeDeployment: (id: string) => Promise<void>;
  setActiveDeployment: (deployment: UnifiedDeployment | null) => void;
  clearError: () => void;
}

export const useDeploymentsStore = create<DeploymentsState>()((set) => ({
  deployments: [],
  activeDeployment: null,
  isLoading: false,
  error: null,

  fetchDeployments: async (filters?: DeploymentFilters) => {
    set({ isLoading: true, error: null });
    try {
      const response = await deploymentsApi.list(filters || {});
      set({ deployments: response.items, isLoading: false });
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Failed to fetch deployments');
      set({ error: message, isLoading: false });
    }
  },

  removeDeployment: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      await deploymentsApi.remove(id);
      set((state) => ({
        deployments: state.deployments.filter((d) => d.id !== id),
        activeDeployment:
          state.activeDeployment?.id === id ? null : state.activeDeployment,
        isLoading: false,
      }));
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Failed to remove deployment');
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  setActiveDeployment: (deployment: UnifiedDeployment | null) => {
    set({ activeDeployment: deployment });
  },

  clearError: () => set({ error: null }),
}));

export default useDeploymentsStore;
