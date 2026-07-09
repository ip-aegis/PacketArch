/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 aggregate edge — merged flows between clusters in group-by
 * view. Neutral stroke whose weight scales with flow count; label shows
 * the count and the protocol mix.
 */

import React from 'react';
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath } from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';
import { SURFACE, TEXT, FONT } from '../tokens';

export interface AggregateEdge2Data extends Record<string, unknown> {
  flowCount: number;
  protocolLabel: string;
}

const AggregateEdge2: React.FC<EdgeProps> = React.memo((props) => {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, selected, data } = props;
  const d = (data ?? { flowCount: 1, protocolLabel: '' }) as AggregateEdge2Data;

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
          stroke: selected ? TEXT.secondary : TEXT.faint,
          strokeWidth: Math.min(1.5 + d.flowCount * 0.4, 4),
          opacity: 0.8,
        }}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            background: SURFACE.chrome,
            color: selected ? TEXT.primary : TEXT.muted,
            border: `1px solid ${SURFACE.border}`,
            borderRadius: 4,
            padding: '1px 7px',
            fontFamily: FONT.mono,
            fontSize: 9.5,
            pointerEvents: 'none',
            whiteSpace: 'nowrap',
          }}
        >
          {d.flowCount}× {d.protocolLabel}
        </div>
      </EdgeLabelRenderer>
    </>
  );
});

AggregateEdge2.displayName = 'AggregateEdge2';

export default AggregateEdge2;
