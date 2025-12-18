/**
 * AI Scenario Creation Wizard state management
 */

import { create } from 'zustand';
import { aiScenarioApi } from '../api/aiScenario';
import type { AIScenarioPreviewResponse } from '../api/aiScenario';

// Available verticals
export const VERTICALS = [
  { id: 'manufacturing', name: 'Manufacturing', description: 'Discrete and process manufacturing' },
  { id: 'water', name: 'Water/Wastewater', description: 'Water treatment and distribution' },
  { id: 'energy', name: 'Energy/Power', description: 'Substations and power distribution' },
  { id: 'oil_gas', name: 'Oil & Gas', description: 'Pipeline and refinery SCADA' },
];

// Available vendors
export const VENDORS = [
  { id: 'rockwell', name: 'Rockwell Automation', aka: 'Allen-Bradley' },
  { id: 'siemens', name: 'Siemens', aka: 'S7/PROFINET' },
  { id: 'schneider', name: 'Schneider Electric', aka: 'Modicon' },
  { id: 'abb', name: 'ABB', aka: 'Drives/Motors' },
  { id: 'honeywell', name: 'Honeywell', aka: 'Experion' },
  { id: 'ge', name: 'GE', aka: 'PACSystems' },
  { id: 'emerson', name: 'Emerson', aka: 'DeltaV' },
];

// Available protocols
export const PROTOCOLS = [
  { id: 'modbus_tcp', name: 'Modbus TCP', description: 'Universal industrial protocol' },
  { id: 'ethernet_ip', name: 'EtherNet/IP', description: 'Rockwell/ODVA protocol' },
  { id: 'profinet', name: 'PROFINET', description: 'Siemens/PROFINET' },
  { id: 'dnp3', name: 'DNP3', description: 'Distributed Network Protocol' },
  { id: 'iec104', name: 'IEC 104', description: 'IEC 60870-5-104' },
  { id: 'opcua', name: 'OPC UA', description: 'Open Platform Communications' },
];

// Device types by vertical
export const DEVICE_TYPES_BY_VERTICAL: Record<string, Array<{ id: string; name: string; description: string; range: [number, number] }>> = {
  manufacturing: [
    { id: 'plc', name: 'PLC', description: 'Programmable Logic Controller', range: [2, 10] },
    { id: 'hmi', name: 'HMI', description: 'Human-Machine Interface', range: [1, 5] },
    { id: 'drive', name: 'Drive', description: 'Variable Frequency Drive', range: [2, 20] },
    { id: 'robot', name: 'Robot', description: 'Industrial Robot Controller', range: [0, 5] },
    { id: 'sensor', name: 'Sensor', description: 'Field Sensors/Transmitters', range: [10, 50] },
  ],
  water: [
    { id: 'rtu', name: 'RTU', description: 'Remote Terminal Unit', range: [5, 20] },
    { id: 'plc', name: 'PLC', description: 'Programmable Logic Controller', range: [1, 5] },
    { id: 'pump_controller', name: 'Pump Controller', description: 'Pump/Motor Controller', range: [3, 15] },
    { id: 'flow_meter', name: 'Flow Meter', description: 'Flow Measurement Device', range: [5, 30] },
    { id: 'level_sensor', name: 'Level Sensor', description: 'Tank Level Sensor', range: [5, 20] },
  ],
  energy: [
    { id: 'rtu', name: 'RTU', description: 'Remote Terminal Unit', range: [10, 50] },
    { id: 'ied', name: 'IED', description: 'Intelligent Electronic Device', range: [5, 30] },
    { id: 'pmu', name: 'PMU', description: 'Phasor Measurement Unit', range: [2, 10] },
    { id: 'meter', name: 'Meter', description: 'Power/Energy Meter', range: [10, 100] },
  ],
  oil_gas: [
    { id: 'rtu', name: 'RTU', description: 'Remote Terminal Unit', range: [10, 100] },
    { id: 'plc', name: 'PLC', description: 'Programmable Logic Controller', range: [2, 10] },
    { id: 'flow_computer', name: 'Flow Computer', description: 'Gas Flow Computer', range: [5, 30] },
    { id: 'compressor_controller', name: 'Compressor Controller', description: 'Compressor Control', range: [2, 10] },
  ],
};

export type WizardStep = 'name-vertical' | 'description' | 'device-count' | 'vendors' | 'protocols' | 'preview';

interface AIScenarioWizardState {
  // Current step
  currentStep: WizardStep;

  // Step 1: Name & Vertical
  scenarioName: string;
  vertical: string | null;

  // Step 2: Description
  description: string;

  // Step 3: Device Count
  letAiDecideDevices: boolean;
  totalDeviceCount: number;
  deviceCounts: Record<string, number>;

  // Step 4: Vendors
  letAiDecideVendors: boolean;
  selectedVendors: string[];

  // Step 5: Protocols
  letAiDecideProtocols: boolean;
  selectedProtocols: string[];

  // Step 6: Preview
  isGenerating: boolean;
  preview: AIScenarioPreviewResponse | null;
  previewError: string | null;

  // Creating scenario
  isCreating: boolean;
  createError: string | null;

  // Actions
  setScenarioName: (name: string) => void;
  setVertical: (vertical: string | null) => void;
  setDescription: (description: string) => void;
  setLetAiDecideDevices: (value: boolean) => void;
  setTotalDeviceCount: (count: number) => void;
  setDeviceCount: (deviceType: string, count: number) => void;
  setLetAiDecideVendors: (value: boolean) => void;
  toggleVendor: (vendorId: string) => void;
  setLetAiDecideProtocols: (value: boolean) => void;
  toggleProtocol: (protocolId: string) => void;

  nextStep: () => void;
  prevStep: () => void;
  goToStep: (step: WizardStep) => void;

  generatePreview: () => Promise<void>;
  createScenario: () => Promise<string | null>;

  reset: () => void;
  canProceed: () => boolean;
}

const STEP_ORDER: WizardStep[] = ['name-vertical', 'description', 'device-count', 'vendors', 'protocols', 'preview'];

const initialState = {
  currentStep: 'name-vertical' as WizardStep,
  scenarioName: '',
  vertical: null as string | null,
  description: '',
  // Device count
  letAiDecideDevices: true,
  totalDeviceCount: 20,
  deviceCounts: {} as Record<string, number>,
  // Vendors
  letAiDecideVendors: true,
  selectedVendors: [] as string[],
  // Protocols
  letAiDecideProtocols: true,
  selectedProtocols: [] as string[],
  // Preview
  isGenerating: false,
  preview: null as AIScenarioPreviewResponse | null,
  previewError: null as string | null,
  isCreating: false,
  createError: null as string | null,
};

export const useAIScenarioWizardStore = create<AIScenarioWizardState>((set, get) => ({
  ...initialState,

  setScenarioName: (name: string) => set({ scenarioName: name }),
  setVertical: (vertical: string | null) => set({ vertical, deviceCounts: {} }),
  setDescription: (description: string) => set({ description }),

  setLetAiDecideDevices: (value: boolean) => set({
    letAiDecideDevices: value,
    deviceCounts: value ? {} : get().deviceCounts,
  }),
  setTotalDeviceCount: (count: number) => set({ totalDeviceCount: count }),
  setDeviceCount: (deviceType: string, count: number) => {
    const state = get();
    set({
      deviceCounts: {
        ...state.deviceCounts,
        [deviceType]: count,
      },
    });
  },

  setLetAiDecideVendors: (value: boolean) => set({
    letAiDecideVendors: value,
    selectedVendors: value ? [] : get().selectedVendors,
  }),

  toggleVendor: (vendorId: string) => {
    const state = get();
    const selected = state.selectedVendors.includes(vendorId)
      ? state.selectedVendors.filter(v => v !== vendorId)
      : [...state.selectedVendors, vendorId];
    set({ selectedVendors: selected });
  },

  setLetAiDecideProtocols: (value: boolean) => set({
    letAiDecideProtocols: value,
    selectedProtocols: value ? [] : get().selectedProtocols,
  }),

  toggleProtocol: (protocolId: string) => {
    const state = get();
    const selected = state.selectedProtocols.includes(protocolId)
      ? state.selectedProtocols.filter(p => p !== protocolId)
      : [...state.selectedProtocols, protocolId];
    set({ selectedProtocols: selected });
  },

  nextStep: () => {
    const state = get();
    const currentIndex = STEP_ORDER.indexOf(state.currentStep);
    if (currentIndex < STEP_ORDER.length - 1) {
      const nextStep = STEP_ORDER[currentIndex + 1];

      // If going to preview step, trigger generation
      if (nextStep === 'preview') {
        set({ currentStep: nextStep });
        get().generatePreview();
      } else {
        set({ currentStep: nextStep });
      }
    }
  },

  prevStep: () => {
    const state = get();
    const currentIndex = STEP_ORDER.indexOf(state.currentStep);
    if (currentIndex > 0) {
      set({ currentStep: STEP_ORDER[currentIndex - 1] });
    }
  },

  goToStep: (step: WizardStep) => set({ currentStep: step }),

  generatePreview: async () => {
    const state = get();

    set({ isGenerating: true, previewError: null });

    try {
      const preview = await aiScenarioApi.generatePreview({
        name: state.scenarioName,
        vertical: state.vertical || 'manufacturing',
        description: state.description,
        vendors: state.letAiDecideVendors ? null : state.selectedVendors,
        protocols: state.letAiDecideProtocols ? null : state.selectedProtocols,
        // Device count parameters
        total_device_count: state.letAiDecideDevices ? state.totalDeviceCount : null,
        device_counts: state.letAiDecideDevices ? null : state.deviceCounts,
      });

      set({ preview, isGenerating: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to generate preview';
      set({ previewError: message, isGenerating: false });
    }
  },

  createScenario: async () => {
    const state = get();
    if (!state.preview) return null;

    set({ isCreating: true, createError: null });

    try {
      const result = await aiScenarioApi.createFromPreview(state.preview.preview_id);
      set({ isCreating: false });
      return result.scenario_id;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create scenario';
      set({ createError: message, isCreating: false });
      return null;
    }
  },

  reset: () => set(initialState),

  canProceed: () => {
    const state = get();

    switch (state.currentStep) {
      case 'name-vertical':
        return state.scenarioName.trim().length > 0 && state.vertical !== null;

      case 'description':
        return state.description.trim().length >= 10;

      case 'device-count': {
        if (state.letAiDecideDevices) {
          return state.totalDeviceCount >= 5 && state.totalDeviceCount <= 100;
        }
        const total = Object.values(state.deviceCounts).reduce((a, b) => a + b, 0);
        return total >= 1 && total <= 100;
      }

      case 'vendors':
        return state.letAiDecideVendors || state.selectedVendors.length > 0;

      case 'protocols':
        return state.letAiDecideProtocols || state.selectedProtocols.length > 0;

      case 'preview':
        return state.preview !== null && !state.isGenerating;

      default:
        return false;
    }
  },
}));

export default useAIScenarioWizardStore;
