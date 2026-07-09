/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 cluster node — an aggregate card shown in group-by view.
 * Neutral card with a colored identity tick; double-click expands the
 * cluster into its member devices.
 */

import React from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { getDeviceTypeMeta } from '../../constants/deviceTypeRegistry';
import { SURFACE, TEXT, FONT } from '../tokens';

export interface ClusterNode2Data extends Record<string, unknown> {
  clusterId: string;
  label: string;
  color: string;
  deviceCount: number;
  deviceTypes: Record<string, number>;
  protocols: string[];
}

const hiddenHandle: React.CSSProperties = {
  opacity: 0,
  pointerEvents: 'none',
  width: 6,
  height: 6,
};

const ClusterNode2: React.FC<NodeProps> = React.memo(({ data, selected }) => {
  const d = data as ClusterNode2Data;
  const topTypes = Object.entries(d.deviceTypes)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  return (
    <div
      role="treeitem"
      aria-label={`Cluster ${d.label}: ${d.deviceCount} devices`}
      aria-selected={selected}
      title="Double-click to expand"
      style={{
        minWidth: 190,
        maxWidth: 250,
        background: SURFACE.node,
        border: `1px solid ${selected ? d.color : SURFACE.border}`,
        borderRadius: 10,
        padding: '10px 13px',
        fontFamily: FONT.ui,
        cursor: 'pointer',
        position: 'relative',
        boxShadow: `inset 3px 0 0 ${d.color}`,
      }}
    >
      <Handle type="target" position={Position.Top} style={hiddenHandle} />
      <Handle type="source" position={Position.Bottom} style={hiddenHandle} />

      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <span
          style={{
            fontSize: 13,
            fontWeight: 650,
            color: TEXT.primary,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {d.label}
        </span>
        <span
          style={{
            marginLeft: 'auto',
            fontFamily: FONT.mono,
            fontSize: 10.5,
            color: TEXT.muted,
            whiteSpace: 'nowrap',
          }}
        >
          {d.deviceCount}
        </span>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 7 }}>
        {topTypes.map(([type, count]) => (
          <span
            key={type}
            style={{
              fontFamily: FONT.mono,
              fontSize: 9.5,
              color: TEXT.muted,
              background: SURFACE.iconWell,
              borderRadius: 4,
              padding: '1px 6px',
              whiteSpace: 'nowrap',
            }}
          >
            {getDeviceTypeMeta(type).label} ×{count}
          </span>
        ))}
        {Object.keys(d.deviceTypes).length > 3 && (
          <span style={{ fontFamily: FONT.mono, fontSize: 9.5, color: TEXT.faint }}>
            +{Object.keys(d.deviceTypes).length - 3}
          </span>
        )}
      </div>

      {d.protocols.length > 0 && (
        <div
          style={{
            fontFamily: FONT.mono,
            fontSize: 9.5,
            color: TEXT.faint,
            marginTop: 6,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {d.protocols.slice(0, 4).join(' · ')}
          {d.protocols.length > 4 ? ` +${d.protocols.length - 4}` : ''}
        </div>
      )}
    </div>
  );
});

ClusterNode2.displayName = 'ClusterNode2';

export default ClusterNode2;
