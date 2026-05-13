/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Custom edge for protocol flows
 * Enhanced with dark theme styling and consistent protocol colors
 */

import React from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
} from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';
import { useCompactMode } from '../hooks/useCompactMode';
import type { ProtocolType } from '../../../types';
import { PROTOCOL_COLORS, PROTOCOL_EDGE_LABELS, PROTOCOL_SHORT_NAMES } from '../../../constants/protocols';
import { useFlowRationality } from '../../../stores/rationalityStore';

export interface FlowEdgeData extends Record<string, unknown> {
  protocol: ProtocolType;
  name?: string;
  /** Aggregate edge: number of merged flows */
  flowCount?: number;
  /** Aggregate edge: unique protocols in the aggregate */
  protocolList?: string[];
  /** Parallel edge index (0-based) among edges sharing the same node pair */
  parallelIndex?: number;
  /** Total number of parallel edges between the same node pair */
  parallelCount?: number;
  /** Conduit compliance status for cross-zone flows */
  complianceReason?: 'same_zone' | 'compliant' | 'no_conduit' | 'protocol_not_allowed' | 'wrong_direction' | 'no_zone_info';
}

/** Perpendicular pixel offset between parallel edges */
const PARALLEL_OFFSET_PX = 16;

const FlowEdge: React.FC<EdgeProps<FlowEdgeData>> = React.memo((props) => {
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
    markerEnd,
  } = props;

  const isCompact = useCompactMode();
  const edgeData = data as FlowEdgeData;
  const protocol = edgeData?.protocol || 'modbus_tcp';
  const color = PROTOCOL_COLORS[protocol] || '#6a9fd4';
  const isAggregate = edgeData?.flowCount != null && edgeData.flowCount > 0;
  const complianceReason = edgeData?.complianceReason;
  // Phase 7: rationality indicator. Skipped for aggregate edges
  // (which represent multiple flows merged for display).
  const rationality = useFlowRationality(id as string);

  // Compute perpendicular offset for parallel edges between the same node pair
  const pIndex = edgeData?.parallelIndex ?? 0;
  const pCount = edgeData?.parallelCount ?? 1;
  let offsetSourceX = sourceX;
  let offsetSourceY = sourceY;
  let offsetTargetX = targetX;
  let offsetTargetY = targetY;

  if (pCount > 1) {
    const offset = (pIndex - (pCount - 1) / 2) * PARALLEL_OFFSET_PX;
    // Offset perpendicular to the source→target axis
    const dx = targetX - sourceX;
    const dy = targetY - sourceY;
    const len = Math.sqrt(dx * dx + dy * dy) || 1;
    // Perpendicular unit vector (rotated 90°)
    const px = -dy / len;
    const py = dx / len;
    offsetSourceX = sourceX + px * offset;
    offsetSourceY = sourceY + py * offset;
    offsetTargetX = targetX + px * offset;
    offsetTargetY = targetY + py * offset;
  }

  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX: offsetSourceX,
    sourceY: offsetSourceY,
    sourcePosition,
    targetX: offsetTargetX,
    targetY: offsetTargetY,
    targetPosition,
    borderRadius: 8,
  });

  // Build label text
  let label: string;
  if (isAggregate && edgeData.protocolList && edgeData.protocolList.length > 0) {
    label = edgeData.protocolList
      .map((p) => PROTOCOL_SHORT_NAMES[p as ProtocolType] || p.slice(0, 3).toUpperCase())
      .join(', ');
    label = `${edgeData.flowCount}x ${label}`;
  } else {
    label = PROTOCOL_EDGE_LABELS[protocol] || protocol.toUpperCase();
  }

  // Aggregate edges are thicker (smoothstep segments appear bolder than bezier at same width)
  const baseWidth = isAggregate ? 1.5 + Math.min(edgeData.flowCount!, 4) : 1.5;

  return (
    <>
      <BaseEdge
        id={id as string}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: color,
          strokeWidth: selected ? baseWidth + 1 : baseWidth,
          strokeDasharray: selected ? '5,5' : undefined,
          animation: selected ? 'dashdraw 0.5s linear infinite' : undefined,
          filter: selected ? `drop-shadow(0 0 4px ${color})` : undefined,
        }}
      />
      {!isCompact && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY - 12}px)`,
              fontSize: isAggregate ? 11 : 10,
              fontWeight: 600,
              background: '#1e2a3a',
              padding: isAggregate ? '4px 10px' : '3px 8px',
              borderRadius: '4px',
              border: `1px solid ${color}60`,
              color: color,
              pointerEvents: 'all',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              zIndex: 10,
              boxShadow: selected ? `0 0 8px ${color}40` : '0 2px 4px rgba(0, 0, 0, 0.3)',
              transition: 'all 0.2s ease',
            }}
            className="nodrag nopan"
          >
            {label}
            {complianceReason === 'compliant' && (
              <span title="Compliant with conduit" style={{ marginLeft: 4, fontSize: 10 }}>{'\u2705'}</span>
            )}
            {complianceReason === 'no_conduit' && (
              <span title="No conduit between zones" style={{ marginLeft: 4, fontSize: 10 }}>{'\u26A0\uFE0F'}</span>
            )}
            {complianceReason === 'protocol_not_allowed' && (
              <span title="Protocol not allowed by conduit" style={{ marginLeft: 4, fontSize: 10 }}>{'\u274C'}</span>
            )}
            {complianceReason === 'wrong_direction' && (
              <span title="Wrong direction for conduit" style={{ marginLeft: 4, fontSize: 10 }}>{'\u274C'}</span>
            )}
            {!isAggregate && rationality?.status === 'off-rail' && (
              <span
                title={
                  rationality.suggestion ||
                  'No matrix entry for this role pair \u2014 off-rail authoring choice.'
                }
                style={{
                  marginLeft: 4,
                  fontSize: 10,
                  color: '#ff9f4a',
                }}
              >
                {'\u26A0\uFE0F'}
              </span>
            )}
            {!isAggregate && rationality?.status === 'mismatch' && (
              <span
                title={
                  rationality.suggestion ||
                  'Protocol mismatch with the architecture matrix.'
                }
                style={{
                  marginLeft: 4,
                  fontSize: 10,
                  color: '#ffd54a',
                }}
              >
                {'\u26A0\uFE0F'}
              </span>
            )}
            {!isAggregate && rationality?.status === 'ok' && (
              <span
                title="On the architecture rail (matrix-endorsed flow)"
                style={{
                  marginLeft: 4,
                  fontSize: 10,
                  color: '#5fb878',
                }}
              >
                {'\u2693'}
              </span>
            )}
          </div>
        </EdgeLabelRenderer>
      )}

      <style>
        {`
          @keyframes dashdraw {
            to {
              stroke-dashoffset: -10;
            }
          }
        `}
      </style>
    </>
  );
});

FlowEdge.displayName = 'FlowEdge';

export default FlowEdge;
