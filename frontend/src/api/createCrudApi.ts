/**
 * Generic CRUD API factory.
 *
 * Generates standard list/get/create/update/delete methods for a REST endpoint.
 * Spread the result and extend with custom methods:
 *
 *   export const widgetsApi = {
 *     ...createCrudApi<Widget, WidgetCreate, WidgetUpdate>({
 *       prefix: '/api/v1/widgets',
 *     }),
 *     async duplicate(id: string) { ... },
 *   };
 *
 * The returned object satisfies ResourceApi<T, C, U> from createResourceStore.ts.
 */

import apiClient from './client';

export interface CrudApiConfig {
  /** URL prefix, e.g. '/api/v1/devices' */
  prefix: string;
  /** HTTP method for update: 'patch' (default) or 'put' */
  updateMethod?: 'patch' | 'put';
}

export interface CrudApi<T, C = Partial<T>, U = Partial<T>> {
  list: (params?: Record<string, unknown>) => Promise<unknown>;
  get: (id: string) => Promise<T>;
  create: (data: C) => Promise<T>;
  update: (id: string, data: U) => Promise<T>;
  delete: (id: string) => Promise<void>;
}

export function createCrudApi<T, C = Partial<T>, U = Partial<T>>(
  config: CrudApiConfig,
): CrudApi<T, C, U> {
  const { prefix, updateMethod = 'patch' } = config;

  return {
    async list(params?: Record<string, unknown>) {
      const response = await apiClient.get(prefix, { params });
      return response.data;
    },

    async get(id: string): Promise<T> {
      const response = await apiClient.get<T>(`${prefix}/${id}`);
      return response.data;
    },

    async create(data: C): Promise<T> {
      const response = await apiClient.post<T>(prefix, data);
      return response.data;
    },

    async update(id: string, data: U): Promise<T> {
      const response = await apiClient[updateMethod]<T>(`${prefix}/${id}`, data);
      return response.data;
    },

    async delete(id: string): Promise<void> {
      await apiClient.delete(`${prefix}/${id}`);
    },
  };
}
