/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Custom React Flow node for collapsed device clusters.
 * Shows aggregate info: device count, device type breakdown, protocol badges.
 * Double-click to expand and see member devices.
 */

import React, { useState } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { Tag, Tooltip } from 'antd';
import type { ProtocolType } from '../../../types';
import {
  PROTOCOL_COLORS,
  PROTOCOL_SHORT_NAMES,
} from '../../../constants/protocols';
import { getDeviceTypeColor, getDeviceTypeLabel } from '../../../constants/deviceTypeRegistry';

export interface ClusterNodeData extends Record<string, unknown> {
  clusterId: string;
  label: string;
  groupKey: string;
  color: string;
  deviceCount: number;
  deviceTypes: Record<string, number>;
  protocols: string[];
  vendors: string[];
  isExpanded: boolean;
}

const ClusterNode: React.FC<NodeProps<ClusterNodeData>> = React.memo((props) => {
  const { data, selected } = props;
  const [hovered, setHovered] = useState(false);
  if (!data) return null;

  const nodeData = data as ClusterNodeData;
  const deviceTypeEntries = Object.entries(nodeData.deviceTypes)
    .sort(([, a], [, b]) => b - a);
  const protocolList = nodeData.protocols.slice(0, 5);
  const vendorSummary =
    nodeData.vendors.length <= 2
      ? nodeData.vendors.join(', ')
      : `${nodeData.vendors.slice(0, 2).join(', ')} +${nodeData.vendors.length - 2}`;

  const handleStyle = {
    background: nodeData.color,
    width: 10,
    height: 10,
    border: '2px solid #1e2a3a',
  };

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding: '12px 16px',
        borderRadius: '14px',
        background: '#1e2a3a',
        border: `2px solid ${selected ? nodeData.color : `${nodeData.color}40`}`,
        borderTop: `4px solid ${nodeData.color}`,
        minWidth: '200px',
        maxWidth: '280px',
        boxShadow: selected
          ? `0 4px 20px ${nodeData.color}40, 0 0 0 1px ${nodeData.color}60`
          : '0 2px 8px rgba(0,0,0,0.3)',
        transition: 'all 0.2s ease',
        cursor: 'pointer',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ ...handleStyle, top: -5 }} />
      <Handle type="source" position={Position.Bottom} style={{ ...handleStyle, bottom: -5 }} />
      <Handle type="target" position={Position.Left} style={{ ...handleStyle, left: -5 }} />
      <Handle type="source" position={Position.Right} style={{ ...handleStyle, right: -5 }} />

      {/* Header: label + device count */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 8,
          gap: 8,
        }}
      >
        <span
          style={{
            color: nodeData.color,
            fontWeight: 600,
            fontSize: '13px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {nodeData.label}
        </span>
        <Tag
          color={nodeData.color}
          style={{
            fontSize: '10px',
            margin: 0,
            lineHeight: '18px',
            padding: '0 6px',
            borderRadius: '4px',
            fontWeight: 600,
            flexShrink: 0,
          }}
        >
          {nodeData.deviceCount}
        </Tag>
      </div>

      {/* Device type breakdown */}
      {deviceTypeEntries.length > 0 && (
        <div style={{ display: 'flex', gap: 4, marginBottom: 6, flexWrap: 'wrap' }}>
          {deviceTypeEntries.map(([type, count]) => (
            <Tooltip key={type} title={`${count} ${getDeviceTypeLabel(type)}`}>
              <div
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: 6,
                  background: `${getDeviceTypeColor(type)}20`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 10,
                  fontWeight: 600,
                  color: getDeviceTypeColor(type),
                }}
              >
                {count}
              </div>
            </Tooltip>
          ))}
        </div>
      )}

      {/* Protocol badges */}
      {protocolList.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 4 }}>
          {protocolList.map((protocol) => (
            <Tag
              key={protocol}
              color={PROTOCOL_COLORS[protocol as ProtocolType] || '#6a9fd4'}
              style={{
                fontSize: '9px',
                margin: 0,
                lineHeight: '16px',
                padding: '0 5px',
                borderRadius: '3px',
                fontWeight: 600,
              }}
            >
              {PROTOCOL_SHORT_NAMES[protocol as ProtocolType] || protocol.slice(0, 4).toUpperCase()}
            </Tag>
          ))}
          {nodeData.protocols.length > 5 && (
            <Tag
              style={{
                fontSize: '9px',
                margin: 0,
                lineHeight: '16px',
                padding: '0 5px',
                borderRadius: '3px',
                background: 'rgba(255,255,255,0.1)',
                border: 'none',
                color: 'rgba(255,255,255,0.6)',
              }}
            >
              +{nodeData.protocols.length - 5}
            </Tag>
          )}
        </div>
      )}

      {/* Vendor summary */}
      {vendorSummary && (
        <div
          style={{
            fontSize: '10px',
            color: 'rgba(255,255,255,0.45)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {vendorSummary}
        </div>
      )}

      {/* Expand hint */}
      {hovered && (
        <div
          style={{
            fontSize: '9px',
            color: 'rgba(255,255,255,0.3)',
            textAlign: 'center',
            marginTop: 6,
          }}
        >
          Double-click to expand
        </div>
      )}
    </div>
  );
});

ClusterNode.displayName = 'ClusterNode';

export default ClusterNode;
