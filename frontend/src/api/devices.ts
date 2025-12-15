/**
 * Device Profile API functions
 */

import apiClient from './client';
import type { DeviceProfile, DeviceProfileCreate, DeviceProfileUpdate, PaginatedResponse } from '../types';

const DEVICES_PREFIX = '/api/v1/devices';

export interface DeviceProfileFilters {
  device_type?: string;
  protocol?: string;
  vertical?: string;
  search?: string;
  builtin_only?: boolean;
  page?: number;
  page_size?: number;
}

export const devicesApi = {
  /**
   * List device profiles with optional filters
   */
  async list(filters: DeviceProfileFilters = {}): Promise<PaginatedResponse<DeviceProfile>> {
    const params = new URLSearchParams();

    if (filters.device_type) params.append('device_type', filters.device_type);
    if (filters.protocol) params.append('protocol', filters.protocol);
    if (filters.vertical) params.append('vertical', filters.vertical);
    if (filters.search) params.append('search', filters.search);
    if (filters.builtin_only !== undefined) params.append('builtin_only', String(filters.builtin_only));
    if (filters.page) params.append('page', String(filters.page));
    if (filters.page_size) params.append('page_size', String(filters.page_size));

    const response = await apiClient.get<PaginatedResponse<DeviceProfile>>(
      `${DEVICES_PREFIX}?${params.toString()}`
    );
    return response.data;
  },

  /**
   * Get a single device profile by ID
   */
  async get(id: string): Promise<DeviceProfile> {
    const response = await apiClient.get<DeviceProfile>(`${DEVICES_PREFIX}/${id}`);
    return response.data;
  },

  /**
   * Create a new device profile
   */
  async create(data: DeviceProfileCreate): Promise<DeviceProfile> {
    const response = await apiClient.post<DeviceProfile>(DEVICES_PREFIX, data);
    return response.data;
  },

  /**
   * Update an existing device profile
   */
  async update(id: string, data: DeviceProfileUpdate): Promise<DeviceProfile> {
    const response = await apiClient.patch<DeviceProfile>(`${DEVICES_PREFIX}/${id}`, data);
    return response.data;
  },

  /**
   * Delete a device profile
   */
  async delete(id: string): Promise<void> {
    await apiClient.delete(`${DEVICES_PREFIX}/${id}`);
  },

  /**
   * Duplicate a device profile
   */
  async duplicate(id: string, newName?: string): Promise<DeviceProfile> {
    const params = newName ? `?new_name=${encodeURIComponent(newName)}` : '';
    const response = await apiClient.post<DeviceProfile>(`${DEVICES_PREFIX}/${id}/duplicate${params}`);
    return response.data;
  },

  /**
   * Get available device types
   */
  async getDeviceTypes(): Promise<string[]> {
    const response = await apiClient.get<string[]>(`${DEVICES_PREFIX}/types`);
    return response.data;
  },
};

export default devicesApi;
