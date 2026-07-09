/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 conduit edge — IEC 62443 zone-to-zone conduit. Thick dashed
 * neutral line with a compact label; full conduit editing arrives with
 * the conduit tool in the next increment.
 */

import React from 'react';
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath } from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';
import { SURFACE, TEXT, FONT } from '../tokens';

export interface ConduitEdge2Data extends Record<string, unknown> {
  name: string;
  direction?: string;
  protocolCount?: number;
}

const ConduitEdge2: React.FC<EdgeProps> = React.memo((props) => {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, selected, data } = props;
  const d = (data ?? {}) as ConduitEdge2Data;

  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 10,
  });

  const arrow = d.direction === 'bidirectional' ? '↔' : d.direction === 'reverse' ? '←' : '→';

  return (
    <>
      <BaseEdge
        path={path}
        style={{
          stroke: selected ? TEXT.secondary : TEXT.faint,
          strokeWidth: 3,
          strokeDasharray: '7 5',
          opacity: 0.65,
        }}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            background: SURFACE.chrome,
            color: TEXT.muted,
            border: `1px solid ${SURFACE.border}`,
            borderRadius: 4,
            padding: '1px 7px',
            fontFamily: FONT.mono,
            fontSize: 9.5,
            pointerEvents: 'none',
            whiteSpace: 'nowrap',
          }}
        >
          ⛨ {d.name} {arrow}
          {typeof d.protocolCount === 'number' ? ` · ${d.protocolCount}p` : ''}
        </div>
      </EdgeLabelRenderer>
    </>
  );
});

ConduitEdge2.displayName = 'ConduitEdge2';

export default ConduitEdge2;
