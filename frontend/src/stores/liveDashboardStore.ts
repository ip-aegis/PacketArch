/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import { create } from 'zustand';
import { dashboardApi, type LiveDashboardData } from '../api/dashboard';
import { extractErrorMessage } from '../utils/errorUtils';

interface LiveDashboardState {
  data: LiveDashboardData | null;
  isLoading: boolean;
  error: string | null;
  lastUpdated: number | null;
  pollingInterval: ReturnType<typeof setInterval> | null;

  fetchDashboard: () => Promise<void>;
  startPolling: (intervalMs?: number) => void;
  stopPolling: () => void;
}

export const useLiveDashboardStore = create<LiveDashboardState>()((set, get) => ({
  data: null,
  isLoading: false,
  error: null,
  lastUpdated: null,
  pollingInterval: null,

  fetchDashboard: async () => {
    // Don't set isLoading on subsequent polls to avoid flicker
    const isFirstLoad = get().data === null;
    if (isFirstLoad) {
      set({ isLoading: true });
    }

    try {
      const data = await dashboardApi.getLive();
      set({ data, isLoading: false, error: null, lastUpdated: Date.now() });
    } catch (error) {
      const message = extractErrorMessage(error, 'Failed to load dashboard data');
      set({ error: message, isLoading: false });
    }
  },

  startPolling: (intervalMs = 3000) => {
    const { pollingInterval, fetchDashboard } = get();
    if (pollingInterval) return; // Already polling

    // Fetch immediately
    fetchDashboard();

    const interval = setInterval(() => {
      fetchDashboard();
    }, intervalMs);
    set({ pollingInterval: interval });
  },

  stopPolling: () => {
    const { pollingInterval } = get();
    if (pollingInterval) {
      clearInterval(pollingInterval);
      set({ pollingInterval: null });
    }
  },
}));
