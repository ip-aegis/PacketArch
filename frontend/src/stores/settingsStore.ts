/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Settings state management with Zustand
 */

import { create } from 'zustand';
import type { SettingsResponse, SystemSetting } from '../types';
import { settingsApi } from '../api/settings';
import { extractErrorMessage } from '../utils/errorUtils';

interface SettingsState {
  settings: SettingsResponse | null;
  isLoading: boolean;
  error: string | null;
  lastUpdated: string | null;

  // Actions
  fetchSettings: () => Promise<void>;
  updateSetting: (key: string, value: string | null) => Promise<void>;
  seedSettings: () => Promise<{ created: number; skipped: number }>;
  testConnection: () => Promise<{ success: boolean; message: string }>;
  clearError: () => void;

  // Selectors
  getSettingByKey: (key: string) => SystemSetting | undefined;
}

export const useSettingsStore = create<SettingsState>()((set, get) => ({
  settings: null,
  isLoading: false,
  error: null,
  lastUpdated: null,

  fetchSettings: async () => {
    set({ isLoading: true, error: null });
    try {
      const settings = await settingsApi.getAllSettings();
      set({
        settings,
        isLoading: false,
        lastUpdated: new Date().toISOString(),
      });
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Failed to fetch settings');
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  updateSetting: async (key: string, value: string | null) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await settingsApi.updateSetting(key, value);

      // Update the local state
      const currentSettings = get().settings;
      if (currentSettings) {
        const updateCategory = (settings: SystemSetting[]) =>
          settings.map((s) => (s.key === key ? updated : s));

        set({
          settings: {
            api_tokens: updateCategory(currentSettings.api_tokens),
            network: updateCategory(currentSettings.network),
            system: updateCategory(currentSettings.system),
          },
          isLoading: false,
          lastUpdated: new Date().toISOString(),
        });
      } else {
        set({ isLoading: false });
      }
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Failed to update setting');
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  seedSettings: async () => {
    set({ isLoading: true, error: null });
    try {
      const result = await settingsApi.seedSettings();
      // Refresh settings after seeding
      await get().fetchSettings();
      return result;
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Failed to seed settings');
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  testConnection: async () => {
    try {
      const result = await settingsApi.testConnection();
      return result;
    } catch (error: unknown) {
      const message = extractErrorMessage(error, 'Connection test failed');
      return { success: false, message };
    }
  },

  clearError: () => {
    set({ error: null });
  },

  getSettingByKey: (key: string) => {
    const settings = get().settings;
    if (!settings) return undefined;

    const allSettings = [
      ...settings.api_tokens,
      ...settings.network,
      ...settings.system,
    ];
    return allSettings.find((s) => s.key === key);
  },
}));

export default useSettingsStore;
