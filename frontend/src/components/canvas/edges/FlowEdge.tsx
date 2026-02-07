/**
 * Custom edge for protocol flows
 * Enhanced with dark theme styling and consistent protocol colors
 */

import React from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
} from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';
import type { ProtocolType } from '../../../types';
import { PROTOCOL_COLORS, PROTOCOL_EDGE_LABELS } from '../../../constants/protocols';

export interface FlowEdgeData extends Record<string, unknown> {
  protocol: ProtocolType;
  name?: string;
}

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

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const edgeData = data as FlowEdgeData;
  const protocol = edgeData?.protocol || 'modbus_tcp';
  const color = PROTOCOL_COLORS[protocol] || '#6a9fd4';
  const label = PROTOCOL_EDGE_LABELS[protocol] || protocol.toUpperCase();

  return (
    <>
      <BaseEdge
        id={id as string}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: color,
          strokeWidth: selected ? 3 : 2,
          strokeDasharray: selected ? '5,5' : undefined,
          animation: selected ? 'dashdraw 0.5s linear infinite' : undefined,
          filter: selected ? `drop-shadow(0 0 4px ${color})` : undefined,
        }}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            fontSize: 10,
            fontWeight: 600,
            background: '#1e2a3a',
            padding: '3px 8px',
            borderRadius: '4px',
            border: `1px solid ${color}60`,
            color: color,
            pointerEvents: 'all',
            cursor: 'pointer',
            whiteSpace: 'nowrap',
            boxShadow: selected ? `0 0 8px ${color}40` : '0 2px 4px rgba(0, 0, 0, 0.3)',
            transition: 'all 0.2s ease',
          }}
          className="nodrag nopan"
        >
          {label}
        </div>
      </EdgeLabelRenderer>

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
