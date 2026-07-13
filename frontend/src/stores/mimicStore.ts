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
} from '../api/mimic';
import { extractErrorMessage } from '../utils/errorUtils';

interface MimicState {
  status: MimicStatus | null;
  cells: MimicCell[];
  presets: MimicPreset[];
  templates: MimicTemplate[];
  processModels: string[];
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
  clearError: () => void;
}

export const useMimicStore = create<MimicState>()((set, get) => ({
  status: null,
  cells: [],
  presets: [],
  templates: [],
  processModels: [],
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

  clearError: () => set({ error: null }),
}));

export default useMimicStore;
