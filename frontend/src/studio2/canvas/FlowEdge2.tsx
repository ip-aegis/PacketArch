/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 flow edge — thin desaturated protocol stroke. The label is
 * zoom-gated (card tier or selection only) so a dense scenario reads as
 * a fabric, not a wall of pills.
 */

import React from 'react';
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath, useStore } from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';
import { protocolEdgeColor, SURFACE, TEXT, NODE, FONT } from '../tokens';
import { PROTOCOL_EDGE_LABELS } from '../../constants/protocols';

function protocolLabel(protocol: string): string {
  return (
    PROTOCOL_EDGE_LABELS[protocol as keyof typeof PROTOCOL_EDGE_LABELS] ??
    protocol.replace(/_/g, ' ').toUpperCase()
  );
}

export interface FlowEdge2Data extends Record<string, unknown> {
  protocol: string;
}

const FlowEdge2: React.FC<EdgeProps> = React.memo((props) => {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, selected, data } = props;
  const protocol = ((data as FlowEdge2Data | undefined)?.protocol ?? '') as string;
  const color = protocolEdgeColor(protocol);
  const showLabel = useStore((s) => s.transform[2] >= NODE.lodChip) || !!selected;

  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 8,
  });

  return (
    <>
      <BaseEdge
        path={path}
        style={{
          stroke: color,
          strokeWidth: selected ? 2.5 : 1.5,
          opacity: selected ? 1 : 0.85,
        }}
      />
      {showLabel && protocol && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              background: SURFACE.chrome,
              color: selected ? TEXT.primary : TEXT.muted,
              border: `1px solid ${selected ? color : SURFACE.border}`,
              borderRadius: 4,
              padding: '1px 6px',
              fontFamily: FONT.mono,
              fontSize: 9.5,
              pointerEvents: 'none',
            }}
          >
            {protocolLabel(protocol)}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
});

FlowEdge2.displayName = 'FlowEdge2';

export default FlowEdge2;
