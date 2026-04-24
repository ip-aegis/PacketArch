/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Feature flag store.
 *
 * Loaded on app boot from /api/v1/about.features. When the endpoint is
 * unreachable (or hasn't been fetched yet), selectors fail-open to the
 * permissive default (feature enabled), so a degraded backend doesn't
 * accidentally hide the entire UI. The backend is the authoritative gate
 * via route-level 503s.
 */

import { create } from 'zustand';
import { aboutApi, type Features } from '../api/about';

interface FeaturesState {
  features: Features | null;
  loaded: boolean;
  load: () => Promise<void>;
  isAIEnabled: () => boolean;
}

export const useFeaturesStore = create<FeaturesState>((set, get) => ({
  features: null,
  loaded: false,

  load: async () => {
    try {
      const about = await aboutApi.get();
      set({ features: about.features, loaded: true });
    } catch {
      // Leave features null; selectors default to permissive.
    }
  },

  isAIEnabled: () => {
    const f = get().features;
    if (!f) return true; // fail-open until loaded; backend still gates hard
    return f.ai_enabled;
  },
}));
