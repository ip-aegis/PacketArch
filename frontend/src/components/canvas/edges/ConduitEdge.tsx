/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Custom edge for zone-to-zone conduits (IEC 62443)
 * Thick dashed style, color-coded by compliance status
 */

import React from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
} from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';
import type { ConduitDirection, ComplianceStatus, ProtocolType } from '../../../types';
import { PROTOCOL_SHORT_NAMES } from '../../../constants/protocols';

export interface ConduitEdgeData extends Record<string, unknown> {
  conduitId: string;
  name: string;
  direction: ConduitDirection;
  allowedProtocols: ProtocolType[];
  complianceStatus: ComplianceStatus;
  color?: string;
}

const COMPLIANCE_COLORS: Record<ComplianceStatus, string> = {
  compliant: '#52c41a',
  partial: '#faad14',
  non_compliant: '#ff4d4f',
  unchecked: '#6a8caf',
};

const DIRECTION_LABELS: Record<ConduitDirection, string> = {
  bidirectional: '\u2194',
  a_to_b: '\u2192',
  b_to_a: '\u2190',
};

const ConduitEdge: React.FC<EdgeProps<ConduitEdgeData>> = React.memo((props) => {
  const {
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    data,
    selected,
  } = props;

  const edgeData = data as ConduitEdgeData;
  const status = edgeData?.complianceStatus || 'unchecked';
  const color = edgeData?.color || COMPLIANCE_COLORS[status];
  const name = edgeData?.name || 'Conduit';
  const protocols = edgeData?.allowedProtocols || [];
  const direction = edgeData?.direction || 'bidirectional';

  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 16,
  });

  // Build protocol summary
  const protocolSummary = protocols.length > 0
    ? protocols
        .slice(0, 3)
        .map((p) => PROTOCOL_SHORT_NAMES[p] || p.slice(0, 3).toUpperCase())
        .join(', ')
    : 'No protocols';
  const extraCount = protocols.length > 3 ? ` +${protocols.length - 3}` : '';

  return (
    <>
      {/* Outer glow for selection */}
      {selected && (
        <BaseEdge
          id={`${id}-glow`}
          path={edgePath}
          style={{
            stroke: color,
            strokeWidth: 6,
            strokeDasharray: '6,4',
            opacity: 0.25,
            filter: `blur(2px)`,
          }}
        />
      )}
      {/* Halo: a dark wider stroke that matches the canvas background. Where
          the conduit crosses over a zone, this halo creates a clean visual
          break around the colored dashed line on top — the "highway over an
          underpass" effect — so it reads as passing OVER, not slicing through. */}
      <BaseEdge
        id={`${id}-halo`}
        path={edgePath}
        style={{
          stroke: '#1a2332',
          strokeWidth: selected ? 8 : 6,
          opacity: 0.95,
        }}
      />
      {/* Main conduit path — orthogonal dashed colored stroke on top of the halo. */}
      <BaseEdge
        id={id as string}
        path={edgePath}
        style={{
          stroke: color,
          strokeWidth: selected ? 3 : 2,
          strokeDasharray: '6,4',
          strokeLinecap: 'round',
          opacity: selected ? 1 : 0.85,
          filter: selected ? `drop-shadow(0 0 6px ${color}80)` : undefined,
        }}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY - 16}px)`,
            fontSize: 11,
            fontWeight: 600,
            background: '#1a2332',
            padding: '4px 10px',
            borderRadius: '6px',
            border: `2px solid ${color}80`,
            color: '#e0e0e0',
            pointerEvents: 'all',
            cursor: 'pointer',
            whiteSpace: 'nowrap',
            zIndex: 5,
            boxShadow: selected ? `0 0 12px ${color}40` : '0 2px 6px rgba(0, 0, 0, 0.4)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
          className="nodrag nopan"
        >
          {/* Shield icon */}
          <span style={{ color, fontSize: 13 }}>{'\u26A1'}</span>
          {/* Name + direction */}
          <span>{name}</span>
          <span style={{ color: '#8899aa', fontSize: 10 }}>
            {DIRECTION_LABELS[direction]}
          </span>
          {/* Protocol count badge */}
          <span
            style={{
              background: `${color}30`,
              color,
              padding: '1px 6px',
              borderRadius: '3px',
              fontSize: 10,
              fontWeight: 500,
            }}
          >
            {protocolSummary}{extraCount}
          </span>
        </div>
        {/* Expanded protocol list on selection */}
        {selected && protocols.length > 0 && (
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY + 12}px)`,
              display: 'flex',
              gap: '4px',
              flexWrap: 'wrap',
              justifyContent: 'center',
              zIndex: 5,
              pointerEvents: 'none',
            }}
          >
            {protocols.map((p) => (
              <span
                key={p}
                style={{
                  background: '#1e2a3a',
                  border: `1px solid ${color}50`,
                  color: '#c0d0e0',
                  padding: '2px 6px',
                  borderRadius: '3px',
                  fontSize: 9,
                  fontWeight: 500,
                }}
              >
                {PROTOCOL_SHORT_NAMES[p] || p}
              </span>
            ))}
          </div>
        )}
      </EdgeLabelRenderer>
    </>
  );
});

ConduitEdge.displayName = 'ConduitEdge';

export default ConduitEdge;
