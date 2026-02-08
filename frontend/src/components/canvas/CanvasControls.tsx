/**
 * Canvas controls toolbar (zoom, fit view, undo/redo, delete, layout, customize names)
 */

import React, { useState, useEffect } from 'react';
import { Button, Space, Tooltip, Dropdown, Modal, Input, App } from 'antd';
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
} from '@ant-design/icons';
import { useReactFlow, useViewport } from '@xyflow/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useHistoryStore } from '../../stores/historyStore';
import { useUIStore } from '../../stores/uiStore';
import type { ClusterViewMode } from '../../stores/uiStore';
import { useScenarioStore } from '../../stores/scenarioStore';
import { useAutoLayout, type LayoutType } from './hooks/useAutoLayout';
import { scenariosApi } from '../../api/scenarios';
import { scenarioVersionsApi } from '../../api/scenarioVersions';
import { extractErrorMessage } from '../../utils/errorUtils';
import VersionHistoryDrawer from './VersionHistoryDrawer';

const CanvasControls: React.FC = () => {
  const { message } = App.useApp();
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
  const clusterViewMode = useUIStore((state) => state.clusterViewMode);
  const setClusterViewMode = useUIStore((state) => state.setClusterViewMode);
  const { applyLayout } = useAutoLayout();

  // Version history drawer state
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [savingVersion, setSavingVersion] = useState(false);

  // Customize Names modal state
  const [customizeNamesModalOpen, setCustomizeNamesModalOpen] = useState(false);
  const [processContext, setProcessContext] = useState('');

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
    mutationFn: (data: { scenarioId: string; processContext: string }) =>
      scenariosApi.regenerateDeviceNames(data.scenarioId, { process_context: data.processContext }),
    onSuccess: (result) => {
      message.success(`${result.devices_renamed} device names updated`);
      setCustomizeNamesModalOpen(false);
      setProcessContext('');
      // Invalidate scenario query to reload with new names
      queryClient.invalidateQueries({ queryKey: ['scenario', scenarioId] });
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
    regenerateNamesMutation.mutate({ scenarioId, processContext: processContext.trim() });
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
        alignItems: 'center',
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

      {/* Version group */}
      <div style={groupStyle}>
        <span style={groupLabelStyle}>Version</span>
        <div style={groupButtonsStyle}>
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
        </div>
      </div>

      {/* Version History Drawer */}
      <VersionHistoryDrawer
        scenarioId={scenarioId}
        open={historyDrawerOpen}
        onClose={() => setHistoryDrawerOpen(false)}
      />

      {/* Customize Names Modal */}
      <Modal
        title="Customize Device Names"
        open={customizeNamesModalOpen}
        onOk={handleCustomizeNames}
        onCancel={() => {
          setCustomizeNamesModalOpen(false);
          setProcessContext('');
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
              background: '#253545',
              border: '1px solid #3a5068',
              borderRadius: 8,
              padding: 12,
            }}
          >
            <div style={{ color: '#5a9fd4', fontWeight: 500, marginBottom: 4 }}>
              Example Transformation
            </div>
            <div style={{ color: '#a8a8c0', fontSize: 12 }}>
              <span style={{ color: '#6b6b8a' }}>Before:</span> CNC_Machining_Main_PLC
            </div>
            <div style={{ color: '#a8a8c0', fontSize: 12 }}>
              <span style={{ color: '#6b6b8a' }}>After:</span> Chocolate_Tempering_PLC
            </div>
          </div>
        </Space>
      </Modal>
    </div>
  );
};

export default CanvasControls;
