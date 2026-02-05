/**
 * Canvas controls toolbar (zoom, fit view, undo/redo, delete, layout, customize names)
 */

import React, { useState } from 'react';
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
} from '@ant-design/icons';
import { useReactFlow } from '@xyflow/react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useHistoryStore } from '../../stores/historyStore';
import { useUIStore } from '../../stores/uiStore';
import { useScenarioStore } from '../../stores/scenarioStore';
import { useAutoLayout, type LayoutType } from './hooks/useAutoLayout';
import { scenariosApi } from '../../api/scenarios';

const CanvasControls: React.FC = () => {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const { zoomIn, zoomOut, fitView } = useReactFlow();
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
  const { applyLayout } = useAutoLayout();

  // Customize Names modal state
  const [customizeNamesModalOpen, setCustomizeNamesModalOpen] = useState(false);
  const [processContext, setProcessContext] = useState('');

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
    onError: (error: any) => {
      const detail = error.response?.data?.detail || error.message || 'Unknown error';
      message.error(`Failed to regenerate names: ${detail}`);
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

  const buttonStyle = {
    background: '#253545',
    borderColor: '#3a5068',
    color: '#b8c9dc',
  };

  return (
    <div
      style={{
        background: '#1a2734',
        padding: '8px',
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
        border: '1px solid #2a3f54',
      }}
    >
      <Space>
        {/* Zoom controls */}
        <Tooltip title="Zoom In">
          <Button icon={<ZoomInOutlined />} onClick={() => zoomIn()} style={buttonStyle} />
        </Tooltip>
        <Tooltip title="Zoom Out">
          <Button icon={<ZoomOutOutlined />} onClick={() => zoomOut()} style={buttonStyle} />
        </Tooltip>
        <Tooltip title="Fit View">
          <Button icon={<ExpandOutlined />} onClick={() => fitView()} style={buttonStyle} />
        </Tooltip>

        {/* Divider */}
        <div style={{ width: 1, height: 24, background: '#3a5068' }} />

        {/* History controls */}
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

        {/* Divider */}
        <div style={{ width: 1, height: 24, background: '#3a5068' }} />

        {/* Delete control */}
        <Tooltip title="Delete Selected">
          <Button
            icon={<DeleteOutlined />}
            onClick={handleDelete}
            disabled={selectedNodeIds.length === 0}
            danger
          />
        </Tooltip>

        {/* Divider */}
        <div style={{ width: 1, height: 24, background: '#3a5068' }} />

        {/* Minimap toggle */}
        <Tooltip title={minimapVisible ? 'Hide Minimap' : 'Show Minimap'}>
          <Button
            icon={minimapVisible ? <EyeInvisibleOutlined /> : <EyeOutlined />}
            onClick={toggleMinimap}
            style={buttonStyle}
          />
        </Tooltip>

        {/* Divider */}
        <div style={{ width: 1, height: 24, background: '#3a5068' }} />

        {/* Layout dropdown */}
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

        {/* Divider */}
        <div style={{ width: 1, height: 24, background: '#3a5068' }} />

        {/* Customize Names button */}
        <Tooltip title="Customize device names using AI based on your facility description">
          <Button
            icon={<EditOutlined />}
            style={buttonStyle}
            onClick={() => setCustomizeNamesModalOpen(true)}
            disabled={deviceCount === 0}
          >
            Customize Names
          </Button>
        </Tooltip>
      </Space>

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
