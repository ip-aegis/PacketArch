/**
 * Guided Scenario Builder wizard state management.
 *
 * 6-step flow: vertical → template → review devices → customize → review flows → finalize.
 */

import { create } from 'zustand';
import { templatesApi } from '../api/templates';
import { scenariosApi } from '../api/scenarios';
import type { TemplateSummary, TemplateDetail } from '../api/templates';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type WizardStep =
  | 'vertical'
  | 'template'
  | 'review-devices'
  | 'customize'
  | 'review-flows'
  | 'finalize';

export interface TemplateDevicePreview {
  uid: string;
  type: string;
  name: string;
  vendor: string | undefined;
  fingerprintModel: string | undefined;
  zone: string | undefined;
  protocols: string[];
  role: string | undefined;
  cveIds: string[];
}

export interface DeviceCustomization {
  name?: string;
  vendor?: string;
  fingerprintModel?: string;
}

interface GuidedBuilderState {
  currentStep: WizardStep;

  // Step 1
  selectedVertical: string | null;

  // Step 2
  selectedTemplate: TemplateSummary | null;
  templateDetail: TemplateDetail | null;
  templateDetailLoading: boolean;
  templateDetailError: string | null;

  // Steps 3 & 4
  expandedDevices: TemplateDevicePreview[];
  customizations: Record<string, DeviceCustomization>;

  // Step 6
  scenarioName: string;
  description: string;
  phasePreset: string;
  useAINaming: boolean;
  processContext: string;

  // Creation
  isCreating: boolean;
  createError: string | null;

  // Actions
  setSelectedVertical: (v: string | null) => void;
  setSelectedTemplate: (t: TemplateSummary | null) => void;
  fetchTemplateDetail: (vertical: string, name: string) => Promise<void>;
  setCustomization: (uid: string, changes: DeviceCustomization) => void;
  applyBulkRename: (prefix: string) => void;
  setScenarioName: (name: string) => void;
  setDescription: (desc: string) => void;
  setPhasePreset: (preset: string) => void;
  setUseAINaming: (v: boolean) => void;
  setProcessContext: (ctx: string) => void;
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (step: WizardStep) => void;
  canProceed: () => boolean;
  createScenario: () => Promise<string | null>;
  reset: () => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STEP_ORDER: WizardStep[] = [
  'vertical',
  'template',
  'review-devices',
  'customize',
  'review-flows',
  'finalize',
];

const initialState = {
  currentStep: 'vertical' as WizardStep,
  selectedVertical: null as string | null,
  selectedTemplate: null as TemplateSummary | null,
  templateDetail: null as TemplateDetail | null,
  templateDetailLoading: false,
  templateDetailError: null as string | null,
  expandedDevices: [] as TemplateDevicePreview[],
  customizations: {} as Record<string, DeviceCustomization>,
  scenarioName: '',
  description: '',
  phasePreset: 'standard',
  useAINaming: false,
  processContext: '',
  isCreating: false,
  createError: null as string | null,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Expand template device specs (which have count > 1) into individual rows. */
function expandDevices(detail: TemplateDetail): TemplateDevicePreview[] {
  const expanded: TemplateDevicePreview[] = [];
  let index = 0;

  for (const spec of detail.devices) {
    const count = spec.count || 1;
    for (let i = 0; i < count; i++) {
      index++;
      const padded = String(index).padStart(3, '0');

      let name: string;
      if (spec.name) {
        name = count > 1 ? `${spec.name}_${i + 1}` : spec.name;
      } else if (spec.name_pattern) {
        name = spec.name_pattern
          .replace('{n}', String(i + 1))
          .replace('{n:02d}', String(i + 1).padStart(2, '0'))
          .replace('{n:03d}', String(i + 1).padStart(3, '0'));
      } else {
        name = `${spec.type}-${padded}`;
      }

      expanded.push({
        uid: `td_${padded}`,
        type: spec.type,
        name,
        vendor: spec.vendor,
        fingerprintModel: spec.fingerprint_model,
        zone: spec.zone,
        protocols: spec.protocols || [],
        role: spec.role,
        cveIds: spec.cve_ids || [],
      });
    }
  }

  return expanded;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useGuidedBuilderStore = create<GuidedBuilderState>((set, get) => ({
  ...initialState,

  setSelectedVertical: (v) =>
    set({
      selectedVertical: v,
      selectedTemplate: null,
      templateDetail: null,
      templateDetailError: null,
      expandedDevices: [],
      customizations: {},
      scenarioName: '',
      description: '',
    }),

  setSelectedTemplate: (t) => set({ selectedTemplate: t }),

  fetchTemplateDetail: async (vertical, name) => {
    set({ templateDetailLoading: true, templateDetailError: null });
    try {
      const detail = await templatesApi.getDetail(vertical, name);
      const expanded = expandDevices(detail);

      const today = new Date().toISOString().split('T')[0];
      const defaultName = `${detail.name} - ${today}`;

      set({
        templateDetail: detail,
        expandedDevices: expanded,
        templateDetailLoading: false,
        scenarioName: defaultName,
        description: detail.description || '',
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load template details';
      set({ templateDetailError: message, templateDetailLoading: false });
    }
  },

  setCustomization: (uid, changes) => {
    const { customizations } = get();
    set({
      customizations: {
        ...customizations,
        [uid]: { ...customizations[uid], ...changes },
      },
    });
  },

  applyBulkRename: (prefix) => {
    const { expandedDevices } = get();
    const newCustomizations: Record<string, DeviceCustomization> = {};
    expandedDevices.forEach((d, i) => {
      const existing = get().customizations[d.uid];
      newCustomizations[d.uid] = {
        ...existing,
        name: `${prefix}_${String(i + 1).padStart(3, '0')}`,
      };
    });
    set({ customizations: newCustomizations });
  },

  setScenarioName: (name) => set({ scenarioName: name }),
  setDescription: (desc) => set({ description: desc }),
  setPhasePreset: (preset) => set({ phasePreset: preset }),
  setUseAINaming: (v) => set({ useAINaming: v }),
  setProcessContext: (ctx) => set({ processContext: ctx }),

  nextStep: () => {
    const { currentStep } = get();
    const idx = STEP_ORDER.indexOf(currentStep);
    if (idx < STEP_ORDER.length - 1) {
      set({ currentStep: STEP_ORDER[idx + 1] });
    }
  },

  prevStep: () => {
    const { currentStep } = get();
    const idx = STEP_ORDER.indexOf(currentStep);
    if (idx > 0) {
      set({ currentStep: STEP_ORDER[idx - 1] });
    }
  },

  goToStep: (step) => set({ currentStep: step }),

  canProceed: () => {
    const state = get();
    switch (state.currentStep) {
      case 'vertical':
        return state.selectedVertical !== null;
      case 'template':
        return state.selectedTemplate !== null;
      case 'review-devices':
        return state.expandedDevices.length > 0 && !state.templateDetailLoading;
      case 'customize':
        return true; // Customization is optional
      case 'review-flows':
        return true; // Informational
      case 'finalize':
        return state.scenarioName.trim().length > 0 && !state.isCreating;
      default:
        return false;
    }
  },

  createScenario: async () => {
    const state = get();
    if (!state.selectedTemplate) return null;

    set({ isCreating: true, createError: null });

    try {
      // Step 1: Create scenario from template
      const result = await templatesApi.createFromTemplate({
        vertical: state.selectedTemplate.vertical,
        template_name: state.selectedTemplate.name,
        scenario_name: state.scenarioName,
        description: state.description || undefined,
        phase_preset: state.phasePreset,
        auto_assign_addresses: true,
        use_ai_naming: state.useAINaming,
        process_context: state.useAINaming ? state.processContext : undefined,
      });

      const scenarioId = result.scenario_id;

      // Step 2: Apply customizations if any
      const hasCustomizations = Object.keys(state.customizations).length > 0;
      if (hasCustomizations) {
        try {
          const scenario = await scenariosApi.get(scenarioId);
          const definition = { ...scenario.definition } as Record<string, unknown>;
          const devices = { ...(definition.devices as Record<string, Record<string, unknown>>) };

          // Map positional uid (td_001 → device_001, etc.)
          const deviceKeys = Object.keys(devices).sort();
          const sortedUids = state.expandedDevices.map((d) => d.uid);

          for (let i = 0; i < sortedUids.length && i < deviceKeys.length; i++) {
            const uid = sortedUids[i];
            const customization = state.customizations[uid];
            if (!customization) continue;

            const deviceKey = deviceKeys[i];
            const device = { ...devices[deviceKey] } as Record<string, unknown>;

            if (customization.name) {
              device.name = customization.name;
            }
            if (customization.vendor) {
              device.vendor = customization.vendor;
            }
            if (customization.fingerprintModel) {
              const fp = device.vendorFingerprint as Record<string, unknown> | undefined;
              if (fp) {
                device.vendorFingerprint = { ...fp, model: customization.fingerprintModel };
              }
            }

            devices[deviceKey] = device;
          }

          definition.devices = devices;
          await scenariosApi.update(scenarioId, { definition });
        } catch {
          // Customization patch failed but scenario was created — proceed anyway
          console.warn('Failed to apply device customizations, continuing to Studio');
        }
      }

      set({ isCreating: false });
      return scenarioId;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create scenario';
      set({ createError: message, isCreating: false });
      return null;
    }
  },

  reset: () => set(initialState),
}));

export const WIZARD_STEPS: { key: WizardStep; title: string }[] = [
  { key: 'vertical', title: 'Vertical' },
  { key: 'template', title: 'Template' },
  { key: 'review-devices', title: 'Review Devices' },
  { key: 'customize', title: 'Customize' },
  { key: 'review-flows', title: 'Review Flows' },
  { key: 'finalize', title: 'Finalize' },
];

export default useGuidedBuilderStore;
