/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Cisco Modeling Labs (CML) state management with Zustand
 */

import { create } from 'zustand';
import {
  cmlApi,
  type CMLSettings,
  type CMLSettingsUpdate,
  type CMLConnectionStatus,
  type CMLTestConnectionRequest,
  type CMLLab,
  type CMLNode,
  type CMLDeployRequest,
  type CMLDeployResponse,
  type CMLUndeployRequest,
  type CMLDeploymentItem,
  type CMLLabBuildRequest,
  type CMLLabBuildResponse,
  type CMLTeardownLabRequest,
} from '../api/cml';
import { extractErrorMessage } from '../utils/errorUtils';

interface CmlState {
  settings: CMLSettings | null;
  connectionStatus: CMLConnectionStatus | null;
  labs: CMLLab[];
  labNodes: CMLNode[];
  deployments: CMLDeploymentItem[];
  deployResult: CMLDeployResponse | null;
  buildResult: CMLLabBuildResponse | null;

  isLoading: boolean;
  isTesting: boolean;
  isLoadingLabs: boolean;
  isLoadingNodes: boolean;
  isDeploying: boolean;
  isBuilding: boolean;
  error: string | null;

  fetchSettings: () => Promise<void>;
  updateSettings: (settings: CMLSettingsUpdate) => Promise<void>;
  fetchStatus: () => Promise<void>;
  testConnection: (request: CMLTestConnectionRequest) => Promise<{ success: boolean; message: string }>;
  fetchLabs: () => Promise<void>;
  fetchLabNodes: (labId: string) => Promise<void>;
  deploy: (request: CMLDeployRequest) => Promise<CMLDeployResponse | null>;
  undeploy: (request: CMLUndeployRequest) => Promise<boolean>;
  buildLab: (request: CMLLabBuildRequest) => Promise<CMLLabBuildResponse | null>;
  teardownLab: (request: CMLTeardownLabRequest) => Promise<boolean>;
  fetchDeployments: () => Promise<void>;
  clearError: () => void;
  clearDeployResult: () => void;
  clearBuildResult: () => void;
}

export const useCmlStore = create<CmlState>()((set, get) => ({
  settings: null,
  connectionStatus: null,
  labs: [],
  labNodes: [],
  deployments: [],
  deployResult: null,
  buildResult: null,
  isLoading: false,
  isTesting: false,
  isLoadingLabs: false,
  isLoadingNodes: false,
  isDeploying: false,
  isBuilding: false,
  error: null,

  fetchSettings: async () => {
    set({ isLoading: true, error: null });
    try {
      const settings = await cmlApi.getSettings();
      set({ settings, isLoading: false });
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to fetch CML settings'), isLoading: false });
    }
  },

  updateSettings: async (settingsUpdate: CMLSettingsUpdate) => {
    set({ isLoading: true, error: null });
    try {
      const settings = await cmlApi.updateSettings(settingsUpdate);
      set({ settings, isLoading: false });
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to update CML settings'), isLoading: false });
      throw error;
    }
  },

  fetchStatus: async () => {
    set({ isLoading: true, error: null });
    try {
      const status = await cmlApi.getStatus();
      set({ connectionStatus: status, isLoading: false });
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Failed to fetch CML status');
      set({ error: message, isLoading: false, connectionStatus: { connected: false, message, version: null } });
    }
  },

  testConnection: async (request: CMLTestConnectionRequest) => {
    set({ isTesting: true, error: null });
    try {
      const result = await cmlApi.testConnection(request);
      set({ isTesting: false });
      return result;
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Connection test failed');
      set({ isTesting: false });
      return { success: false, message };
    }
  },

  fetchLabs: async () => {
    set({ isLoadingLabs: true, error: null });
    try {
      const response = await cmlApi.getLabs();
      set({ labs: response.items, isLoadingLabs: false });
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to fetch CML labs'), isLoadingLabs: false });
    }
  },

  fetchLabNodes: async (labId: string) => {
    set({ isLoadingNodes: true, error: null, labNodes: [] });
    try {
      const response = await cmlApi.getLabNodes(labId);
      set({ labNodes: response.items, isLoadingNodes: false });
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to fetch lab nodes'), isLoadingNodes: false });
    }
  },

  deploy: async (request: CMLDeployRequest) => {
    set({ isDeploying: true, error: null, deployResult: null });
    try {
      const result = await cmlApi.deploy(request);
      set({ deployResult: result, isDeploying: false });
      get().fetchDeployments();
      return result;
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Deploy failed'), isDeploying: false });
      return null;
    }
  },

  undeploy: async (request: CMLUndeployRequest) => {
    set({ error: null });
    try {
      await cmlApi.undeploy(request);
      get().fetchDeployments();
      return true;
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Undeploy failed') });
      return false;
    }
  },

  buildLab: async (request: CMLLabBuildRequest) => {
    set({ isBuilding: true, error: null, buildResult: null });
    try {
      const result = await cmlApi.buildLab(request);
      set({ buildResult: result, isBuilding: false });
      get().fetchDeployments();
      return result;
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Lab build failed'), isBuilding: false });
      return null;
    }
  },

  teardownLab: async (request: CMLTeardownLabRequest) => {
    set({ error: null });
    try {
      await cmlApi.teardownLab(request);
      get().fetchDeployments();
      return true;
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Teardown failed') });
      return false;
    }
  },

  fetchDeployments: async () => {
    try {
      const response = await cmlApi.getDeployments();
      set({ deployments: response.items });
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to fetch deployments') });
    }
  },

  clearError: () => set({ error: null }),
  clearDeployResult: () => set({ deployResult: null }),
  clearBuildResult: () => set({ buildResult: null }),
}));

export default useCmlStore;
