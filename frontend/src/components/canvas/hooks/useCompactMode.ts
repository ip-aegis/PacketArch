/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Hook that returns whether the canvas is in compact mode based on zoom level.
 * Only triggers re-renders when zoom crosses the COMPACT_THRESHOLD boundary.
 */

import { useStore } from '@xyflow/react';

export const COMPACT_THRESHOLD = 0.6;

// Selector defined outside the hook for stable reference —
// React Flow's internal store is Zustand, and a boolean return means
// re-renders only fire when the value flips (not on every zoom tick).
const selectIsCompact = (state: { transform: [number, number, number] }) =>
  state.transform[2] < COMPACT_THRESHOLD;

export function useCompactMode(): boolean {
  return useStore(selectIsCompact);
}
