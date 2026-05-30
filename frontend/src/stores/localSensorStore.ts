/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Local sensor lab state (Zustand). Mirrors cmlStore.ts.
 */

import { create } from 'zustand';
import {
  localSensorApi,
  type LocalHostStatus,
  type LocalLabItem,
  type LocalLabBuildRequest,
  type LocalLabBuildResponse,
} from '../api/localSensor';
import { extractErrorMessage } from '../utils/errorUtils';

interface LocalSensorState {
  hostStatus: LocalHostStatus | null;
  labs: LocalLabItem[];
  buildResult: LocalLabBuildResponse | null;

  isLoading: boolean;
  isBuilding: boolean;
  error: string | null;

  fetchHostStatus: () => Promise<void>;
  fetchLabs: () => Promise<void>;
  build: (request: LocalLabBuildRequest) => Promise<LocalLabBuildResponse | null>;
  teardown: (labId: string) => Promise<boolean>;
  clearError: () => void;
  clearBuildResult: () => void;
}

export const useLocalSensorStore = create<LocalSensorState>()((set, get) => ({
  hostStatus: null,
  labs: [],
  buildResult: null,
  isLoading: false,
  isBuilding: false,
  error: null,

  fetchHostStatus: async () => {
    try {
      const hostStatus = await localSensorApi.getHostStatus();
      set({ hostStatus });
    } catch (error: unknown) {
      set({
        hostStatus: {
          available: false,
          host_agent_seen: false,
          message: extractErrorMessage(error, 'Failed to fetch host status'),
        },
      });
    }
  },

  fetchLabs: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await localSensorApi.getLabs();
      set({ labs: response.items, isLoading: false });
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to fetch local labs'), isLoading: false });
    }
  },

  build: async (request: LocalLabBuildRequest) => {
    set({ isBuilding: true, error: null, buildResult: null });
    try {
      const result = await localSensorApi.build(request);
      set({ buildResult: result, isBuilding: false });
      get().fetchLabs();
      return result;
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Local lab build failed'), isBuilding: false });
      return null;
    }
  },

  teardown: async (labId: string) => {
    set({ error: null });
    try {
      await localSensorApi.teardown(labId);
      get().fetchLabs();
      return true;
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Teardown failed') });
      return false;
    }
  },

  clearError: () => set({ error: null }),
  clearBuildResult: () => set({ buildResult: null }),
}));

export default useLocalSensorStore;
