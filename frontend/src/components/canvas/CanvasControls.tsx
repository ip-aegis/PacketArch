/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Canvas controls toolbar (zoom, fit view, undo/redo, delete, layout, customize names)
 */

import React, { useState, useEffect } from 'react';
import { Button, Space, Tooltip, Dropdown, Modal, Input, App, Checkbox } from 'antd';
import type { MenuProps } from 'antd';
import {
  ZoomInOutlined,
  ZoomOutOutlined,
  ExpandOutlined,
  UndoOutlined,
  RedoOutlined,
  DeleteOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  LayoutOutlined,
  DragOutlined,
  BuildOutlined,
  NodeIndexOutlined,
  AppstoreOutlined,
  RadiusSettingOutlined,
  EditOutlined,
  SaveOutlined,
  HistoryOutlined,
  BlockOutlined,
  PartitionOutlined,
  ApiOutlined,
  ShopOutlined,
  GroupOutlined,
  FileSearchOutlined,
  SafetyOutlined,
  WifiOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useReactFlow, useViewport } from '@xyflow/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useHistoryStore } from '../../stores/historyStore';
import { useUIStore } from '../../stores/uiStore';
import type { ClusterViewMode } from '../../stores/uiStore';
import { useScenarioStore, useScenarioIsDirty } from '../../stores/scenarioStore';
import { useAutoLayout, type LayoutType } from './hooks/useAutoLayout';
import { scenariosApi } from '../../api/scenarios';
import { scenarioVersionsApi } from '../../api/scenarioVersions';
import { extractErrorMessage } from '../../utils/errorUtils';
import { useFeatures } from '../../hooks/useFeatures';
import VersionHistoryDrawer from './VersionHistoryDrawer';
import ScenarioReviewDrawer from './ScenarioReviewDrawer';
import CellIsolationControl from './CellIsolationControl';
import RationalityBadge from './RationalityBadge';

const CanvasControls: React.FC = () => {
  const { message } = App.useApp();
  const { aiEnabled } = useFeatures();
  const queryClient = useQueryClient();
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  const { zoom } = useViewport();
  const undo = useHistoryStore((state) => state.undo);
  const redo = useHistoryStore((state) => state.redo);
  const canUndo = useHistoryStore((state) => state.canUndo());
  const canRedo = useHistoryStore((state) => state.canRedo());
  const selectedNodeIds = useUIStore((state) => state.selectedNodeIds);
  const removeDevice = useScenarioStore((state) => state.removeDevice);
  const scenarioId = useScenarioStore((state) => state.id);
  const deviceCount = useScenarioStore((state) => Object.keys(state.devices).length);
  const minimapVisible = useUIStore((state) => state.panels.minimapVisible);
  const toggleMinimap = useUIStore((state) => state.toggleMinimap);
  const showFlows = useUIStore((s) => s.panels.showFlows);
  const showConduits = useUIStore((s) => s.panels.showConduits);
  const aggregateFlows = useUIStore((s) => s.panels.aggregateFlows);
  const toggleShowFlows = useUIStore((s) => s.toggleShowFlows);
  const toggleShowConduits = useUIStore((s) => s.toggleShowConduits);
  const toggleAggregateFlows = useUIStore((s) => s.toggleAggregateFlows);
  const clusterViewMode = useUIStore((state) => state.clusterViewMode);
  const setClusterViewMode = useUIStore((state) => state.setClusterViewMode);
  const isDirty = useScenarioIsDirty();
  const { applyLayout } = useAutoLayout();
  const scenarioName = useScenarioStore((s) => s.name);
  const scenarioVertical = useScenarioStore((s) => s.vertical);
  const scenarioIpRange = useScenarioStore((s) => s.ipRange);
  const broadcastTrafficEnabled = useScenarioStore((s) => s.broadcastTrafficEnabled);
  const setBroadcastTrafficEnabled = useScenarioStore((s) => s.setBroadcastTrafficEnabled);
  const cleanDemoMode = useScenarioStore((s) => s.cleanDemoMode);
  const setCleanDemoMode = useScenarioStore((s) => s.setCleanDemoMode);

  // Version history drawer state
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [savingVersion, setSavingVersion] = useState(false);

  // Review drawer state
  const [reviewDrawerOpen, setReviewDrawerOpen] = useState(false);

  // Customize Names modal state
  const [customizeNamesModalOpen, setCustomizeNamesModalOpen] = useState(false);
  const [processContext, setProcessContext] = useState('');
  const [descriptiveNames, setDescriptiveNames] = useState(false);

  // Listen for command palette events
  useEffect(() => {
    const onOpenHistory = () => setHistoryDrawerOpen(true);
    const onOpenNames = () => setCustomizeNamesModalOpen(true);
    window.addEventListener('command-palette:open-version-history', onOpenHistory);
    window.addEventListener('command-palette:open-customize-names', onOpenNames);
    return () => {
      window.removeEventListener('command-palette:open-version-history', onOpenHistory);
      window.removeEventListener('command-palette:open-customize-names', onOpenNames);
    };
  }, []);

  // Regenerate names mutation
  const regenerateNamesMutation = useMutation({
    mutationFn: (data: { scenarioId: string; processContext: string; descriptiveNames: boolean }) =>
      scenariosApi.regenerateDeviceNames(data.scenarioId, {
        process_context: data.processContext,
        descriptive_names: data.descriptiveNames,
      }),
    onSuccess: async (result) => {
      message.success(`${result.devices_renamed} device names updated`);
      setCustomizeNamesModalOpen(false);
      setProcessContext('');
      setDescriptiveNames(false);
      // Refetch the scenario and push it into the Zustand store so the
      // canvas redraws with the new device/zone names. Invalidating the
      // React Query alone doesn't update the local studio store.
      if (scenarioId) {
        try {
          const fresh = await scenariosApi.get(scenarioId);
          const defn = (fresh.definition || {}) as {
            devices?: Record<string, import('../../types').ScenarioDevice>;
            flows?: Record<string, import('../../types').ScenarioFlow>;
            zones?: Record<string, import('../../types').ScenarioZone>;
            conduits?: Record<string, import('../../types').ScenarioConduit>;
            phases?: import('../../types').Phase[];
            cell_isolation?: import('../../types').CellIsolationConfig;
            broadcast_traffic_enabled?: boolean;
            clean_demo_mode?: boolean;
          };
          useScenarioStore.getState().loadScenario({
            id: fresh.id,
            name: fresh.name,
            description: fresh.description || '',
            vertical: fresh.vertical || undefined,
            totalDurationMs: fresh.total_duration_ms,
            devices: defn.devices || {},
            flows: defn.flows || {},
            zones: defn.zones || {},
            conduits: defn.conduits || {},
            phases: defn.phases || [],
            cellIsolation: defn.cell_isolation,
            broadcastTrafficEnabled: defn.broadcast_traffic_enabled,
            cleanDemoMode: defn.clean_demo_mode,
            addressingConfig: fresh.addressing_config as {
              ip_range?: string;
              range_index?: number;
              auto_assign_enabled?: boolean;
            } | null,
          });
        } catch (err) {
          console.error('Failed to reload scenario after rename:', err);
        }
        queryClient.invalidateQueries({ queryKey: ['scenario', scenarioId] });
      }
    },
    onError: (error: unknown) => {
      message.error(`Failed to regenerate names: ${extractErrorMessage(error, 'Unknown error')}`);
    },
  });

  const handleCustomizeNames = () => {
    if (!processContext.trim()) {
      message.error('Please describe your facility or process');
      return;
    }
    if (!scenarioId) {
      message.error('No scenario loaded');
      return;
    }
    regenerateNamesMutation.mutate({
      scenarioId,
      processContext: processContext.trim(),
      descriptiveNames,
    });
  };

  const handleSaveVersion = async () => {
    if (!scenarioId) {
      message.error('No scenario loaded');
      return;
    }
    setSavingVersion(true);
    try {
      const version = await scenarioVersionsApi.create(scenarioId);
      message.success(`Version ${version.version_number} saved`);
    } catch (error: unknown) {
      message.error(`Failed to save version: ${extractErrorMessage(error, 'Unknown error')}`);
    } finally {
      setSavingVersion(false);
    }
  };

  const handleDelete = () => {
    selectedNodeIds.forEach((nodeId) => {
      removeDevice(nodeId);
    });
  };

  const handleAutoGenerateConduits = () => {
    const { zones, conduits, addConduit } = useScenarioStore.getState();
    const zoneList = Object.values(zones);
    if (zoneList.length < 2) {
      message.info('Need at least 2 zones with Purdue levels to generate conduits');
      return;
    }

    // Purdue adjacency pairs
    const adjacency: [number, number][] = [
      [0, 1], [1, 2], [2, 3], [3, 3.5], [3.5, 4],
    ];
    const defaultProtocols: Record<string, string[]> = {
      '0-1': ['profinet', 'ethernet_ip', 'modbus_tcp'],
      '1-2': ['s7comm', 'ethernet_ip', 'modbus_tcp', 'profinet', 'bacnet'],
      '2-3': ['modbus_tcp', 'ethernet_ip', 'snmp', 'bacnet'],
      '3-3.5': ['snmp'],
      '3.5-4': ['snmp'],
    };

    const existing = Object.values(conduits);
    const newConduits: Array<{ id: string; name: string; sourceZoneId: string; targetZoneId: string; direction: 'bidirectional'; allowedProtocols: string[]; autoGenerated: boolean }> = [];

    for (let i = 0; i < zoneList.length; i++) {
      for (let j = i + 1; j < zoneList.length; j++) {
        const z1 = zoneList[i];
        const z2 = zoneList[j];
        if (z1.level == null || z2.level == null) continue;

        const pair: [number, number] = [Math.min(z1.level, z2.level), Math.max(z1.level, z2.level)];
        if (!adjacency.some(([a, b]) => a === pair[0] && b === pair[1])) continue;

        // Check duplicate
        const isDuplicate = existing.some(
          (c) =>
            (c.sourceZoneId === z1.id && c.targetZoneId === z2.id) ||
            (c.sourceZoneId === z2.id && c.targetZoneId === z1.id)
        );
        if (isDuplicate) continue;

        const lower = z1.level <= z2.level ? z1 : z2;
        const upper = z1.level <= z2.level ? z2 : z1;
        const key = `${pair[0]}-${pair[1]}`;

        const conduitId = `conduit-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        newConduits.push({
          id: conduitId,
          name: `${lower.name} \u2194 ${upper.name}`,
          sourceZoneId: lower.id,
          targetZoneId: upper.id,
          direction: 'bidirectional',
          allowedProtocols: (defaultProtocols[key] || []) as string[],
          autoGenerated: true,
        });
      }
    }

    if (newConduits.length === 0) {
      message.info('No new conduits to generate. Ensure zones have Purdue levels assigned.');
      return;
    }

    newConduits.forEach((c) => addConduit(c as import('../../types').ScenarioConduit));
    message.success(`Generated ${newConduits.length} conduit(s) from Purdue adjacency`);
  };

  const handleLayoutSelect: MenuProps['onClick'] = ({ key }) => {
    if (key !== 'manual') {
      applyLayout(key as LayoutType);
      // Fit view after layout with slight delay for animation
      setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 50);
    }
  };

  const layoutMenuItems: MenuProps['items'] = [
    {
      key: 'manual',
      icon: <DragOutlined />,
      label: 'Manual (Current)',
    },
    { type: 'divider' },
    {
      key: 'purdue',
      icon: <BuildOutlined />,
      label: 'Purdue Model',
    },
    {
      key: 'dataflow',
      icon: <NodeIndexOutlined />,
      label: 'Data Flow',
    },
    {
      key: 'grid',
      icon: <AppstoreOutlined />,
      label: 'Grid',
    },
    {
      key: 'circular',
      icon: <RadiusSettingOutlined />,
      label: 'Circular',
    },
  ];

  const handleGroupSelect: MenuProps['onClick'] = ({ key }) => {
    setClusterViewMode(key as ClusterViewMode);
    setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 50);
  };

  const GROUP_MODE_LABELS: Record<ClusterViewMode, string> = {
    none: 'Group',
    zone: 'By Zone',
    protocol: 'By Protocol',
    vendor: 'By Vendor',
    purdueLevel: 'By Purdue',
    deviceType: 'By Type',
  };

  const groupMenuItems: MenuProps['items'] = [
    { key: 'none', icon: <BlockOutlined />, label: 'No Grouping' },
    { type: 'divider' },
    { key: 'zone', icon: <PartitionOutlined />, label: 'By Zone' },
    { key: 'protocol', icon: <ApiOutlined />, label: 'By Protocol' },
    { key: 'vendor', icon: <ShopOutlined />, label: 'By Vendor' },
    { key: 'purdueLevel', icon: <BuildOutlined />, label: 'By Purdue Level' },
    { key: 'deviceType', icon: <AppstoreOutlined />, label: 'By Device Type' },
  ];

  const buttonStyle = {
    background: '#253545',
    borderColor: '#3a5068',
    color: '#b8c9dc',
  };

  const groupLabelStyle: React.CSSProperties = {
    fontSize: '9px',
    color: 'rgba(184,201,220,0.45)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: '2px',
    lineHeight: 1,
    userSelect: 'none',
  };

  const groupStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  };

  const groupButtonsStyle: React.CSSProperties = {
    display: 'flex',
    gap: '4px',
  };

  const dividerStyle: React.CSSProperties = {
    width: 1,
    alignSelf: 'stretch',
    background: '#3a5068',
    margin: '0 2px',
  };

  return (
    <div
      style={{
        background: '#1a2734',
        padding: '6px 8px',
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
        border: '1px solid #2a3f54',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'stretch',
        rowGap: '6px',
        gap: '6px',
        // Bound width to the available canvas so wrapped rows don't extend
        // past the right-side panel.
        maxWidth: 'calc(100vw - 80px)',
      }}
    >
      {/* Scenario title row — name + at-a-glance metadata so the user
          always knows which scenario they are editing. Lives inside the
          toolbar so it can never overlap menu buttons regardless of
          how the toolbar wraps. */}
      {scenarioName && (
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: 10,
            padding: '2px 4px 4px',
            borderBottom: '1px solid #2a3f54',
            minWidth: 0,
          }}
        >
          <span
            style={{
              color: '#e0e8f0',
              fontWeight: 600,
              fontSize: 13,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
            title={scenarioName}
          >
            {scenarioName}
          </span>
          {scenarioVertical && (
            <span
              style={{
                color: '#8aa4bc',
                fontSize: 11,
                textTransform: 'capitalize',
                whiteSpace: 'nowrap',
              }}
            >
              {scenarioVertical.replace(/_/g, ' ')}
            </span>
          )}
          {scenarioIpRange?.cidr && (
            <span
              style={{
                color: '#8aa4bc',
                fontSize: 11,
                fontFamily: 'monospace',
                whiteSpace: 'nowrap',
              }}
            >
              {scenarioIpRange.cidr}
            </span>
          )}
        </div>
      )}

      {/* Button rows — wrap as needed within the toolbar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          rowGap: '6px',
          gap: '6px',
        }}
      >
      {/* View group */}
      <div style={groupStyle}>
        <span style={groupLabelStyle}>View</span>
        <div style={groupButtonsStyle}>
          <Tooltip title="Zoom In">
            <Button icon={<ZoomInOutlined />} onClick={() => zoomIn()} style={buttonStyle} />
          </Tooltip>
          <Tooltip title="Zoom Out">
            <Button icon={<ZoomOutOutlined />} onClick={() => zoomOut()} style={buttonStyle} />
          </Tooltip>
          <Tooltip title="Fit View">
            <Button icon={<ExpandOutlined />} onClick={() => fitView()} style={buttonStyle} />
          </Tooltip>
          <span
            style={{
              fontSize: '10px',
              color: '#b8c9dc',
              minWidth: '32px',
              textAlign: 'center',
              fontFamily: 'monospace',
              lineHeight: '32px',
            }}
          >
            {Math.round(zoom * 100)}%
          </span>
        </div>
      </div>

      <div style={dividerStyle} />

      {/* Edit group */}
      <div style={groupStyle}>
        <span style={groupLabelStyle}>Edit</span>
        <div style={groupButtonsStyle}>
          <Tooltip title="Undo">
            <Button
              icon={<UndoOutlined />}
              onClick={undo}
              disabled={!canUndo}
              style={buttonStyle}
            />
          </Tooltip>
          <Tooltip title="Redo">
            <Button
              icon={<RedoOutlined />}
              onClick={redo}
              disabled={!canRedo}
              style={buttonStyle}
            />
          </Tooltip>
          <Tooltip title="Delete Selected">
            <Button
              icon={<DeleteOutlined />}
              onClick={handleDelete}
              disabled={selectedNodeIds.length === 0}
              danger
            />
          </Tooltip>
        </div>
      </div>

      <div style={dividerStyle} />

      {/* Conduit group */}
      <div style={groupStyle}>
        <span style={groupLabelStyle}>Conduit</span>
        <div style={groupButtonsStyle}>
          <Tooltip title="Draw conduit between zones (C)">
            <Button
              icon={<SafetyOutlined />}
              onClick={() => {
                const tool = useUIStore.getState().tool.activeTool;
                useUIStore.getState().setActiveTool(tool === 'conduit' ? 'select' : 'conduit');
              }}
              style={{
                ...buttonStyle,
                ...(useUIStore.getState().tool.activeTool === 'conduit'
                  ? { borderColor: '#049FD9', color: '#049FD9' }
                  : {}),
              }}
            />
          </Tooltip>
          <Tooltip title="Auto-generate conduits from Purdue adjacency">
            <Button
              icon={<BuildOutlined />}
              onClick={handleAutoGenerateConduits}
              style={buttonStyle}
            >
              Auto
            </Button>
          </Tooltip>
        </div>
      </div>

      <div style={dividerStyle} />

      {/* Cell isolation group — Purdue-aware east/west enforcement */}
      <div style={groupStyle}>
        <span style={groupLabelStyle}>Cell Isolation</span>
        <div style={groupButtonsStyle}>
          <CellIsolationControl scenarioId={scenarioId} buttonStyle={buttonStyle} />
        </div>
      </div>

      <div style={dividerStyle} />

      {/* Ambient traffic group — broadcast/multicast generator toggle */}
      <div style={groupStyle}>
        <span style={groupLabelStyle}>Ambient</span>
        <div style={groupButtonsStyle}>
          <Tooltip
            title={
              broadcastTrafficEnabled
                ? 'Broadcast/multicast traffic ON: ARP, NTP, LLDP, STP, CDP, DHCP, IGMP, BACnet Who-Is, PROFINET DCP, SNMP traps. Click to disable.'
                : 'Broadcast/multicast traffic OFF: no ambient noise generated. Click to enable.'
            }
          >
            <Button
              icon={<WifiOutlined />}
              onClick={() => setBroadcastTrafficEnabled(!broadcastTrafficEnabled)}
              style={{
                ...buttonStyle,
                ...(broadcastTrafficEnabled
                  ? { borderColor: '#049FD9', color: '#049FD9' }
                  : { opacity: 0.5 }),
              }}
            >
              {broadcastTrafficEnabled ? 'Broadcast On' : 'Broadcast Off'}
            </Button>
          </Tooltip>
          <Tooltip
            title={
              cleanDemoMode
                ? 'Clean Demo Mode ON: cyclic protocol traffic that creates phantom components in DPI tools is suppressed (currently PROFINET PN-IO). Discovery, AR setup, alarms, and identification frames still fire. Click to disable.'
                : 'Clean Demo Mode OFF: full protocol traffic including PROFINET cyclic I/O. Recommended ON for asset-classification demos in CV. Click to enable.'
            }
          >
            <Button
              icon={<ExperimentOutlined />}
              onClick={() => setCleanDemoMode(!cleanDemoMode)}
              style={{
                ...buttonStyle,
                ...(cleanDemoMode
                  ? { borderColor: '#FBAB18', color: '#FBAB18' }
                  : { opacity: 0.6 }),
              }}
            >
              {cleanDemoMode ? 'Clean Demo' : 'Full Traffic'}
            </Button>
          </Tooltip>
        </div>
      </div>

      <div style={dividerStyle} />

      {/* Edges group — visibility toggles + aggregation */}
      <div style={groupStyle}>
        <span style={groupLabelStyle}>Edges</span>
        <div style={groupButtonsStyle}>
          <Tooltip title={showFlows ? 'Hide flow edges' : 'Show flow edges'}>
            <Button
              icon={<NodeIndexOutlined />}
              onClick={toggleShowFlows}
              style={{
                ...buttonStyle,
                ...(showFlows ? {} : { opacity: 0.5 }),
                borderColor: showFlows ? '#049FD9' : undefined,
                color: showFlows ? '#049FD9' : undefined,
              }}
            >
              Flows
            </Button>
          </Tooltip>
          <Tooltip title={showConduits ? 'Hide conduit edges' : 'Show conduit edges'}>
            <Button
              icon={<SafetyOutlined />}
              onClick={toggleShowConduits}
              style={{
                ...buttonStyle,
                ...(showConduits ? {} : { opacity: 0.5 }),
                borderColor: showConduits ? '#52c41a' : undefined,
                color: showConduits ? '#52c41a' : undefined,
              }}
            >
              Conduits
            </Button>
          </Tooltip>
          <Tooltip title={
            aggregateFlows
              ? 'Stop aggregating: show every flow as its own edge'
              : 'Aggregate flows by zone-pair (one edge per source-zone → target-zone, with a count)'
          }>
            <Button
              icon={<GroupOutlined />}
              onClick={toggleAggregateFlows}
              style={{
                ...buttonStyle,
                ...(aggregateFlows ? { borderColor: '#FBAB18', color: '#FBAB18' } : {}),
              }}
            >
              {aggregateFlows ? 'Aggregated' : 'Per-flow'}
            </Button>
          </Tooltip>
        </div>
      </div>

      <div style={dividerStyle} />

      {/* Map group */}
      <div style={groupStyle}>
        <span style={groupLabelStyle}>Map</span>
        <div style={groupButtonsStyle}>
          <Tooltip title={minimapVisible ? 'Hide Minimap' : 'Show Minimap'}>
            <Button
              icon={minimapVisible ? <EyeInvisibleOutlined /> : <EyeOutlined />}
              onClick={toggleMinimap}
              style={buttonStyle}
            />
          </Tooltip>
        </div>
      </div>

      <div style={dividerStyle} />

      {/* Layout group */}
      <div style={groupStyle}>
        <span style={groupLabelStyle}>Layout</span>
        <div style={groupButtonsStyle}>
          <Dropdown
            menu={{ items: layoutMenuItems, onClick: handleLayoutSelect }}
            trigger={['click']}
          >
            <Tooltip title="Auto-arrange Layout">
              <Button icon={<LayoutOutlined />} style={buttonStyle}>
                Layout
              </Button>
            </Tooltip>
          </Dropdown>
        </div>
      </div>

      <div style={dividerStyle} />

      {/* Group-by cluster view */}
      <div style={groupStyle}>
        <span style={groupLabelStyle}>Group</span>
        <div style={groupButtonsStyle}>
          <Dropdown
            menu={{ items: groupMenuItems, onClick: handleGroupSelect }}
            trigger={['click']}
          >
            <Tooltip title="Group devices by attribute (G)">
              <Button
                icon={<GroupOutlined />}
                style={
                  clusterViewMode !== 'none'
                    ? { ...buttonStyle, borderColor: '#049FD9', color: '#049FD9' }
                    : buttonStyle
                }
              >
                {GROUP_MODE_LABELS[clusterViewMode]}
              </Button>
            </Tooltip>
          </Dropdown>
        </div>
      </div>

      <div style={dividerStyle} />

      {/* Names group */}
      <div style={groupStyle}>
        <span style={groupLabelStyle}>Names</span>
        <div style={groupButtonsStyle}>
          <Tooltip title="Customize device names using AI based on your facility description">
            <Button
              icon={<EditOutlined />}
              style={buttonStyle}
              onClick={() => setCustomizeNamesModalOpen(true)}
              disabled={deviceCount === 0}
            >
              Customize
            </Button>
          </Tooltip>
        </div>
      </div>

      <div style={dividerStyle} />

      {/* Review group — AI-powered (when enabled) plus the always-on
          architecture rationality badge. */}
      <div style={groupStyle}>
        <span style={groupLabelStyle}>Review</span>
        <div style={{ ...groupButtonsStyle, alignItems: 'center' }}>
          <RationalityBadge />
          {aiEnabled && (
            <Tooltip title="AI Scenario Review">
              <Button
                icon={<FileSearchOutlined />}
                style={buttonStyle}
                onClick={() => setReviewDrawerOpen(true)}
                disabled={deviceCount === 0 || !scenarioId}
              >
                Review
              </Button>
            </Tooltip>
          )}
        </div>
      </div>

      <div style={dividerStyle} />

      {/* Version group */}
      <div style={groupStyle}>
        <span style={groupLabelStyle}>Version</span>
        <div style={{ ...groupButtonsStyle, alignItems: 'center' }}>
          <Tooltip title="Save Version (Ctrl+S)">
            <Button
              icon={<SaveOutlined />}
              style={buttonStyle}
              onClick={handleSaveVersion}
              loading={savingVersion}
              disabled={!scenarioId}
            />
          </Tooltip>
          <Tooltip title="Version History">
            <Button
              icon={<HistoryOutlined />}
              style={buttonStyle}
              onClick={() => setHistoryDrawerOpen(true)}
              disabled={!scenarioId}
            />
          </Tooltip>
          {scenarioId && (
            <span
              style={{
                fontSize: '10px',
                padding: '2px 6px',
                borderRadius: '4px',
                background: isDirty ? 'rgba(250, 140, 22, 0.15)' : 'rgba(82, 196, 26, 0.15)',
                color: isDirty ? '#fa8c16' : '#52c41a',
                border: `1px solid ${isDirty ? 'rgba(250, 140, 22, 0.3)' : 'rgba(82, 196, 26, 0.3)'}`,
                whiteSpace: 'nowrap',
              }}
            >
              {isDirty ? 'Unsaved' : 'Saved'}
            </span>
          )}
        </div>
      </div>
      </div>

      {/* Version History Drawer */}
      <VersionHistoryDrawer
        scenarioId={scenarioId}
        open={historyDrawerOpen}
        onClose={() => setHistoryDrawerOpen(false)}
      />

      {/* Scenario Review Drawer */}
      <ScenarioReviewDrawer
        scenarioId={scenarioId}
        open={reviewDrawerOpen}
        onClose={() => setReviewDrawerOpen(false)}
      />

      {/* Customize Names Modal */}
      <Modal
        title="Customize Device Names"
        open={customizeNamesModalOpen}
        onOk={handleCustomizeNames}
        onCancel={() => {
          setCustomizeNamesModalOpen(false);
          setProcessContext('');
          setDescriptiveNames(false);
        }}
        confirmLoading={regenerateNamesMutation.isPending}
        okText="Generate Names"
        okButtonProps={{ disabled: !processContext.trim() }}
        styles={{
          header: { background: '#141428', borderBottom: '1px solid #2d2d52' },
          body: { background: '#1a1a2e', padding: 24 },
          content: { background: '#141428' },
        }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <div style={{ color: '#a8a8c0' }}>
            Describe your industrial process and AI will generate contextual device names
            that reflect your specific facility.
          </div>

          <Input.TextArea
            value={processContext}
            onChange={(e) => setProcessContext(e.target.value)}
            placeholder="e.g., 'candy factory with chocolate tempering line and packaging'"
            rows={3}
            maxLength={200}
            showCount
            style={{
              background: '#141428',
              border: '1px solid #2d2d52',
              color: '#fff',
            }}
          />

          <div
            style={{
              background: '#1f1f3a',
              border: '1px solid #2d2d52',
              borderRadius: 8,
              padding: 12,
            }}
          >
            <Checkbox
              checked={descriptiveNames}
              onChange={(e) => setDescriptiveNames(e.target.checked)}
              style={{ color: '#e6e6f0' }}
            >
              Demo-friendly descriptive names
            </Checkbox>
            <div style={{ color: '#8a8aa8', fontSize: 12, marginTop: 6, marginLeft: 24 }}>
              Overlay longer, human-readable labels on top of the structured
              site names. SNMP and fingerprint identifiers stay canonical so
              Cyber Vision matching still works.
            </div>
          </div>

          <div
            style={{
              background: '#253545',
              border: '1px solid #3a5068',
              borderRadius: 8,
              padding: 12,
            }}
          >
            <div style={{ color: '#5a9fd4', fontWeight: 500, marginBottom: 4 }}>
              {descriptiveNames ? 'Descriptive (demo)' : 'Structured (default)'}
            </div>
            <div style={{ color: '#a8a8c0', fontSize: 12 }}>
              <span style={{ color: '#6b6b8a' }}>Before:</span> CNC_Machining_Main_PLC
            </div>
            <div style={{ color: '#a8a8c0', fontSize: 12 }}>
              <span style={{ color: '#6b6b8a' }}>After:</span>{' '}
              {descriptiveNames ? 'Chocolate_Tempering_PLC' : 'PDX-CDY-MIX-PLC-01'}
            </div>
          </div>
        </Space>
      </Modal>
    </div>
  );
};

export default CanvasControls;
