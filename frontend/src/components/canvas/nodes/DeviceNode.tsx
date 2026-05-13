/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Custom React Flow node for OT devices
 * Enhanced visual design with color-coded device type icons
 */

import React, { useState } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { useCompactMode } from '../hooks/useCompactMode';
import { BugOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';
import type { ProtocolType } from '../../../types';
import { getDeviceTypeMeta, getDeviceTypeIcon } from '../../../constants/deviceTypeRegistry';

export interface DeviceNodeData extends Record<string, unknown> {
  id: string;
  name: string;
  type: string;
  role?: string;
  protocols: ProtocolType[];
  isConfigured: boolean;
  ipAddress?: string;
  cveIds?: string[];
  vendor?: string;
}

const DeviceNode: React.FC<NodeProps<DeviceNodeData>> = React.memo((props) => {
  const { data, selected } = props;
  const [hovered, setHovered] = useState(false);
  const rawCompact = useCompactMode();
  // Selected nodes always show full detail
  const isCompact = rawCompact && !selected;
  if (!data) return null;

  const nodeData = data as DeviceNodeData;
  const deviceMeta = getDeviceTypeMeta(nodeData.type);
  const deviceColor = deviceMeta.color;
  const deviceIcon = getDeviceTypeIcon(nodeData.type);
  const hasCves = !!(nodeData.cveIds && nodeData.cveIds.length > 0);

  const handleStyle = (pos: 'top' | 'bottom' | 'left' | 'right') => {
    const size = isCompact ? 8 : 10;
    const offset = isCompact ? -4 : -5;
    return {
      background: deviceColor,
      width: size,
      height: size,
      border: '2px solid #1e2a3a',
      [pos]: offset,
    };
  };

  if (isCompact) {
    return (
      <div
        role="treeitem"
        aria-label={`${deviceMeta.label}: ${nodeData.name}`}
        aria-selected={selected}
        tabIndex={0}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onContextMenu={(e) => {
          e.preventDefault();
          e.stopPropagation();
          window.dispatchEvent(
            new CustomEvent('device-context-menu', {
              detail: { deviceId: nodeData.id, x: e.clientX, y: e.clientY },
            }),
          );
        }}
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '4px',
          cursor: 'pointer',
          position: 'relative',
        }}
      >
        <Handle type="target" position={Position.Top} style={handleStyle('top')} />
        <Handle type="source" position={Position.Bottom} style={handleStyle('bottom')} />
        <Handle type="target" position={Position.Left} style={handleStyle('left')} />
        <Handle type="source" position={Position.Right} style={handleStyle('right')} />

        {/* Colored circle with icon */}
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: `linear-gradient(135deg, ${deviceColor}40, ${deviceColor}20)`,
            border: `2px solid ${hovered ? deviceColor : `${deviceColor}60`}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 16,
            color: deviceColor,
            boxShadow: hovered
              ? `0 0 12px ${deviceColor}50`
              : '0 1px 4px rgba(0,0,0,0.3)',
            transition: 'all 0.2s ease',
          }}
        >
          {deviceIcon}
        </div>

        {/* Name label */}
        <div
          style={{
            fontSize: 10,
            color: '#ffffff',
            fontWeight: 600,
            maxWidth: 70,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            textAlign: 'center',
            textShadow: '0 1px 3px rgba(0,0,0,0.8)',
          }}
        >
          {nodeData.name}
        </div>
      </div>
    );
  }

  return (
    <div
      role="treeitem"
      aria-label={`${deviceMeta.label} device: ${nodeData.name}${nodeData.vendor ? `, vendor ${nodeData.vendor}` : ''}${nodeData.ipAddress ? `, IP ${nodeData.ipAddress}` : ''}`}
      aria-selected={selected}
      tabIndex={0}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onContextMenu={(e) => {
        e.preventDefault();
        e.stopPropagation();
        window.dispatchEvent(
          new CustomEvent('device-context-menu', {
            detail: { deviceId: nodeData.id, x: e.clientX, y: e.clientY },
          }),
        );
      }}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '8px 10px',
        borderRadius: 10,
        background: '#1e2a3a',
        border: `2px solid ${selected ? deviceColor : 'rgba(255,255,255,0.08)'}`,
        boxShadow: selected
          ? `0 4px 20px ${deviceColor}40, 0 0 0 1px ${deviceColor}60`
          : '0 2px 8px rgba(0,0,0,0.3)',
        minWidth: 140,
        maxWidth: 200,
        transition: 'all 0.2s ease',
        cursor: 'pointer',
        position: 'relative',
      }}
    >
      {/* Connection handles */}
      <Handle type="target" position={Position.Top} style={handleStyle('top')} />
      <Handle type="source" position={Position.Bottom} style={handleStyle('bottom')} />
      <Handle type="target" position={Position.Left} style={handleStyle('left')} />
      <Handle type="source" position={Position.Right} style={handleStyle('right')} />

      {/* Icon block */}
      <div
        style={{
          flex: '0 0 auto',
          width: 32,
          height: 32,
          borderRadius: 8,
          background: `linear-gradient(135deg, ${deviceColor}30, ${deviceColor}15)`,
          border: `1px solid ${deviceColor}50`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 16,
          color: deviceColor,
        }}
      >
        {deviceIcon}
      </div>

      {/* Name + type */}
      <div style={{ flex: '1 1 auto', minWidth: 0 }}>
        <div
          style={{
            fontWeight: 600,
            fontSize: 12,
            color: '#ffffff',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            lineHeight: 1.3,
          }}
        >
          {nodeData.name}
        </div>
        <div
          style={{
            fontSize: 10,
            color: 'rgba(255,255,255,0.45)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            marginTop: 1,
          }}
        >
          {deviceMeta.label}
        </div>
      </div>

      {/* CVE indicator stays — security-relevant signal you want at-a-glance. */}
      {hasCves && (
        <Tooltip title={`Vulnerable: ${nodeData.cveIds!.join(', ')}`}>
          <BugOutlined
            style={{
              flex: '0 0 auto',
              color: '#ff4d4f',
              fontSize: 12,
            }}
          />
        </Tooltip>
      )}
    </div>
  );
});

DeviceNode.displayName = 'DeviceNode';

export default DeviceNode;
