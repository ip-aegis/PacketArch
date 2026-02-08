/**
 * Cyber Vision state management with Zustand
 */

import { create } from 'zustand';
import {
  cyberVisionApi,
  type CVDevice,
  type CVVulnerability,
  type CVComparisonResult,
  type CVConnectionStatus,
  type CVSettings,
  type CVSettingsUpdate,
  type CVTestConnectionRequest,
  type CVPreset,
  type CVEnrichmentRequest,
  type CVEnrichmentResult,
} from '../api/cyberVision';
import { extractErrorMessage } from '../utils/errorUtils';

interface CyberVisionState {
  // Connection state
  connectionStatus: CVConnectionStatus | null;
  settings: CVSettings | null;

  // Data
  devices: CVDevice[];
  vulnerabilities: CVVulnerability[];
  presets: CVPreset[];
  comparisonResult: CVComparisonResult | null;

  // UI state
  isLoading: boolean;
  isLoadingDevices: boolean;
  isLoadingVulnerabilities: boolean;
  isLoadingPresets: boolean;
  isComparing: boolean;
  isTesting: boolean;
  isEnriching: boolean;
  enrichmentResult: CVEnrichmentResult | null;
  enrichedSinceCompare: boolean;
  error: string | null;

  // Actions
  fetchStatus: () => Promise<void>;
  fetchSettings: () => Promise<void>;
  updateSettings: (settings: CVSettingsUpdate) => Promise<void>;
  testConnection: (request: CVTestConnectionRequest) => Promise<{ success: boolean; message: string }>;
  fetchDevices: (params?: { limit?: number; offset?: number; search?: string }) => Promise<void>;
  fetchVulnerabilities: (params?: { limit?: number; offset?: number; severity?: string }) => Promise<void>;
  fetchPresets: () => Promise<void>;
  compareScenario: (scenarioId: string, presetId?: string) => Promise<void>;
  enrichDevices: (request: CVEnrichmentRequest) => Promise<CVEnrichmentResult | null>;
  clearError: () => void;
  clearComparison: () => void;
  clearEnrichmentResult: () => void;
}

export const useCyberVisionStore = create<CyberVisionState>()((set, get) => ({
  // Initial state
  connectionStatus: null,
  settings: null,
  devices: [],
  vulnerabilities: [],
  presets: [],
  comparisonResult: null,
  isLoading: false,
  isLoadingDevices: false,
  isLoadingVulnerabilities: false,
  isLoadingPresets: false,
  isComparing: false,
  isTesting: false,
  isEnriching: false,
  enrichmentResult: null,
  enrichedSinceCompare: false,
  error: null,

  fetchStatus: async () => {
    set({ isLoading: true, error: null });
    try {
      const status = await cyberVisionApi.getStatus();
      set({ connectionStatus: status, isLoading: false });
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Failed to fetch CV status');
      set({
        error: message,
        isLoading: false,
        connectionStatus: { connected: false, message, version: null, center_name: null }
      });
    }
  },

  fetchSettings: async () => {
    set({ isLoading: true, error: null });
    try {
      const settings = await cyberVisionApi.getSettings();
      set({ settings, isLoading: false });
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Failed to fetch CV settings');
      set({ error: message, isLoading: false });
    }
  },

  updateSettings: async (settingsUpdate: CVSettingsUpdate) => {
    set({ isLoading: true, error: null });
    try {
      const settings = await cyberVisionApi.updateSettings(settingsUpdate);
      set({ settings, isLoading: false });
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Failed to update CV settings');
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  testConnection: async (request: CVTestConnectionRequest) => {
    set({ isTesting: true, error: null });
    try {
      const result = await cyberVisionApi.testConnection(request);
      set({ isTesting: false });
      return result;
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Connection test failed');
      set({ isTesting: false });
      return { success: false, message };
    }
  },

  fetchDevices: async (params) => {
    set({ isLoadingDevices: true, error: null });
    try {
      const response = await cyberVisionApi.getDevices(params);
      set({ devices: response.items, isLoadingDevices: false });
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Failed to fetch CV devices');
      set({ error: message, isLoadingDevices: false });
    }
  },

  fetchVulnerabilities: async (params) => {
    set({ isLoadingVulnerabilities: true, error: null });
    try {
      const response = await cyberVisionApi.getVulnerabilities(params);
      set({ vulnerabilities: response.items, isLoadingVulnerabilities: false });
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Failed to fetch CV vulnerabilities');
      set({ error: message, isLoadingVulnerabilities: false });
    }
  },

  fetchPresets: async () => {
    set({ isLoadingPresets: true, error: null });
    try {
      const response = await cyberVisionApi.getPresets();
      set({ presets: response.items, isLoadingPresets: false });
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Failed to fetch CV presets');
      set({ error: message, isLoadingPresets: false });
    }
  },

  compareScenario: async (scenarioId: string, presetId?: string) => {
    set({ isComparing: true, error: null, comparisonResult: null, enrichedSinceCompare: false });
    try {
      const result = await cyberVisionApi.compareScenario(scenarioId, presetId);
      set({ comparisonResult: result, isComparing: false });
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Failed to compare scenario');
      set({ error: message, isComparing: false });
    }
  },

  clearError: () => {
    set({ error: null });
  },

  clearComparison: () => {
    set({ comparisonResult: null });
  },

  enrichDevices: async (request: CVEnrichmentRequest) => {
    set({ isEnriching: true, error: null, enrichmentResult: null });
    try {
      const result = await cyberVisionApi.enrichDevices(request);
      set({ enrichmentResult: result, isEnriching: false, enrichedSinceCompare: true });
      return result;
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Failed to enrich CV devices');
      set({ error: message, isEnriching: false });
      return null;
    }
  },

  clearEnrichmentResult: () => {
    set({ enrichmentResult: null });
  },
}));

export default useCyberVisionStore;
