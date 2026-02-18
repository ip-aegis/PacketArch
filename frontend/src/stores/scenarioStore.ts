/**
 * Scenario state management with Zustand
 * Manages the current scenario being edited in the canvas
 */

import { create } from 'zustand';
import type {
  ScenarioDevice,
  ScenarioFlow,
  ScenarioZone,
  ScenarioConduit,
  Phase,
  VerticalType,
} from '../types';

// IP range info from scenario's addressing_config
interface IPRangeInfo {
  cidr: string;         // e.g., "10.1.0.0/16"
  rangeIndex: number;   // e.g., 1-254
  autoAssignEnabled: boolean;
}

interface ScenarioState {
  // Scenario metadata
  id: string | null;
  name: string;
  description: string;
  vertical?: VerticalType;
  totalDurationMs: number;

  // IP range info
  ipRange: IPRangeInfo | null;

  // Scenario data using Record for O(1) lookup
  devices: Record<string, ScenarioDevice>;
  flows: Record<string, ScenarioFlow>;
  zones: Record<string, ScenarioZone>;
  conduits: Record<string, ScenarioConduit>;
  phases: Phase[];

  // State flags
  isDirty: boolean;
  isLoading: boolean;

  // Device actions
  addDevice: (device: ScenarioDevice) => void;
  updateDevice: (id: string, updates: Partial<ScenarioDevice>) => void;
  removeDevice: (id: string) => void;
  moveDevice: (id: string, position: { x: number; y: number }) => void;

  // Flow actions
  addFlow: (flow: ScenarioFlow) => void;
  updateFlow: (id: string, updates: Partial<ScenarioFlow>) => void;
  removeFlow: (id: string) => void;

  // Zone actions
  addZone: (zone: ScenarioZone) => void;
  updateZone: (id: string, updates: Partial<ScenarioZone>) => void;
  removeZone: (id: string) => void;

  // Conduit actions
  addConduit: (conduit: ScenarioConduit) => void;
  updateConduit: (id: string, updates: Partial<ScenarioConduit>) => void;
  removeConduit: (id: string) => void;

  // Bulk actions for layout
  bulkMoveDevices: (positions: Record<string, { x: number; y: number }>) => void;
  bulkUpdateZones: (updates: Record<string, { position?: { x: number; y: number }; dimensions?: { width: number; height: number } }>) => void;

  // Phase actions
  addPhase: (phase: Phase) => void;
  updatePhase: (id: string, updates: Partial<Phase>) => void;
  removePhase: (id: string) => void;

  // Scenario actions
  loadScenario: (scenario: {
    id: string;
    name: string;
    description?: string;
    vertical?: VerticalType;
    totalDurationMs: number;
    devices: Record<string, ScenarioDevice>;
    flows: Record<string, ScenarioFlow>;
    zones: Record<string, ScenarioZone>;
    conduits?: Record<string, ScenarioConduit>;
    phases: Phase[];
    addressingConfig?: {
      ip_range?: string;
      range_index?: number;
      auto_assign_enabled?: boolean;
    } | null;
  }) => void;
  resetScenario: () => void;
  setMetadata: (metadata: { name?: string; description?: string; vertical?: VerticalType; totalDurationMs?: number }) => void;
  setIPRange: (ipRange: IPRangeInfo | null) => void;
  setDirty: (dirty: boolean) => void;
  setLoading: (loading: boolean) => void;
}

const DEFAULT_PHASES: Phase[] = [
  {
    id: 'phase-startup',
    name: 'startup',
    displayName: 'Startup',
    startOffsetMs: 0,
    durationMs: 30000,
    intensity: 0.7,
    color: '#52c41a',
  },
  {
    id: 'phase-steady-state',
    name: 'steady-state',
    displayName: 'Steady State',
    startOffsetMs: 30000,
    durationMs: 300000,
    intensity: 1.0,
    color: '#1890ff',
  },
  {
    id: 'phase-shutdown',
    name: 'shutdown',
    displayName: 'Shutdown',
    startOffsetMs: 330000,
    durationMs: 30000,
    intensity: 0.5,
    color: '#fa8c16',
  },
];

export const useScenarioStore = create<ScenarioState>((set) => ({
  // Initial state
  id: null,
  name: 'Untitled Scenario',
  description: '',
  vertical: undefined,
  totalDurationMs: 360000, // 6 minutes default
  ipRange: null,
  devices: {},
  flows: {},
  zones: {},
  conduits: {},
  phases: DEFAULT_PHASES,
  isDirty: false,
  isLoading: false,

  // Device actions
  addDevice: (device) =>
    set((state) => ({
      devices: { ...state.devices, [device.id]: device },
      isDirty: true,
    })),

  updateDevice: (id, updates) =>
    set((state) => {
      const device = state.devices[id];
      if (!device) return state;

      return {
        devices: {
          ...state.devices,
          [id]: { ...device, ...updates },
        },
        isDirty: true,
      };
    }),

  removeDevice: (id) =>
    set((state) => {
      const { [id]: removed, ...remainingDevices } = state.devices;

      // Also remove flows connected to this device
      const remainingFlows = Object.fromEntries(
        Object.entries(state.flows).filter(
          ([, flow]) => flow.sourceDeviceId !== id && flow.targetDeviceId !== id
        )
      );

      // Remove device from zones
      const updatedZones = Object.fromEntries(
        Object.entries(state.zones).map(([zoneId, zone]) => [
          zoneId,
          {
            ...zone,
            deviceIds: zone.deviceIds.filter((deviceId) => deviceId !== id),
          },
        ])
      );

      return {
        devices: remainingDevices,
        flows: remainingFlows,
        zones: updatedZones,
        isDirty: true,
      };
    }),

  moveDevice: (id, position) =>
    set((state) => {
      const device = state.devices[id];
      if (!device) return state;

      return {
        devices: {
          ...state.devices,
          [id]: { ...device, position },
        },
        isDirty: true,
      };
    }),

  // Flow actions
  addFlow: (flow) =>
    set((state) => ({
      flows: { ...state.flows, [flow.id]: flow },
      isDirty: true,
    })),

  updateFlow: (id, updates) =>
    set((state) => {
      const flow = state.flows[id];
      if (!flow) return state;

      return {
        flows: {
          ...state.flows,
          [id]: { ...flow, ...updates },
        },
        isDirty: true,
      };
    }),

  removeFlow: (id) =>
    set((state) => {
      const { [id]: removed, ...remainingFlows } = state.flows;
      return {
        flows: remainingFlows,
        isDirty: true,
      };
    }),

  // Zone actions
  addZone: (zone) =>
    set((state) => ({
      zones: { ...state.zones, [zone.id]: zone },
      isDirty: true,
    })),

  updateZone: (id, updates) =>
    set((state) => {
      const zone = state.zones[id];
      if (!zone) return state;

      return {
        zones: {
          ...state.zones,
          [id]: { ...zone, ...updates },
        },
        isDirty: true,
      };
    }),

  removeZone: (id) =>
    set((state) => {
      const { [id]: removed, ...remainingZones } = state.zones;

      // Remove zone reference from devices
      const updatedDevices = Object.fromEntries(
        Object.entries(state.devices).map(([deviceId, device]) => [
          deviceId,
          device.zoneId === id ? { ...device, zoneId: undefined } : device,
        ])
      );

      // Remove conduits referencing this zone
      const remainingConduits = Object.fromEntries(
        Object.entries(state.conduits).filter(
          ([, conduit]) => conduit.sourceZoneId !== id && conduit.targetZoneId !== id
        )
      );

      return {
        zones: remainingZones,
        devices: updatedDevices,
        conduits: remainingConduits,
        isDirty: true,
      };
    }),

  // Conduit actions
  addConduit: (conduit) =>
    set((state) => ({
      conduits: { ...state.conduits, [conduit.id]: conduit },
      isDirty: true,
    })),

  updateConduit: (id, updates) =>
    set((state) => {
      const conduit = state.conduits[id];
      if (!conduit) return state;

      return {
        conduits: {
          ...state.conduits,
          [id]: { ...conduit, ...updates },
        },
        isDirty: true,
      };
    }),

  removeConduit: (id) =>
    set((state) => {
      const { [id]: removed, ...remainingConduits } = state.conduits;
      return {
        conduits: remainingConduits,
        isDirty: true,
      };
    }),

  // Bulk actions for layout
  bulkMoveDevices: (positions) =>
    set((state) => {
      const updatedDevices = { ...state.devices };
      for (const [id, position] of Object.entries(positions)) {
        if (updatedDevices[id]) {
          updatedDevices[id] = { ...updatedDevices[id], position };
        }
      }
      return { devices: updatedDevices, isDirty: true };
    }),

  bulkUpdateZones: (updates) =>
    set((state) => {
      const updatedZones = { ...state.zones };
      for (const [id, update] of Object.entries(updates)) {
        if (updatedZones[id]) {
          updatedZones[id] = {
            ...updatedZones[id],
            ...(update.position && { position: update.position }),
            ...(update.dimensions && { dimensions: update.dimensions }),
          };
        }
      }
      return { zones: updatedZones, isDirty: true };
    }),

  // Phase actions
  addPhase: (phase) =>
    set((state) => ({
      phases: [...state.phases, phase],
      isDirty: true,
    })),

  updatePhase: (id, updates) =>
    set((state) => ({
      phases: state.phases.map((phase) =>
        phase.id === id ? { ...phase, ...updates } : phase
      ),
      isDirty: true,
    })),

  removePhase: (id) =>
    set((state) => ({
      phases: state.phases.filter((phase) => phase.id !== id),
      isDirty: true,
    })),

  // Scenario actions
  loadScenario: (scenario) => {
    // Extract IP range info from addressingConfig
    const addressingConfig = scenario.addressingConfig;
    let ipRange: IPRangeInfo | null = null;
    if (addressingConfig?.ip_range && addressingConfig?.range_index !== undefined) {
      ipRange = {
        cidr: addressingConfig.ip_range,
        rangeIndex: addressingConfig.range_index,
        autoAssignEnabled: addressingConfig.auto_assign_enabled ?? true,
      };
    }

    set({
      id: scenario.id,
      name: scenario.name,
      description: scenario.description || '',
      vertical: scenario.vertical,
      totalDurationMs: scenario.totalDurationMs,
      ipRange,
      devices: scenario.devices,
      flows: scenario.flows,
      zones: scenario.zones,
      conduits: scenario.conduits || {},
      phases: scenario.phases.length > 0 ? scenario.phases : DEFAULT_PHASES,
      isDirty: false,
      isLoading: false,
    });
  },

  resetScenario: () =>
    set({
      id: null,
      name: 'Untitled Scenario',
      description: '',
      vertical: undefined,
      totalDurationMs: 360000,
      ipRange: null,
      devices: {},
      flows: {},
      zones: {},
      conduits: {},
      phases: DEFAULT_PHASES,
      isDirty: false,
      isLoading: false,
    }),

  setMetadata: (metadata) =>
    set(() => ({
      ...metadata,
      isDirty: true,
    })),

  setIPRange: (ipRange) => set({ ipRange }),
  setDirty: (dirty) => set({ isDirty: dirty }),
  setLoading: (loading) => set({ isLoading: loading }),
}));

// Selector helpers for performance — select only the needed slice to prevent
// unnecessary re-renders when unrelated parts of the store change.
export const useDeviceList = () =>
  useScenarioStore((s) => Object.values(s.devices));
export const useFlowList = () =>
  useScenarioStore((s) => Object.values(s.flows));
export const useZoneList = () =>
  useScenarioStore((s) => Object.values(s.zones));
export const useConduitList = () =>
  useScenarioStore((s) => Object.values(s.conduits));
export const useDeviceCount = () =>
  useScenarioStore((s) => Object.keys(s.devices).length);
export const useFlowCount = () =>
  useScenarioStore((s) => Object.keys(s.flows).length);
export const useConduitCount = () =>
  useScenarioStore((s) => Object.keys(s.conduits).length);
export const useScenarioName = () =>
  useScenarioStore((s) => s.name);
export const useScenarioId = () =>
  useScenarioStore((s) => s.id);
export const useScenarioVertical = () =>
  useScenarioStore((s) => s.vertical);
export const useScenarioIsDirty = () =>
  useScenarioStore((s) => s.isDirty);
export const useScenarioIsLoading = () =>
  useScenarioStore((s) => s.isLoading);
export const useScenarioPhases = () =>
  useScenarioStore((s) => s.phases);

export default useScenarioStore;
