/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Attack Simulation Zustand Store
 * Manages playbook selection, configuration, and runtime state.
 */

import { create } from 'zustand';
import { attacksApi } from '../api/attacks';
import type {
  AttackPlaybook,
  AttackPlaybookConfig,
  AttackPlaybookSummary,
  AttackReport,
  AttackState,
} from '../types/attackPlaybook';

type InjectionStatus = 'idle' | 'injecting' | 'polling' | 'confirmed' | 'failed';

interface AttackStore {
  // Playbook library
  playbooks: AttackPlaybookSummary[];
  isLoadingPlaybooks: boolean;

  // Selected playbook (full detail)
  selectedPlaybook: AttackPlaybook | null;
  isLoadingPlaybook: boolean;

  // Configuration
  playbookConfig: AttackPlaybookConfig | null;

  // Injection tracking (per-scenario, keyed by scenarioId)
  injectionStatus: Record<string, InjectionStatus>;
  injectionError: Record<string, string | null>;

  // Actions
  fetchPlaybooks: () => Promise<void>;
  fetchCompatible: (scenarioId: string) => Promise<void>;
  selectPlaybook: (playbookId: string) => Promise<void>;
  clearSelection: () => void;
  setConfig: (config: AttackPlaybookConfig) => void;

  // Injection with polling confirmation (now per-scenario)
  injectAndPoll: (scenarioId: string) => Promise<void>;
  resetInjection: (scenarioId: string) => void;

  // Runtime controls
  startAttack: (scenarioId: string) => Promise<void>;
  stopAttack: (scenarioId: string) => Promise<void>;
  advanceStage: (scenarioId: string) => Promise<void>;
  togglePause: (scenarioId: string, isPaused: boolean) => Promise<void>;

  // After-action report — fetched on demand. Keyed by scenarioId so
  // each scenario's last report is cached for re-open without refetch.
  attackReports: Record<string, { source: 'live' | 'history' | 'none'; report: AttackReport | null }>;
  isFetchingReport: Record<string, boolean>;
  fetchAttackReport: (scenarioId: string) => Promise<void>;
}

// Internal timer refs per scenario (not in store state to avoid serialization issues)
const _injectionPollTimers: Map<string, ReturnType<typeof setInterval>> = new Map();

function stopInjectionPolling(scenarioId: string) {
  const timer = _injectionPollTimers.get(scenarioId);
  if (timer) {
    clearInterval(timer);
    _injectionPollTimers.delete(scenarioId);
  }
}

export const useAttackStore = create<AttackStore>((set, get) => ({
  playbooks: [],
  isLoadingPlaybooks: false,
  selectedPlaybook: null,
  isLoadingPlaybook: false,
  playbookConfig: null,
  injectionStatus: {},
  injectionError: {},

  fetchPlaybooks: async () => {
    set({ isLoadingPlaybooks: true });
    try {
      const playbooks = await attacksApi.listPlaybooks();
      set({ playbooks });
    } catch (err) {
      console.error('Failed to fetch playbooks:', err);
    } finally {
      set({ isLoadingPlaybooks: false });
    }
  },

  fetchCompatible: async (scenarioId: string) => {
    set({ isLoadingPlaybooks: true });
    try {
      const playbooks = await attacksApi.getCompatible(scenarioId);
      set({ playbooks });
    } catch (err) {
      console.error('Failed to fetch compatible playbooks:', err);
    } finally {
      set({ isLoadingPlaybooks: false });
    }
  },

  selectPlaybook: async (playbookId: string) => {
    set({ isLoadingPlaybook: true });
    try {
      const playbook = await attacksApi.getPlaybook(playbookId);
      set({
        selectedPlaybook: playbook,
        playbookConfig: {
          playbook_id: playbookId,
          auto_advance: true,
          start_mode: 'with_deployment',
          intensity: 1.0,
        },
      });
    } catch (err) {
      console.error('Failed to fetch playbook:', err);
    } finally {
      set({ isLoadingPlaybook: false });
    }
  },

  clearSelection: () => {
    set({
      selectedPlaybook: null,
      playbookConfig: null,
    });
    // Don't clear injection status - that's per-deployment and persists
  },

  setConfig: (config: AttackPlaybookConfig) => {
    set({ playbookConfig: config });
  },

  injectAndPoll: async (scenarioId: string) => {
    const config = get().playbookConfig;
    if (!config) return;

    stopInjectionPolling(scenarioId);
    set((state) => ({
      injectionStatus: { ...state.injectionStatus, [scenarioId]: 'injecting' },
      injectionError: { ...state.injectionError, [scenarioId]: null },
    }));

    // Step 1: Send the inject request
    try {
      await attacksApi.injectAttack(scenarioId, config.playbook_id, {
        auto_advance: config.auto_advance,
        start_mode: config.start_mode,
        intensity: config.intensity,
      });
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const errorMsg = typeof detail === 'string' ? detail : 'Injection failed';
      set((state) => ({
        injectionStatus: { ...state.injectionStatus, [scenarioId]: 'failed' },
        injectionError: { ...state.injectionError, [scenarioId]: errorMsg },
      }));
      return;
    }

    // Step 2: POST succeeded — poll for agent confirmation
    set((state) => ({
      injectionStatus: { ...state.injectionStatus, [scenarioId]: 'polling' },
    }));
    const startedAt = Date.now();
    const TIMEOUT_MS = 15_000;
    const POLL_MS = 1_000;

    const timer = setInterval(async () => {
      // Timeout check
      if (Date.now() - startedAt > TIMEOUT_MS) {
        stopInjectionPolling(scenarioId);
        set((state) => ({
          injectionStatus: { ...state.injectionStatus, [scenarioId]: 'failed' },
          injectionError: {
            ...state.injectionError,
            [scenarioId]: 'Injection timed out — agent may not be responding.',
          },
        }));
        return;
      }

      try {
        const result = await attacksApi.getInjectionStatus(scenarioId);

        if (result.status === 'confirmed') {
          stopInjectionPolling(scenarioId);
          set((state) => ({
            injectionStatus: { ...state.injectionStatus, [scenarioId]: 'confirmed' },
          }));
        } else if (result.status === 'failed') {
          stopInjectionPolling(scenarioId);
          set((state) => ({
            injectionStatus: { ...state.injectionStatus, [scenarioId]: 'failed' },
            injectionError: {
              ...state.injectionError,
              [scenarioId]: result.message || 'Agent rejected injection',
            },
          }));
        }
        // 'pending' → keep polling
      } catch {
        // Network error during poll — keep trying
      }
    }, POLL_MS);

    _injectionPollTimers.set(scenarioId, timer);
  },

  resetInjection: (scenarioId: string) => {
    stopInjectionPolling(scenarioId);
    set((state) => ({
      injectionStatus: { ...state.injectionStatus, [scenarioId]: 'idle' },
      injectionError: { ...state.injectionError, [scenarioId]: null },
    }));
  },

  startAttack: async (scenarioId: string) => {
    const config = get().playbookConfig;
    if (!config) return;
    try {
      await attacksApi.startAttack(scenarioId, config.playbook_id);
    } catch (err) {
      console.error('Failed to start attack:', err);
    }
  },

  stopAttack: async (scenarioId: string) => {
    try {
      await attacksApi.stopAttack(scenarioId);
    } catch (err) {
      console.error('Failed to stop attack:', err);
    }
  },

  advanceStage: async (scenarioId: string) => {
    try {
      await attacksApi.advanceStage(scenarioId);
    } catch (err) {
      console.error('Failed to advance stage:', err);
    }
  },

  togglePause: async (scenarioId: string, isPaused: boolean) => {
    try {
      await attacksApi.pauseAttack(scenarioId, !isPaused);
    } catch (err) {
      console.error('Failed to toggle pause:', err);
    }
  },

  attackReports: {},
  isFetchingReport: {},
  fetchAttackReport: async (scenarioId: string) => {
    set((s) => ({
      isFetchingReport: { ...s.isFetchingReport, [scenarioId]: true },
    }));
    try {
      const response = await attacksApi.getReport(scenarioId);
      set((s) => ({
        attackReports: { ...s.attackReports, [scenarioId]: response },
      }));
    } catch (err) {
      console.error('Failed to fetch attack report:', err);
    } finally {
      set((s) => ({
        isFetchingReport: { ...s.isFetchingReport, [scenarioId]: false },
      }));
    }
  },
}));
