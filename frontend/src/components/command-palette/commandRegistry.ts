/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Command registry — static command definitions assembled with injected dependencies.
 * Each command has an id, label, category, context, icon, optional shortcut/keywords, and execute callback.
 */

import React from 'react';
import {
  DashboardOutlined,
  FolderOutlined,
  DatabaseOutlined,

  CloudServerOutlined,
  BarChartOutlined,
  GlobalOutlined,
  BugOutlined,
  EyeOutlined,
  SettingOutlined,
  QuestionCircleOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  ExpandOutlined,
  UndoOutlined,
  RedoOutlined,
  DeleteOutlined,
  LayoutOutlined,
  BuildOutlined,
  NodeIndexOutlined,
  AppstoreOutlined,
  RadiusSettingOutlined,
  EyeInvisibleOutlined,
  EditOutlined,
  SaveOutlined,
  HistoryOutlined,
  BlockOutlined,
  PartitionOutlined,
  ApiOutlined,
  ShopOutlined,
  GroupOutlined,
  PlusOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import type { CommandDefinition } from './types';
import type { ClusterViewMode } from '../../stores/uiStore';
import type { LayoutType } from '../canvas/hooks/useAutoLayout';

/** Platform-aware modifier key display */
const isMac = typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.platform);
const MOD = isMac ? '⌘' : 'Ctrl';

export interface RegistryDeps {
  navigate: (path: string) => void;
  // History
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  // Canvas
  zoomIn: () => void;
  zoomOut: () => void;
  fitView: () => void;
  // Selection
  selectedNodeIds: string[];
  deleteSelected: () => void;
  // Panels
  leftSidebarOpen: boolean;
  rightSidebarOpen: boolean;
  minimapVisible: boolean;
  bottomPanelOpen: boolean;
  toggleLeftSidebar: () => void;
  toggleRightSidebar: () => void;
  toggleMinimap: () => void;
  toggleBottomPanel: () => void;
  // Layout
  applyLayout: (type: LayoutType) => void;
  // Cluster view
  clusterViewMode: ClusterViewMode;
  setClusterViewMode: (mode: ClusterViewMode) => void;
  // Scenario
  scenarioId: string | null;
  saveVersion: () => void;
  openVersionHistory: () => void;
  openCustomizeNames: () => void;
  // Feature flags
  aiEnabled: boolean;
}

export function buildCommandRegistry(deps: RegistryDeps): CommandDefinition[] {
  const commands: CommandDefinition[] = [];
  const e = React.createElement;

  // ── Navigation ─────────────────────────────────────────────
  const navItems: Array<{ path: string; label: string; icon: React.ReactNode; keywords?: string[] }> = [
    { path: '/', label: 'Go to Dashboard', icon: e(DashboardOutlined), keywords: ['home', 'overview'] },
    { path: '/scenarios', label: 'Go to Scenarios', icon: e(FolderOutlined), keywords: ['list', 'projects'] },
    { path: '/studio', label: 'Go to Scenario Studio', icon: e(LayoutOutlined), keywords: ['canvas', 'editor', 'design'] },
    { path: '/fingerprints', label: 'Go to Device Library', icon: e(DatabaseOutlined), keywords: ['templates', 'profiles', 'fingerprints', 'signatures'] },

    { path: '/deployments', label: 'Go to Deployments', icon: e(CloudServerOutlined), keywords: ['running', 'active'] },
    { path: '/live-traffic', label: 'Go to Live Traffic', icon: e(BarChartOutlined), keywords: ['dashboard', 'monitoring'] },
    { path: '/ip-management', label: 'Go to IP Management', icon: e(GlobalOutlined), keywords: ['addresses', 'ranges', 'subnets'] },
    { path: '/cves', label: 'Go to CVE Browser', icon: e(BugOutlined), keywords: ['vulnerabilities', 'security'] },
    { path: '/cyber-vision', label: 'Go to Cyber Vision', icon: e(EyeOutlined), keywords: ['cisco', 'comparison', 'enrichment'] },
    { path: '/admin/settings', label: 'Go to Settings', icon: e(SettingOutlined), keywords: ['admin', 'configuration', 'preferences'] },
    { path: '/help', label: 'Go to Help', icon: e(QuestionCircleOutlined), keywords: ['documentation', 'guide'] },
  ];

  navItems.forEach(({ path, label, icon, keywords }) => {
    commands.push({
      id: `nav:${path}`,
      label,
      category: 'navigation',
      context: 'global',
      icon,
      keywords,
      execute: () => deps.navigate(path),
    });
  });

  // ── Canvas Actions ─────────────────────────────────────────

  commands.push(
    {
      id: 'canvas:zoom-in',
      label: 'Zoom In',
      category: 'canvas',
      context: 'studio',
      icon: e(ZoomInOutlined),
      shortcut: `${MOD}+=`,
      keywords: ['magnify', 'bigger'],
      execute: () => deps.zoomIn(),
    },
    {
      id: 'canvas:zoom-out',
      label: 'Zoom Out',
      category: 'canvas',
      context: 'studio',
      icon: e(ZoomOutOutlined),
      shortcut: `${MOD}+-`,
      keywords: ['smaller'],
      execute: () => deps.zoomOut(),
    },
    {
      id: 'canvas:fit-view',
      label: 'Fit View',
      category: 'canvas',
      context: 'studio',
      icon: e(ExpandOutlined),
      keywords: ['reset', 'center', 'overview'],
      execute: () => deps.fitView(),
    },
    {
      id: 'canvas:undo',
      label: 'Undo',
      category: 'canvas',
      context: 'studio',
      icon: e(UndoOutlined),
      shortcut: `${MOD}+Z`,
      disabled: !deps.canUndo,
      execute: () => deps.undo(),
    },
    {
      id: 'canvas:redo',
      label: 'Redo',
      category: 'canvas',
      context: 'studio',
      icon: e(RedoOutlined),
      shortcut: `${MOD}+Shift+Z`,
      disabled: !deps.canRedo,
      execute: () => deps.redo(),
    },
    {
      id: 'canvas:delete-selected',
      label: 'Delete Selected',
      category: 'canvas',
      context: 'studio-with-selection',
      icon: e(DeleteOutlined),
      shortcut: 'Del',
      execute: () => deps.deleteSelected(),
    },
  );

  // ── Layout ─────────────────────────────────────────────────

  const layoutItems: Array<{ type: LayoutType; label: string; icon: React.ReactNode; keywords?: string[] }> = [
    { type: 'purdue', label: 'Layout: Purdue Model', icon: e(BuildOutlined), keywords: ['levels', 'hierarchy', 'ics'] },
    { type: 'dataflow', label: 'Layout: Data Flow', icon: e(NodeIndexOutlined), keywords: ['hierarchical', 'tree'] },
    { type: 'grid', label: 'Layout: Grid', icon: e(AppstoreOutlined), keywords: ['arrange', 'align', 'tidy'] },
    { type: 'circular', label: 'Layout: Circular', icon: e(RadiusSettingOutlined), keywords: ['ring', 'radial'] },
  ];

  layoutItems.forEach(({ type, label, icon, keywords }) => {
    commands.push({
      id: `layout:${type}`,
      label,
      category: 'canvas',
      context: 'studio',
      icon,
      keywords,
      execute: () => {
        deps.applyLayout(type);
        setTimeout(() => deps.fitView(), 50);
      },
    });
  });

  // ── Panel Toggles ──────────────────────────────────────────

  commands.push(
    {
      id: 'panel:left-sidebar',
      label: deps.leftSidebarOpen ? 'Hide Device Palette' : 'Show Device Palette',
      category: 'panel',
      context: 'studio',
      icon: deps.leftSidebarOpen ? e(MenuFoldOutlined) : e(MenuUnfoldOutlined),
      keywords: ['left', 'sidebar', 'palette', 'devices'],
      execute: () => deps.toggleLeftSidebar(),
    },
    {
      id: 'panel:right-sidebar',
      label: deps.rightSidebarOpen ? 'Hide Properties Panel' : 'Show Properties Panel',
      category: 'panel',
      context: 'studio',
      icon: deps.rightSidebarOpen ? e(MenuFoldOutlined) : e(MenuUnfoldOutlined),
      keywords: ['right', 'sidebar', 'properties', 'ai', 'deploy'],
      execute: () => deps.toggleRightSidebar(),
    },
    {
      id: 'panel:minimap',
      label: deps.minimapVisible ? 'Hide Minimap' : 'Show Minimap',
      category: 'panel',
      context: 'studio',
      icon: deps.minimapVisible ? e(EyeInvisibleOutlined) : e(EyeOutlined),
      keywords: ['map', 'overview'],
      execute: () => deps.toggleMinimap(),
    },
    {
      id: 'panel:bottom',
      label: deps.bottomPanelOpen ? 'Hide Bottom Panel' : 'Show Bottom Panel',
      category: 'panel',
      context: 'studio',
      icon: deps.bottomPanelOpen ? e(EyeInvisibleOutlined) : e(EyeOutlined),
      keywords: ['timeline', 'phases'],
      execute: () => deps.toggleBottomPanel(),
    },
  );

  // ── Grouping ───────────────────────────────────────────────

  const groupItems: Array<{ mode: ClusterViewMode; label: string; icon: React.ReactNode; keywords?: string[] }> = [
    { mode: 'none', label: 'Group: None', icon: e(BlockOutlined), keywords: ['clear', 'reset', 'ungroup'] },
    { mode: 'zone', label: 'Group by Zone', icon: e(PartitionOutlined), keywords: ['network', 'segment'] },
    { mode: 'protocol', label: 'Group by Protocol', icon: e(ApiOutlined), keywords: ['modbus', 'ethernet', 'profinet'] },
    { mode: 'vendor', label: 'Group by Vendor', icon: e(ShopOutlined), keywords: ['manufacturer', 'siemens', 'rockwell'] },
    { mode: 'purdueLevel', label: 'Group by Purdue Level', icon: e(BuildOutlined), keywords: ['ics', 'hierarchy'] },
    { mode: 'deviceType', label: 'Group by Device Type', icon: e(AppstoreOutlined), keywords: ['plc', 'hmi', 'rtu'] },
  ];

  groupItems.forEach(({ mode, label, icon, keywords }) => {
    commands.push({
      id: `group:${mode}`,
      label,
      category: 'grouping',
      context: 'studio',
      icon,
      shortcut: mode === 'none' ? undefined : 'G',
      keywords,
      execute: () => {
        deps.setClusterViewMode(mode);
        setTimeout(() => deps.fitView(), 50);
      },
    });
  });

  // ── Scenario Actions ───────────────────────────────────────

  commands.push(
    {
      id: 'scenario:save-version',
      label: 'Save Version',
      category: 'scenario',
      context: 'studio',
      icon: e(SaveOutlined),
      shortcut: `${MOD}+S`,
      disabled: !deps.scenarioId,
      execute: () => deps.saveVersion(),
    },
    {
      id: 'scenario:version-history',
      label: 'View Version History',
      category: 'scenario',
      context: 'studio',
      icon: e(HistoryOutlined),
      disabled: !deps.scenarioId,
      keywords: ['rollback', 'restore', 'diff'],
      execute: () => deps.openVersionHistory(),
    },
    ...(deps.aiEnabled
      ? [{
          id: 'scenario:customize-names',
          label: 'Customize Device Names (AI)',
          category: 'scenario' as const,
          context: 'studio' as const,
          icon: e(EditOutlined),
          keywords: ['rename', 'ai', 'generate'],
          execute: () => deps.openCustomizeNames(),
        }]
      : []),
    {
      id: 'scenario:new',
      label: 'Create New Scenario',
      category: 'scenario',
      context: 'global',
      icon: e(PlusOutlined),
      keywords: ['add', 'create', 'scenario'],
      execute: () => deps.navigate('/scenarios'),
    },
  );

  // ── Help ───────────────────────────────────────────────────

  commands.push(
    {
      id: 'help:docs',
      label: 'Open Help & Documentation',
      category: 'help',
      context: 'global',
      icon: e(QuestionCircleOutlined),
      keywords: ['documentation', 'guide', 'faq'],
      execute: () => deps.navigate('/help'),
    },
  );

  return commands;
}
