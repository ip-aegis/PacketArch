/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 UI state — chrome state only (panel visibility, armed palette
 * template). Scenario data never lives here; that's the document store.
 */

import { create } from 'zustand';
import type { PaletteDeviceResponse } from '../api/fingerprints';

interface Studio2UIState {
  railOpen: boolean;
  inspectorOpen: boolean;
  /** Palette template armed for click-to-place (null = not armed). */
  armedTemplate: PaletteDeviceResponse | null;

  toggleRail: () => void;
  toggleInspector: () => void;
  setArmedTemplate: (t: PaletteDeviceResponse | null) => void;
}

export const useStudio2UI = create<Studio2UIState>((set) => ({
  railOpen: true,
  inspectorOpen: true,
  armedTemplate: null,

  toggleRail: () => set((s) => ({ railOpen: !s.railOpen })),
  toggleInspector: () => set((s) => ({ inspectorOpen: !s.inspectorOpen })),
  setArmedTemplate: (armedTemplate) => set({ armedTemplate }),
}));
