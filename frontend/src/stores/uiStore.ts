/**
 * UI state management with Zustand
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface PanelState {
  leftSidebarOpen: boolean;
  leftSidebarWidth: number;
  rightSidebarOpen: boolean;
  rightSidebarWidth: number;
  bottomPanelOpen: boolean;
  bottomPanelHeight: number;
  timelineVisible: boolean;
  minimapVisible: boolean;
}

interface ViewportState {
  zoom: number;
  position: { x: number; y: number };
}

interface ToolState {
  activeTool: 'select' | 'pan' | 'zone' | 'connection';
}

interface UIState {
  // Panel state
  panels: PanelState;
  toggleLeftSidebar: () => void;
  toggleRightSidebar: () => void;
  toggleBottomPanel: () => void;
  toggleTimeline: () => void;
  toggleMinimap: () => void;
  setLeftSidebarWidth: (width: number) => void;
  setRightSidebarWidth: (width: number) => void;
  setBottomPanelHeight: (height: number) => void;

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
    type: 'device' | 'flow' | 'zone' | 'multi' | null;
    ids: string[];
  };
  setPropertyContext: (type: 'device' | 'flow' | 'zone' | 'multi' | null, ids: string[]) => void;

  // Modals
  activeModal: string | null;
  modalData: Record<string, unknown>;
  openModal: (modalId: string, data?: Record<string, unknown>) => void;
  closeModal: () => void;

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

      // Theme
      theme: 'light',
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        panels: state.panels,
        theme: state.theme,
      }),
    }
  )
);

export default useUIStore;
