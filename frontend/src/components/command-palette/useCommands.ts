/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Hook that assembles the dynamic command list from the registry + store state.
 * Handles context filtering, search scoring, device search mode (@), and recently-used sorting.
 */

import { useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useHistoryStore } from '../../stores/historyStore';
import { useUIStore } from '../../stores/uiStore';
import { useScenarioStore } from '../../stores/scenarioStore';
import { useFeatures } from '../../hooks/useFeatures';
import { buildCommandRegistry, type RegistryDeps } from './commandRegistry';
import type { CommandDefinition } from './types';
import { getRecentCommandIds } from './useCommandPalette';

/** Deps that can only be provided from inside ReactFlowProvider — optional */
export interface CanvasDeps {
  zoomIn: () => void;
  zoomOut: () => void;
  fitView: () => void;
  applyLayout: (type: string) => void;
  deleteSelected: () => void;
  saveVersion: () => void;
  openVersionHistory: () => void;
  openCustomizeNames: () => void;
}

const NOOP = () => {};

/**
 * Assemble and filter commands.
 * canvasDeps is null when not inside the Studio page (no ReactFlow context).
 */
export function useCommands(
  searchQuery: string,
  canvasDeps: CanvasDeps | null,
): CommandDefinition[] {
  const navigate = useNavigate();
  const location = useLocation();
  const isStudio = location.pathname === '/studio';

  // Store selectors
  const canUndo = useHistoryStore((s) => s.canUndo());
  const canRedo = useHistoryStore((s) => s.canRedo());
  const undo = useHistoryStore((s) => s.undo);
  const redo = useHistoryStore((s) => s.redo);

  const selectedNodeIds = useUIStore((s) => s.selectedNodeIds);
  const leftSidebarOpen = useUIStore((s) => s.panels.leftSidebarOpen);
  const rightSidebarOpen = useUIStore((s) => s.panels.rightSidebarOpen);
  const minimapVisible = useUIStore((s) => s.panels.minimapVisible);
  const bottomPanelOpen = useUIStore((s) => s.panels.bottomPanelOpen);
  const toggleLeftSidebar = useUIStore((s) => s.toggleLeftSidebar);
  const toggleRightSidebar = useUIStore((s) => s.toggleRightSidebar);
  const toggleMinimap = useUIStore((s) => s.toggleMinimap);
  const toggleBottomPanel = useUIStore((s) => s.toggleBottomPanel);
  const clusterViewMode = useUIStore((s) => s.clusterViewMode);
  const setClusterViewMode = useUIStore((s) => s.setClusterViewMode);
  const setPendingFitToNode = useUIStore((s) => s.setPendingFitToNode);

  const scenarioId = useScenarioStore((s) => s.id);
  const devices = useScenarioStore((s) => s.devices);
  const { aiEnabled } = useFeatures();

  // Build full registry
  const deps: RegistryDeps = useMemo(() => ({
    navigate,
    undo,
    redo,
    canUndo,
    canRedo,
    zoomIn: canvasDeps?.zoomIn ?? NOOP,
    zoomOut: canvasDeps?.zoomOut ?? NOOP,
    fitView: canvasDeps?.fitView ?? NOOP,
    selectedNodeIds,
    deleteSelected: canvasDeps?.deleteSelected ?? NOOP,
    leftSidebarOpen,
    rightSidebarOpen,
    minimapVisible,
    bottomPanelOpen,
    toggleLeftSidebar,
    toggleRightSidebar,
    toggleMinimap,
    toggleBottomPanel,
    applyLayout: canvasDeps?.applyLayout ?? NOOP,
    clusterViewMode,
    setClusterViewMode,
    scenarioId,
    saveVersion: canvasDeps?.saveVersion ?? NOOP,
    openVersionHistory: canvasDeps?.openVersionHistory ?? NOOP,
    openCustomizeNames: canvasDeps?.openCustomizeNames ?? NOOP,
    aiEnabled,
  }), [
    navigate, undo, redo, canUndo, canRedo, canvasDeps,
    selectedNodeIds, leftSidebarOpen, rightSidebarOpen, minimapVisible, bottomPanelOpen,
    toggleLeftSidebar, toggleRightSidebar, toggleMinimap, toggleBottomPanel,
    clusterViewMode, setClusterViewMode, scenarioId, aiEnabled,
  ]);

  const allCommands = useMemo(() => buildCommandRegistry(deps), [deps]);

  return useMemo(() => {
    // Device search mode: @ prefix
    if (searchQuery.startsWith('@') && isStudio) {
      const q = searchQuery.slice(1).toLowerCase();
      const deviceList = Object.values(devices);
      const deviceCommands: CommandDefinition[] = [];

      for (const device of deviceList) {
        const searchFields = [
          device.name,
          device.type,
          device.vendor ?? '',
          device.network?.ipAddress ?? '',
          device.network?.hostname ?? '',
          device.role ?? '',
          device.fingerprintModel ?? '',
        ];
        if (!q || searchFields.some((f) => f.toLowerCase().includes(q))) {
          deviceCommands.push({
            id: `device:${device.id}`,
            label: device.name,
            category: 'device-search',
            context: 'studio',
            icon: null,
            keywords: [device.type, device.vendor ?? '', device.network?.ipAddress ?? ''],
            execute: () => setPendingFitToNode(device.id),
          });
        }
        if (deviceCommands.length >= 20) break; // Cap results
      }
      return deviceCommands;
    }

    // Context filtering
    const contextFiltered = allCommands.filter((cmd) => {
      if (cmd.context === 'global') return true;
      if (cmd.context === 'studio' && isStudio) return true;
      if (cmd.context === 'studio-with-selection' && isStudio && selectedNodeIds.length > 0) return true;
      return false;
    });

    // No search query: return grouped by category
    if (!searchQuery) {
      return contextFiltered.filter((cmd) => !cmd.disabled);
    }

    // Search scoring
    const q = searchQuery.toLowerCase();
    const recentIds = getRecentCommandIds();
    const recentSet = new Set(recentIds);

    const scored = contextFiltered
      .filter((cmd) => !cmd.disabled)
      .map((cmd) => {
        let score = 0;
        const label = cmd.label.toLowerCase();
        if (label.startsWith(q)) score += 100;
        else if (label.includes(q)) score += 50;
        if (cmd.keywords?.some((k) => k.toLowerCase().includes(q))) score += 25;
        if (recentSet.has(cmd.id)) score += 200;
        return { cmd, score };
      })
      .filter(({ score }) => score > 0)
      .sort((a, b) => b.score - a.score);

    return scored.map(({ cmd }) => cmd);
  }, [searchQuery, allCommands, isStudio, selectedNodeIds, devices, setPendingFitToNode]);
}
