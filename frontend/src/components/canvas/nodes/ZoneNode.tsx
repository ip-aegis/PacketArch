/**
 * Group node for network zones
 * Dark theme styling to match canvas
 */

import React from 'react';
import type { NodeProps } from '@xyflow/react';

export interface ZoneNodeData extends Record<string, unknown> {
  id: string;
  name: string;
  type: 'vertical' | 'network' | 'vlan' | 'logical';
  network?: {
    subnet: string;
    vlanId?: number;
    gateway?: string;
  };
}

// Zone colors with dark theme
const ZONE_COLORS: Record<string, string> = {
  vertical: 'rgba(4, 159, 217, 0.08)',
  network: 'rgba(108, 192, 74, 0.08)',
  vlan: 'rgba(156, 39, 176, 0.08)',
  logical: 'rgba(251, 171, 24, 0.08)',
};

const ZONE_BORDER_COLORS: Record<string, string> = {
  vertical: '#049FD9',
  network: '#6CC04A',
  vlan: '#9C27B0',
  logical: '#FBAB18',
};

const ZoneNode: React.FC<NodeProps<ZoneNodeData>> = (props) => {
  const { data, selected } = props;
  if (!data) return null;

  const nodeData = data as unknown as ZoneNodeData;
  const backgroundColor = ZONE_COLORS[nodeData.type] || ZONE_COLORS.logical;
  const borderColor = ZONE_BORDER_COLORS[nodeData.type] || ZONE_BORDER_COLORS.logical;

  return (
    <>
      <div
        style={{
          width: '100%',
          height: '100%',
          background: backgroundColor,
          border: `2px dashed ${selected ? borderColor : `${borderColor}60`}`,
          borderRadius: '12px',
          padding: '12px',
          pointerEvents: 'all',
          transition: 'all 0.2s ease',
          boxShadow: selected ? `0 0 20px ${borderColor}30` : undefined,
        }}
      >
        {/* Zone header */}
        <div
          style={{
            background: '#1e2a3a',
            border: `1px solid ${borderColor}50`,
            borderRadius: '6px',
            padding: '6px 12px',
            display: 'inline-block',
            fontWeight: 600,
            fontSize: '13px',
            color: borderColor,
            marginBottom: '8px',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
          }}
        >
          {nodeData.name}
        </div>

        {/* Network info */}
        {nodeData.network && (
          <div
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: `1px solid ${borderColor}30`,
              borderRadius: '4px',
              padding: '4px 10px',
              display: 'inline-block',
              fontSize: '11px',
              color: 'rgba(255,255,255,0.6)',
              marginLeft: '8px',
              fontFamily: 'monospace',
            }}
          >
            {nodeData.network.subnet}
            {nodeData.network.vlanId && ` (VLAN ${nodeData.network.vlanId})`}
          </div>
        )}
      </div>
    </>
  );
};

export default ZoneNode;
