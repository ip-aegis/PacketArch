/**
 * Settings API functions
 */

import apiClient from './client';
import type { SettingsResponse, SystemSetting } from '../types';

const ADMIN_PREFIX = '/api/v1/admin';

export const settingsApi = {
  /**
   * Get all settings grouped by category
   */
  async getAllSettings(): Promise<SettingsResponse> {
    const response = await apiClient.get<SettingsResponse>(`${ADMIN_PREFIX}/settings`);
    return response.data;
  },

  /**
   * Get a specific setting by key
   */
  async getSetting(key: string): Promise<SystemSetting> {
    const response = await apiClient.get<SystemSetting>(`${ADMIN_PREFIX}/settings/${key}`);
    return response.data;
  },

  /**
   * Update a specific setting
   */
  async updateSetting(key: string, value: string | null): Promise<SystemSetting> {
    const response = await apiClient.put<SystemSetting>(`${ADMIN_PREFIX}/settings/${key}`, {
      value,
    });
    return response.data;
  },

  /**
   * Seed default settings
   */
  async seedSettings(): Promise<{ message: string; created: number; skipped: number }> {
    const response = await apiClient.post(`${ADMIN_PREFIX}/settings/seed`);
    return response.data;
  },

  /**
   * Test API connection (e.g., Anthropic API)
   */
  async testConnection(): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post(`${ADMIN_PREFIX}/settings/test-connection`);
    return response.data;
  },
};

export default settingsApi;
