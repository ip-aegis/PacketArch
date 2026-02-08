/**
 * Device Profile API functions
 */

import { createCrudApi } from './createCrudApi';
import apiClient from './client';
import type { DeviceProfile, DeviceProfileCreate, DeviceProfileUpdate, PaginatedResponse } from '../types';

const PREFIX = '/api/v1/devices';

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
  ...createCrudApi<DeviceProfile, DeviceProfileCreate, DeviceProfileUpdate>({
    prefix: PREFIX,
  }),

  async list(filters: DeviceProfileFilters = {}): Promise<PaginatedResponse<DeviceProfile>> {
    const response = await apiClient.get<PaginatedResponse<DeviceProfile>>(PREFIX, {
      params: {
        device_type: filters.device_type,
        protocol: filters.protocol,
        vertical: filters.vertical,
        search: filters.search,
        builtin_only: filters.builtin_only,
        page: filters.page,
        page_size: filters.page_size,
      },
    });
    return response.data;
  },

  async duplicate(id: string, newName?: string): Promise<DeviceProfile> {
    const params = newName ? `?new_name=${encodeURIComponent(newName)}` : '';
    const response = await apiClient.post<DeviceProfile>(`${PREFIX}/${id}/duplicate${params}`);
    return response.data;
  },

  async getDeviceTypes(): Promise<string[]> {
    const response = await apiClient.get<string[]>(`${PREFIX}/types`);
    return response.data;
  },
};

export default devicesApi;
