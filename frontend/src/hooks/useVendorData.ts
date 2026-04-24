/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Custom hook for fetching vendor, model, and firmware data.
 *
 * Encapsulates the repeated pattern of:
 *   1. Fetch the vendor list on mount
 *   2. Fetch models when a vendor is selected
 *   3. (Optionally) fetch firmware variants when a device template is matched
 *
 * Used by DevicePropertyForm and RealisticSettingsPanel.
 */

import { useEffect, useState, useCallback } from 'react';
import {
  listVendors,
  getVendorModels,
  listDeviceTemplates,
  listTemplateFirmwares,
  type VendorSummary,
  type DeviceTemplateSummary,
  type FirmwareVariant,
} from '../api/fingerprints';

export interface UseVendorDataOptions {
  /** When true, also fetch device templates and firmware variants. */
  withFirmware?: boolean;
}

export interface UseVendorDataReturn {
  /** List of available vendors (fetched once on mount). */
  vendors: VendorSummary[];
  /** Loading state for the vendor list. */
  loadingVendors: boolean;

  /** Models for the currently selected vendor. */
  models: string[];
  /** Whether the models list is currently loading. */
  loadingModels: boolean;

  /** Device templates matching the selected vendor. */
  deviceTemplates: DeviceTemplateSummary[];

  /** Firmware variants for the matched device template. */
  firmwareVariants: FirmwareVariant[];
  /** Whether firmware variants are currently loading. */
  loadingFirmwares: boolean;

  /** The ID of the currently matched device template (if any). */
  selectedTemplateId: string | null;

  /**
   * Call when the user selects a vendor.
   * Fetches models (and optionally templates) for that vendor,
   * and resets downstream state (models, templates, firmware).
   */
  handleVendorChange: (vendor: string) => Promise<{ models: string[]; templates: DeviceTemplateSummary[] }>;

  /**
   * Call when the user selects a model.
   * Tries to match a device template and loads firmware variants.
   * Returns the matched template ID and firmware list (empty if
   * `withFirmware` is false or no template matches).
   */
  handleModelChange: (model: string) => Promise<{ templateId: string | null; firmwares: FirmwareVariant[] }>;

  /** Reset all state back to initial values. */
  reset: () => void;
}

export function useVendorData(options: UseVendorDataOptions = {}): UseVendorDataReturn {
  const { withFirmware = false } = options;

  // Vendor list (fetched once)
  const [vendors, setVendors] = useState<VendorSummary[]>([]);
  const [loadingVendors, setLoadingVendors] = useState(false);

  // Models for selected vendor
  const [models, setModels] = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);

  // Device templates for selected vendor
  const [deviceTemplates, setDeviceTemplates] = useState<DeviceTemplateSummary[]>([]);

  // Firmware variants for matched template
  const [firmwareVariants, setFirmwareVariants] = useState<FirmwareVariant[]>([]);
  const [loadingFirmwares, setLoadingFirmwares] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);

  // Fetch vendor list on mount
  useEffect(() => {
    let cancelled = false;
    const fetchVendors = async () => {
      setLoadingVendors(true);
      try {
        const data = await listVendors();
        if (!cancelled) setVendors(data);
      } catch (err) {
        console.error('Failed to fetch vendors:', err);
      } finally {
        if (!cancelled) setLoadingVendors(false);
      }
    };
    fetchVendors();
    return () => { cancelled = true; };
  }, []);

  const handleVendorChange = useCallback(async (vendor: string) => {
    // Reset downstream state
    setModels([]);
    setDeviceTemplates([]);
    setFirmwareVariants([]);
    setSelectedTemplateId(null);

    if (!vendor) {
      return { models: [], templates: [] };
    }

    setLoadingModels(true);
    try {
      const fetches: [Promise<string[]>, Promise<DeviceTemplateSummary[]>?] = [
        getVendorModels(vendor),
      ];
      if (withFirmware) {
        fetches.push(listDeviceTemplates({ vendor }));
      }

      const [modelList, templates] = await Promise.all(
        fetches as [Promise<string[]>, Promise<DeviceTemplateSummary[]>]
      );

      const resolvedModels = modelList ?? [];
      const resolvedTemplates = templates ?? [];

      setModels(resolvedModels);
      setDeviceTemplates(resolvedTemplates);

      return { models: resolvedModels, templates: resolvedTemplates };
    } catch (err) {
      console.error('Failed to fetch models:', err);
      return { models: [], templates: [] };
    } finally {
      setLoadingModels(false);
    }
  }, [withFirmware]);

  const handleModelChange = useCallback(async (model: string) => {
    setFirmwareVariants([]);
    setSelectedTemplateId(null);

    if (!withFirmware || !model) {
      return { templateId: null, firmwares: [] };
    }

    // Try to find a matching device template
    const matchedTemplate = deviceTemplates.find(
      (t) => t.model === model || t.model_name === model
    );

    if (!matchedTemplate) {
      return { templateId: null, firmwares: [] };
    }

    setSelectedTemplateId(matchedTemplate.id);
    setLoadingFirmwares(true);
    try {
      const firmwares = await listTemplateFirmwares(matchedTemplate.id);
      setFirmwareVariants(firmwares);
      return { templateId: matchedTemplate.id, firmwares };
    } catch (err) {
      console.error('Failed to fetch firmwares:', err);
      return { templateId: matchedTemplate.id, firmwares: [] };
    } finally {
      setLoadingFirmwares(false);
    }
  }, [withFirmware, deviceTemplates]);

  const reset = useCallback(() => {
    setModels([]);
    setDeviceTemplates([]);
    setFirmwareVariants([]);
    setSelectedTemplateId(null);
  }, []);

  return {
    vendors,
    loadingVendors,
    models,
    loadingModels,
    deviceTemplates,
    firmwareVariants,
    loadingFirmwares,
    selectedTemplateId,
    handleVendorChange,
    handleModelChange,
    reset,
  };
}
