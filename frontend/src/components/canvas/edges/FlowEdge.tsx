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

export interface FlowEdgeData extends Record<string, unknown> {
  protocol: ProtocolType;
  name?: string;
}

// Protocol colors matching DeviceNode and PaletteItem
const PROTOCOL_COLORS: Record<ProtocolType, string> = {
  modbus_tcp: '#049FD9',
  ethernet_ip: '#6CC04A',
  profinet: '#FBAB18',
  opc_ua: '#9C27B0',
  dnp3: '#FF5722',
  iec104: '#E91E63',
  bacnet: '#00BCD4',
};

// Protocol short names for edge labels
const PROTOCOL_SHORT_NAMES: Record<ProtocolType, string> = {
  modbus_tcp: 'MODBUS',
  ethernet_ip: 'EIP',
  profinet: 'PROFINET',
  opc_ua: 'OPC UA',
  dnp3: 'DNP3',
  iec104: 'IEC 104',
  bacnet: 'BACnet',
};

const FlowEdge: React.FC<EdgeProps<FlowEdgeData>> = (props) => {
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

  const edgeData = data as unknown as FlowEdgeData;
  const protocol = edgeData?.protocol || 'modbus_tcp';
  const color = PROTOCOL_COLORS[protocol] || '#6a9fd4';
  const label = PROTOCOL_SHORT_NAMES[protocol] || protocol.toUpperCase();

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
};

export default FlowEdge;
