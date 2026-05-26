/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * UI state management with Zustand
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AggregateEdgeInfo } from '../components/canvas/edges/FlowEdge';

interface PanelState {
  leftSidebarOpen: boolean;
  leftSidebarWidth: number;
  rightSidebarOpen: boolean;
  rightSidebarWidth: number;
  bottomPanelOpen: boolean;
  bottomPanelHeight: number;
  timelineVisible: boolean;
  minimapVisible: boolean;
  showFlows: boolean;
  showConduits: boolean;
  aggregateFlows: boolean;
}

interface ViewportState {
  zoom: number;
  position: { x: number; y: number };
}

interface ToolState {
  activeTool: 'select' | 'pan' | 'zone' | 'connection' | 'conduit';
}

export type ClusterViewMode = 'none' | 'zone' | 'protocol' | 'vendor' | 'purdueLevel' | 'deviceType';

interface UIState {
  // Panel state
  panels: PanelState;
  toggleLeftSidebar: () => void;
  toggleRightSidebar: () => void;
  toggleBottomPanel: () => void;
  toggleTimeline: () => void;
  toggleMinimap: () => void;
  toggleShowFlows: () => void;
  toggleShowConduits: () => void;
  toggleAggregateFlows: () => void;
  setLeftSidebarWidth: (width: number) => void;
  setRightSidebarWidth: (width: number) => void;
  setBottomPanelHeight: (height: number) => void;

  // Cluster view state
  clusterViewMode: ClusterViewMode;
  setClusterViewMode: (mode: ClusterViewMode) => void;

  // Viewport state
  viewport: ViewportState;
  setZoom: (zoom: number) => void;
  setViewport: (viewport: ViewportState) => void;

  // Tool state
  tool: ToolState;
  setActiveTool: (tool: ToolState['activeTool']) => void;

  // Selection state
  selectedNodeIds: string[];
  selectedEdgeIds: string[];
  setSelection: (nodeIds: string[], edgeIds?: string[]) => void;
  clearSelection: () => void;

  // Active property context
  activePropertyContext: {
    type: 'device' | 'flow' | 'zone' | 'conduit' | 'clusterEdge' | 'multi' | null;
    ids: string[];
  };
  setPropertyContext: (type: 'device' | 'flow' | 'zone' | 'conduit' | 'clusterEdge' | 'multi' | null, ids: string[]) => void;

  // Aggregate (cluster-to-cluster) edge selection side-channel.
  // Populated when the user clicks an aggregate edge in cluster view so the
  // Properties panel has enough data to describe the group-to-group link.
  selectedAggregateEdge: AggregateEdgeInfo | null;
  setSelectedAggregateEdge: (info: AggregateEdgeInfo | null) => void;

  // Modals
  activeModal: string | null;
  modalData: Record<string, unknown>;
  openModal: (modalId: string, data?: Record<string, unknown>) => void;
  closeModal: () => void;

  // Command Palette
  commandPaletteOpen: boolean;
  openCommandPalette: () => void;
  closeCommandPalette: () => void;
  toggleCommandPalette: () => void;

  // Device search → canvas navigation bridge
  pendingFitToNode: string | null;
  setPendingFitToNode: (id: string | null) => void;

  // Theme
  theme: 'light' | 'dark' | 'system';
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      // Panel state
      panels: {
        leftSidebarOpen: true,
        leftSidebarWidth: 280,
        rightSidebarOpen: true,
        rightSidebarWidth: 320,
        bottomPanelOpen: false,
        bottomPanelHeight: 200,
        timelineVisible: true,
        minimapVisible: true,
        showFlows: true,
        showConduits: true,
        aggregateFlows: false,
      },
      toggleLeftSidebar: () =>
        set((state) => ({
          panels: { ...state.panels, leftSidebarOpen: !state.panels.leftSidebarOpen },
        })),
      toggleRightSidebar: () =>
        set((state) => ({
          panels: { ...state.panels, rightSidebarOpen: !state.panels.rightSidebarOpen },
        })),
      toggleBottomPanel: () =>
        set((state) => ({
          panels: { ...state.panels, bottomPanelOpen: !state.panels.bottomPanelOpen },
        })),
      toggleTimeline: () =>
        set((state) => ({
          panels: { ...state.panels, timelineVisible: !state.panels.timelineVisible },
        })),
      toggleMinimap: () =>
        set((state) => ({
          panels: { ...state.panels, minimapVisible: !state.panels.minimapVisible },
        })),
      toggleShowFlows: () =>
        set((state) => ({
          panels: { ...state.panels, showFlows: !state.panels.showFlows },
        })),
      toggleShowConduits: () =>
        set((state) => ({
          panels: { ...state.panels, showConduits: !state.panels.showConduits },
        })),
      toggleAggregateFlows: () =>
        set((state) => ({
          panels: { ...state.panels, aggregateFlows: !state.panels.aggregateFlows },
        })),
      setLeftSidebarWidth: (width) =>
        set((state) => ({
          panels: { ...state.panels, leftSidebarWidth: width },
        })),
      setRightSidebarWidth: (width) =>
        set((state) => ({
          panels: { ...state.panels, rightSidebarWidth: width },
        })),
      setBottomPanelHeight: (height) =>
        set((state) => ({
          panels: { ...state.panels, bottomPanelHeight: height },
        })),

      // Cluster view state
      clusterViewMode: 'none',
      setClusterViewMode: (mode) => set({ clusterViewMode: mode }),

      // Viewport state
      viewport: {
        zoom: 1,
        position: { x: 0, y: 0 },
      },
      setZoom: (zoom) =>
        set((state) => ({
          viewport: { ...state.viewport, zoom },
        })),
      setViewport: (viewport) => set({ viewport }),

      // Tool state
      tool: {
        activeTool: 'select',
      },
      setActiveTool: (activeTool) =>
        set((state) => ({
          tool: { ...state.tool, activeTool },
        })),

      // Selection state
      selectedNodeIds: [],
      selectedEdgeIds: [],
      setSelection: (nodeIds, edgeIds = []) =>
        set({
          selectedNodeIds: nodeIds,
          selectedEdgeIds: edgeIds,
        }),
      clearSelection: () =>
        set({
          selectedNodeIds: [],
          selectedEdgeIds: [],
        }),

      // Active property context
      activePropertyContext: {
        type: null,
        ids: [],
      },
      setPropertyContext: (type, ids) =>
        set({
          activePropertyContext: { type, ids },
        }),

      selectedAggregateEdge: null,
      setSelectedAggregateEdge: (info) => set({ selectedAggregateEdge: info }),

      // Modals
      activeModal: null,
      modalData: {},
      openModal: (modalId, data = {}) =>
        set({
          activeModal: modalId,
          modalData: data,
        }),
      closeModal: () =>
        set({
          activeModal: null,
          modalData: {},
        }),

      // Command Palette
      commandPaletteOpen: false,
      openCommandPalette: () => set({ commandPaletteOpen: true }),
      closeCommandPalette: () => set({ commandPaletteOpen: false }),
      toggleCommandPalette: () =>
        set((state) => ({ commandPaletteOpen: !state.commandPaletteOpen })),

      // Device search → canvas navigation bridge
      pendingFitToNode: null,
      setPendingFitToNode: (id) => set({ pendingFitToNode: id }),

      // Theme
      theme: 'light',
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        panels: state.panels,
        theme: state.theme,
        clusterViewMode: state.clusterViewMode,
      }),
    }
  )
);

export default useUIStore;
