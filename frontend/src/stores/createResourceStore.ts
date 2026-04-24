/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Generic CRUD store factory for Zustand.
 *
 * Eliminates try-catch/extractErrorMessage/list-mutation boilerplate across
 * stores that follow the standard items + selectedItem + isLoading + error pattern.
 *
 * Usage:
 *   const crud = createResourceSlice<Widget, WidgetCreate, WidgetUpdate>({
 *     resourceName: 'widget',
 *     api: widgetApi,
 *     listExtractor: (r) => r.items,
 *     itemsKey: 'widgets',
 *     selectedKey: 'selectedWidget',
 *   });
 *
 *   export const useWidgetStore = create<WidgetState>()((set, get) => {
 *     const { fetchAll, fetchOne, createOne, updateOne, deleteOne, clearError } = crud(set, get);
 *     return {
 *       widgets: [], selectedWidget: null, isLoading: false, error: null,
 *       fetchWidgets: fetchAll,
 *       createWidget: createOne,
 *       // ...custom actions...
 *     };
 *   });
 */

import { extractErrorMessage } from '../utils/errorUtils';

/** Minimal API shape the factory can drive. */
export interface ResourceApi<T, C = Partial<T>, U = Partial<T>> {
  list: (...args: any[]) => Promise<any>;
  get: (id: string) => Promise<T>;
  create: (data: C) => Promise<T>;
  update: (id: string, data: U) => Promise<T>;
  delete: (id: string) => Promise<void>;
}

export interface ResourceConfig<T, C, U> {
  /** Human-readable name for error messages, e.g. "Docker host". */
  resourceName: string;
  /** API object with list/get/create/update/delete methods. */
  api: ResourceApi<T, C, U>;
  /** Extract the items array from the list() response. */
  listExtractor: (response: any) => T[];
  /** Property name for the items array in the consuming store (e.g. "hosts"). */
  itemsKey: string;
  /** Property name for the selected item in the consuming store (e.g. "selectedHost"). */
  selectedKey: string;
  /** Field used to match items by ID. Defaults to "id". */
  idField?: string;
}

export interface CrudActions<T, C, U> {
  fetchAll: (...args: any[]) => Promise<void>;
  fetchOne: (id: string) => Promise<T>;
  createOne: (data: C) => Promise<T>;
  updateOne: (id: string, data: U) => Promise<T>;
  deleteOne: (id: string) => Promise<void>;
  clearError: () => void;
}

/**
 * Creates CRUD action implementations that use dynamic property names
 * matching the consuming store's field names.
 *
 * Returns a function that accepts Zustand set/get and produces the actions.
 */
export function createResourceSlice<T, C = Partial<T>, U = Partial<T>>(
  config: ResourceConfig<T, C, U>,
): (set: any, get: any) => CrudActions<T, C, U> {
  const {
    resourceName,
    api,
    listExtractor,
    itemsKey,
    selectedKey,
    idField = 'id',
  } = config;

  return (set: any, _get: any): CrudActions<T, C, U> => {
    const matchId = (item: T, id: string) =>
      String((item as Record<string, unknown>)[idField]) === id;

    return {
      fetchAll: async (...args: any[]) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.list(...args);
          set({ [itemsKey]: listExtractor(response), isLoading: false });
        } catch (error: unknown) {
          const msg = extractErrorMessage(error, `Failed to fetch ${resourceName}s`);
          set({ error: msg, isLoading: false });
          throw error;
        }
      },

      fetchOne: async (id: string) => {
        set({ isLoading: true, error: null });
        try {
          const item = await api.get(id);
          set((s: any) => ({
            [itemsKey]: s[itemsKey].map((i: T) => (matchId(i, id) ? item : i)),
            [selectedKey]:
              s[selectedKey] && matchId(s[selectedKey], id) ? item : s[selectedKey],
            isLoading: false,
          }));
          return item;
        } catch (error: unknown) {
          const msg = extractErrorMessage(error, `Failed to fetch ${resourceName}`);
          set({ error: msg, isLoading: false });
          throw error;
        }
      },

      createOne: async (data: C) => {
        set({ isLoading: true, error: null });
        try {
          const item = await api.create(data);
          set((s: any) => ({
            [itemsKey]: [...s[itemsKey], item],
            isLoading: false,
          }));
          return item;
        } catch (error: unknown) {
          const msg = extractErrorMessage(error, `Failed to create ${resourceName}`);
          set({ error: msg, isLoading: false });
          throw error;
        }
      },

      updateOne: async (id: string, data: U) => {
        set({ isLoading: true, error: null });
        try {
          const item = await api.update(id, data);
          set((s: any) => ({
            [itemsKey]: s[itemsKey].map((i: T) => (matchId(i, id) ? item : i)),
            [selectedKey]:
              s[selectedKey] && matchId(s[selectedKey], id) ? item : s[selectedKey],
            isLoading: false,
          }));
          return item;
        } catch (error: unknown) {
          const msg = extractErrorMessage(error, `Failed to update ${resourceName}`);
          set({ error: msg, isLoading: false });
          throw error;
        }
      },

      deleteOne: async (id: string) => {
        set({ isLoading: true, error: null });
        try {
          await api.delete(id);
          set((s: any) => ({
            [itemsKey]: s[itemsKey].filter((i: T) => !matchId(i, id)),
            [selectedKey]:
              s[selectedKey] && matchId(s[selectedKey], id) ? null : s[selectedKey],
            isLoading: false,
          }));
        } catch (error: unknown) {
          const msg = extractErrorMessage(error, `Failed to delete ${resourceName}`);
          set({ error: msg, isLoading: false });
          throw error;
        }
      },

      clearError: () => set({ error: null }),
    };
  };
}
