/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Setup-state store — mirrors featuresStore semantics.
 *
 * Loaded once on app boot via SetupGate. While unloaded, selectors fail-open
 * to "setup complete" so existing installs don't flash-redirect on slow
 * networks. The backend is the authoritative gate via 503 on every other
 * route while setup is incomplete.
 */

import { create } from 'zustand';
import { setupApi, type SetupStatus } from '../api/setup';

interface SetupStatusState {
  status: SetupStatus | null;
  loaded: boolean;
  load: () => Promise<void>;
  /** Called by the wizard after a successful POST /setup/complete. */
  markComplete: () => void;
}

export const useSetupStatusStore = create<SetupStatusState>((set) => ({
  status: null,
  loaded: false,

  load: async () => {
    try {
      const status = await setupApi.getStatus();
      set({ status, loaded: true });
    } catch {
      // Leave status null; the SetupGate falls back to "complete=true" so a
      // failing endpoint never bricks an existing install.
      set({ loaded: true });
    }
  },

  markComplete: () => {
    set((s) => ({
      status: s.status
        ? { ...s.status, setup_complete: true }
        : {
            setup_complete: true,
            build_variant: 'full',
            ai_supported: true,
            live_traffic_supported: true,
          },
    }));
  },
}));

export default useSetupStatusStore;
