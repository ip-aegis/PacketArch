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
  AttackState,
} from '../types/attackPlaybook';

interface AttackStore {
  // Playbook library
  playbooks: AttackPlaybookSummary[];
  isLoadingPlaybooks: boolean;

  // Selected playbook (full detail)
  selectedPlaybook: AttackPlaybook | null;
  isLoadingPlaybook: boolean;

  // Configuration
  playbookConfig: AttackPlaybookConfig | null;

  // Runtime state (live from dashboard polling)
  attackState: AttackState | null;

  // Actions
  fetchPlaybooks: () => Promise<void>;
  fetchCompatible: (scenarioId: string) => Promise<void>;
  selectPlaybook: (playbookId: string) => Promise<void>;
  clearSelection: () => void;
  setConfig: (config: AttackPlaybookConfig) => void;

  // Runtime controls
  startAttack: (scenarioId: string) => Promise<void>;
  stopAttack: (scenarioId: string) => Promise<void>;
  advanceStage: (scenarioId: string) => Promise<void>;
  togglePause: (scenarioId: string) => Promise<void>;

  // State updates (called from dashboard polling)
  setAttackState: (state: AttackState | null) => void;
}

export const useAttackStore = create<AttackStore>((set, get) => ({
  playbooks: [],
  isLoadingPlaybooks: false,
  selectedPlaybook: null,
  isLoadingPlaybook: false,
  playbookConfig: null,
  attackState: null,

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
    set({ selectedPlaybook: null, playbookConfig: null });
  },

  setConfig: (config: AttackPlaybookConfig) => {
    set({ playbookConfig: config });
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

  togglePause: async (scenarioId: string) => {
    const state = get().attackState;
    if (!state) return;
    try {
      await attacksApi.pauseAttack(scenarioId, !state.is_paused);
    } catch (err) {
      console.error('Failed to toggle pause:', err);
    }
  },

  setAttackState: (state) => {
    set({ attackState: state });
  },
}));
