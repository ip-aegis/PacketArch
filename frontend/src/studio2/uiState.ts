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

export type GroupByMode = 'none' | 'zone' | 'protocol' | 'vendor' | 'purdueLevel' | 'deviceType';

export const GROUP_BY_MODES: GroupByMode[] = [
  'none',
  'zone',
  'protocol',
  'vendor',
  'purdueLevel',
  'deviceType',
];

export const GROUP_BY_LABELS: Record<GroupByMode, string> = {
  none: 'no grouping',
  zone: 'by zone',
  protocol: 'by protocol',
  vendor: 'by vendor',
  purdueLevel: 'by Purdue level',
  deviceType: 'by device type',
};

interface Studio2UIState {
  railOpen: boolean;
  inspectorOpen: boolean;
  /** Palette template armed for click-to-place (null = not armed). */
  armedTemplate: PaletteDeviceResponse | null;
  /** Zone-draw armed: next canvas click places a new zone. */
  zoneArmed: boolean;
  /** Conduit tool armed: click two zones to connect them. */
  conduitArmed: boolean;
  /** First zone clicked while the conduit tool is armed. */
  conduitSourceZoneId: string | null;
  /** Group-by cluster view mode ('none' = normal canvas). */
  groupBy: GroupByMode;
  /** Clusters expanded in place (reset on mode change). */
  expandedClusterIds: Set<string>;
  /** Active workspace: Build (edit) or Verify (health). Run lands in Phase 4. */
  workspace: 'build' | 'verify';
  /** Hovered health finding: elements to spotlight (everything else dims). */
  highlight: { nodeIds: string[]; edgeIds: string[] } | null;
  /** One-shot request to select + zoom to elements (consumed by the canvas). */
  focusRequest: { nodeIds: string[]; edgeIds: string[] } | null;

  toggleRail: () => void;
  toggleInspector: () => void;
  setArmedTemplate: (t: PaletteDeviceResponse | null) => void;
  setZoneArmed: (armed: boolean) => void;
  setConduitArmed: (armed: boolean) => void;
  setConduitSourceZoneId: (zoneId: string | null) => void;
  setGroupBy: (mode: GroupByMode) => void;
  toggleCluster: (clusterId: string) => void;
  setWorkspace: (w: 'build' | 'verify') => void;
  setHighlight: (h: { nodeIds: string[]; edgeIds: string[] } | null) => void;
  setFocusRequest: (f: { nodeIds: string[]; edgeIds: string[] } | null) => void;
}

export const useStudio2UI = create<Studio2UIState>((set) => ({
  railOpen: true,
  inspectorOpen: true,
  armedTemplate: null,
  zoneArmed: false,
  conduitArmed: false,
  conduitSourceZoneId: null,
  groupBy: 'none',
  expandedClusterIds: new Set<string>(),
  workspace: 'build',
  highlight: null,
  focusRequest: null,

  toggleRail: () => set((s) => ({ railOpen: !s.railOpen })),
  toggleInspector: () => set((s) => ({ inspectorOpen: !s.inspectorOpen })),
  setArmedTemplate: (armedTemplate) =>
    set({ armedTemplate, zoneArmed: false, conduitArmed: false, conduitSourceZoneId: null }),
  setZoneArmed: (zoneArmed) =>
    set({ zoneArmed, armedTemplate: null, conduitArmed: false, conduitSourceZoneId: null }),
  setConduitArmed: (conduitArmed) =>
    set({ conduitArmed, armedTemplate: null, zoneArmed: false, conduitSourceZoneId: null }),
  setConduitSourceZoneId: (conduitSourceZoneId) => set({ conduitSourceZoneId }),
  setGroupBy: (groupBy) => set({ groupBy, expandedClusterIds: new Set() }),
  toggleCluster: (clusterId) =>
    set((s) => {
      const next = new Set(s.expandedClusterIds);
      if (next.has(clusterId)) next.delete(clusterId);
      else next.add(clusterId);
      return { expandedClusterIds: next };
    }),
  setWorkspace: (workspace) => set({ workspace, highlight: null }),
  setHighlight: (highlight) => set({ highlight }),
  setFocusRequest: (focusRequest) => set({ focusRequest }),
}));
