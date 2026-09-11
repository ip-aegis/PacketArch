/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Cyber Vision state management with Zustand.
 *
 * PacketArch can talk to several Cyber Vision Centers. `selectedCenterId` is
 * the center the Cyber Vision page is looking at (null = the default center);
 * every data fetch targets it, and switching centers clears the cached data so
 * one center's devices are never shown under another's name.
 */

import { create } from 'zustand';
import {
  cyberVisionApi,
  type CVDevice,
  type CVVulnerability,
  type CVComparisonResult,
  type CVCenter,
  type CVCenterCreate,
  type CVCenterUpdate,
  type CVConnectionStatus,
  type CVTestConnectionRequest,
  type CVPreset,
  type CVEnrichmentRequest,
  type CVEnrichmentResult,
  type DuplicateMacAnalysisResponse,
} from '../api/cyberVision';
import { extractErrorMessage } from '../utils/errorUtils';

interface CyberVisionState {
  // Centers
  centers: CVCenter[];
  defaultCenterId: string | null;
  centersLoaded: boolean;
  selectedCenterId: string | null; // null = the default center

  // Connection state (of the selected center)
  connectionStatus: CVConnectionStatus | null;

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

  // MAC analysis state
  macAnalysis: DuplicateMacAnalysisResponse | null;
  isLoadingMacAnalysis: boolean;

  // Actions
  fetchCenters: () => Promise<void>;
  selectCenter: (centerId: string | null) => void;
  createCenter: (body: CVCenterCreate) => Promise<CVCenter>;
  updateCenter: (centerId: string, body: CVCenterUpdate) => Promise<CVCenter>;
  makeDefaultCenter: (centerId: string) => Promise<void>;
  deleteCenter: (centerId: string) => Promise<void>;
  fetchStatus: () => Promise<void>;
  testConnection: (request: CVTestConnectionRequest) => Promise<{ success: boolean; message: string }>;
  fetchDevices: (params?: { limit?: number; offset?: number; search?: string }) => Promise<void>;
  fetchVulnerabilities: (params?: { limit?: number; offset?: number; severity?: string }) => Promise<void>;
  fetchPresets: () => Promise<void>;
  compareScenario: (scenarioId: string, presetId?: string) => Promise<void>;
  enrichDevices: (request: CVEnrichmentRequest) => Promise<CVEnrichmentResult | null>;
  analyzeDuplicateMacs: (presetId?: string) => Promise<void>;
  clearError: () => void;
  clearComparison: () => void;
  clearEnrichmentResult: () => void;
  clearMacAnalysis: () => void;
}

// Everything fetched FROM a center — reset whenever the selected center changes.
const centerData = {
  connectionStatus: null,
  devices: [] as CVDevice[],
  vulnerabilities: [] as CVVulnerability[],
  presets: [] as CVPreset[],
  comparisonResult: null,
  enrichmentResult: null,
  enrichedSinceCompare: false,
  macAnalysis: null,
};

let centersRequest: Promise<void> | null = null;

export const useCyberVisionStore = create<CyberVisionState>()((set, get) => {
  const loadCenters = async () => {
    try {
      const list = await cyberVisionApi.listCenters();
      const { selectedCenterId } = get();
      // A selected center that was deleted falls back to the default.
      const stillThere = list.centers.some((c) => c.id === selectedCenterId);
      set({
        centers: list.centers,
        defaultCenterId: list.default_center_id,
        centersLoaded: true,
        ...(selectedCenterId && !stillThere ? { selectedCenterId: null, ...centerData } : {}),
      });
    } catch (error: unknown) {
      set({ error: extractErrorMessage(error, 'Failed to load Cyber Vision Centers'), centersLoaded: true });
    }
  };

  return {
    // Initial state
    centers: [],
    defaultCenterId: null,
    centersLoaded: false,
    selectedCenterId: null,
    connectionStatus: null,
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
    macAnalysis: null,
    isLoadingMacAnalysis: false,

    fetchCenters: () => {
      // Many components (pickers, badges) ask at mount; share one request.
      if (!centersRequest) {
        centersRequest = loadCenters().finally(() => {
          centersRequest = null;
        });
      }
      return centersRequest;
    },

    selectCenter: (centerId) => {
      if (centerId === get().selectedCenterId) return;
      set({ selectedCenterId: centerId, ...centerData, error: null });
    },

    createCenter: async (body) => {
      const center = await cyberVisionApi.createCenter(body);
      await get().fetchCenters();
      return center;
    },

    updateCenter: async (centerId, body) => {
      const center = await cyberVisionApi.updateCenter(centerId, body);
      await get().fetchCenters();
      return center;
    },

    makeDefaultCenter: async (centerId) => {
      await cyberVisionApi.makeDefaultCenter(centerId);
      await get().fetchCenters();
    },

    deleteCenter: async (centerId) => {
      await cyberVisionApi.deleteCenter(centerId);
      await get().fetchCenters();
    },

    fetchStatus: async () => {
      const centerId = get().selectedCenterId;
      set({ isLoading: true, error: null });
      try {
        const status = await cyberVisionApi.getStatus(centerId);
        if (get().selectedCenterId !== centerId) return; // switched mid-flight
        set({ connectionStatus: status, isLoading: false });
      } catch (error: unknown) {
        if (get().selectedCenterId !== centerId) return;
        const message = extractErrorMessage(error, 'Failed to fetch CV status');
        set({
          error: message,
          isLoading: false,
          connectionStatus: { connected: false, message, version: null, center_name: null }
        });
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
        const response = await cyberVisionApi.getDevices(params, get().selectedCenterId);
        set({ devices: response.items, isLoadingDevices: false });
      } catch (error: unknown) {
        const message = extractErrorMessage(error, 'Failed to fetch CV devices');
        set({ error: message, isLoadingDevices: false });
      }
    },

    fetchVulnerabilities: async (params) => {
      set({ isLoadingVulnerabilities: true, error: null });
      try {
        const response = await cyberVisionApi.getVulnerabilities(params, get().selectedCenterId);
        set({ vulnerabilities: response.items, isLoadingVulnerabilities: false });
      } catch (error: unknown) {
        const message = extractErrorMessage(error, 'Failed to fetch CV vulnerabilities');
        set({ error: message, isLoadingVulnerabilities: false });
      }
    },

    fetchPresets: async () => {
      set({ isLoadingPresets: true, error: null });
      try {
        const response = await cyberVisionApi.getPresets(get().selectedCenterId);
        set({ presets: response.items, isLoadingPresets: false });
      } catch (error: unknown) {
        const message = extractErrorMessage(error, 'Failed to fetch CV presets');
        set({ error: message, isLoadingPresets: false });
      }
    },

    compareScenario: async (scenarioId: string, presetId?: string) => {
      set({ isComparing: true, error: null, comparisonResult: null, enrichedSinceCompare: false });
      try {
        const result = await cyberVisionApi.compareScenario(scenarioId, presetId, get().selectedCenterId);
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
        const result = await cyberVisionApi.enrichDevices(request, get().selectedCenterId);
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

    analyzeDuplicateMacs: async (presetId?: string) => {
      set({ isLoadingMacAnalysis: true, error: null, macAnalysis: null });
      try {
        const result = await cyberVisionApi.analyzeDuplicateMacs(presetId, get().selectedCenterId);
        set({ macAnalysis: result, isLoadingMacAnalysis: false });
      } catch (error: unknown) {
        const message = extractErrorMessage(error, 'Failed to analyze duplicate MACs');
        set({ error: message, isLoadingMacAnalysis: false });
      }
    },

    clearMacAnalysis: () => {
      set({ macAnalysis: null });
    },
  };
});

export default useCyberVisionStore;
