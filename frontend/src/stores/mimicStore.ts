/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import { create } from 'zustand';
import {
  mimicApi,
  type MimicStatus,
  type MimicCell,
  type MimicPreset,
  type MimicTemplate,
  type DeployCellRequest,
  type DeployCellResponse,
  type AuthorCellRequest,
  type CmlMimicStatus,
  type CmlDeployRequest,
  type CmlDeployResponse,
  type CmlLabItem,
  type CmlLabDetail,
} from '../api/mimic';
import { extractErrorMessage } from '../utils/errorUtils';

interface MimicState {
  status: MimicStatus | null;
  cells: MimicCell[];
  presets: MimicPreset[];
  templates: MimicTemplate[];
  processModels: string[];
  cmlStatus: CmlMimicStatus | null;
  cmlLabs: CmlLabItem[];
  cmlLabDetails: Record<string, CmlLabDetail>;
  isLoading: boolean;
  isDeploying: boolean;
  error: string | null;
  fetchStatus: () => Promise<void>;
  fetchCells: () => Promise<void>;
  fetchPresets: () => Promise<void>;
  fetchTemplates: () => Promise<void>;
  fetchProcessModels: () => Promise<void>;
  deploy: (request: DeployCellRequest) => Promise<DeployCellResponse | null>;
  author: (request: AuthorCellRequest) => Promise<DeployCellResponse | null>;
  teardown: (cellSlug: string) => Promise<boolean>;
  fetchCmlStatus: () => Promise<void>;
  fetchCmlLabs: () => Promise<void>;
  fetchCmlLabDetail: (labId: string) => Promise<void>;
  deployCml: (request: CmlDeployRequest) => Promise<CmlDeployResponse | null>;
  teardownCmlLab: (labId: string) => Promise<boolean>;
  clearError: () => void;
}

export const useMimicStore = create<MimicState>()((set, get) => ({
  status: null,
  cells: [],
  presets: [],
  templates: [],
  processModels: [],
  cmlStatus: null,
  cmlLabs: [],
  cmlLabDetails: {},
  isLoading: false,
  isDeploying: false,
  error: null,

  fetchStatus: async () => {
    try {
      const status = await mimicApi.getStatus();
      set({ status });
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to fetch Mimic status') });
    }
  },

  fetchCells: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await mimicApi.getCells();
      set({ cells: response.items, isLoading: false });
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to fetch Mimic cells'), isLoading: false });
    }
  },

  fetchPresets: async () => {
    try {
      const response = await mimicApi.getPresets();
      set({ presets: response.items });
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to fetch Mimic presets') });
    }
  },

  fetchTemplates: async () => {
    try {
      const response = await mimicApi.getTemplates();
      set({ templates: response.items });
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to fetch Mimic templates') });
    }
  },

  fetchProcessModels: async () => {
    try {
      const response = await mimicApi.getProcessModels();
      set({ processModels: response.models });
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to fetch process models') });
    }
  },

  deploy: async (request: DeployCellRequest) => {
    set({ isDeploying: true, error: null });
    try {
      const result = await mimicApi.deploy(request);
      set({ isDeploying: false });
      get().fetchCells();
      return result;
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Mimic deploy failed'), isDeploying: false });
      return null;
    }
  },

  author: async (request: AuthorCellRequest) => {
    set({ isDeploying: true, error: null });
    try {
      const result = await mimicApi.author(request);
      set({ isDeploying: false });
      get().fetchCells();
      return result;
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Mimic author failed'), isDeploying: false });
      return null;
    }
  },

  teardown: async (cellSlug: string) => {
    set({ error: null });
    try {
      await mimicApi.teardown(cellSlug);
      get().fetchCells();
      return true;
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Mimic teardown failed') });
      return false;
    }
  },

  fetchCmlStatus: async () => {
    try {
      const cmlStatus = await mimicApi.getCmlStatus();
      set({ cmlStatus });
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to fetch CML status') });
    }
  },

  fetchCmlLabs: async () => {
    try {
      const response = await mimicApi.getCmlLabs();
      set({ cmlLabs: response.items });
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to fetch off-box labs') });
    }
  },

  fetchCmlLabDetail: async (labId: string) => {
    try {
      const detail = await mimicApi.getCmlLabDetail(labId);
      set((s) => ({ cmlLabDetails: { ...s.cmlLabDetails, [labId]: detail } }));
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to fetch lab detail') });
    }
  },

  deployCml: async (request: CmlDeployRequest) => {
    set({ isDeploying: true, error: null });
    try {
      const result = await mimicApi.deployCml(request);
      set({ isDeploying: false });
      get().fetchCmlLabs();
      return result;
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Off-box deploy failed'), isDeploying: false });
      return null;
    }
  },

  teardownCmlLab: async (labId: string) => {
    set({ error: null });
    try {
      await mimicApi.teardownCmlLab(labId);
      get().fetchCmlLabs();
      return true;
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Off-box teardown failed') });
      return false;
    }
  },

  clearError: () => set({ error: null }),
}));

export default useMimicStore;
