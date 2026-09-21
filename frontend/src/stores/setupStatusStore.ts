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
  /**
   * True when /setup/status could not be read at all. The gate still fails
   * open (see `load`), but silence made the fallback indistinguishable from a
   * healthy install: an operator whose nginx could not reach the backend got a
   * normal-looking login page, and every attempt said "Server error". This flag
   * is what lets the UI say what is actually wrong.
   */
  statusUnavailable: boolean;
  /** HTTP status behind `statusUnavailable`, or null for a transport failure. */
  statusErrorCode: number | null;
  load: () => Promise<void>;
  /** Called by the wizard after a successful POST /setup/complete. */
  markComplete: () => void;
}

export const useSetupStatusStore = create<SetupStatusState>((set) => ({
  status: null,
  loaded: false,
  statusUnavailable: false,
  statusErrorCode: null,

  load: async () => {
    try {
      const status = await setupApi.getStatus();
      set({ status, loaded: true, statusUnavailable: false, statusErrorCode: null });
    } catch (err) {
      // Keep failing open — a failing endpoint must never brick an existing
      // install — but record that we did, so the UI can say so out loud.
      const code =
        (err as { response?: { status?: number } } | undefined)?.response?.status ?? null;
      set({ loaded: true, statusUnavailable: true, statusErrorCode: code });
    }
  },

  markComplete: () => {
    set((s) => ({
      statusUnavailable: false,
      statusErrorCode: null,
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
