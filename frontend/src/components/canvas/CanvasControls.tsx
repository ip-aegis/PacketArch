/**
 * Canvas controls toolbar (zoom, fit view, undo/redo, delete, layout)
 */

import React from 'react';
import { Button, Space, Tooltip, Dropdown } from 'antd';
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
} from '@ant-design/icons';
import { useReactFlow } from '@xyflow/react';
import { useHistoryStore } from '../../stores/historyStore';
import { useUIStore } from '../../stores/uiStore';
import { useScenarioStore } from '../../stores/scenarioStore';
import { useAutoLayout, type LayoutType } from './hooks/useAutoLayout';

const CanvasControls: React.FC = () => {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  const undo = useHistoryStore((state) => state.undo);
  const redo = useHistoryStore((state) => state.redo);
  const canUndo = useHistoryStore((state) => state.canUndo());
  const canRedo = useHistoryStore((state) => state.canRedo());
  const selectedNodeIds = useUIStore((state) => state.selectedNodeIds);
  const removeDevice = useScenarioStore((state) => state.removeDevice);
  const minimapVisible = useUIStore((state) => state.panels.minimapVisible);
  const toggleMinimap = useUIStore((state) => state.toggleMinimap);
  const { applyLayout } = useAutoLayout();

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
      </Space>
    </div>
  );
};

export default CanvasControls;
