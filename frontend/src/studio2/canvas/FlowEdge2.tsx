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
import { protocolEdgeColor, SURFACE, TEXT, NODE, FONT, STATUS, type StatusLevel } from '../tokens';
import { PROTOCOL_EDGE_LABELS } from '../../constants/protocols';
import { useStudio2UI } from '../uiState';

function protocolLabel(protocol: string): string {
  return (
    PROTOCOL_EDGE_LABELS[protocol as keyof typeof PROTOCOL_EDGE_LABELS] ??
    protocol.replace(/_/g, ' ').toUpperCase()
  );
}

export interface FlowEdge2Data extends Record<string, unknown> {
  protocol: string;
  /** Worst health finding touching this flow (Build-mode status). */
  status?: StatusLevel;
}

const FlowEdge2: React.FC<EdgeProps> = React.memo((props) => {
  const { id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, selected, data } = props;
  const edgeData = data as FlowEdge2Data | undefined;
  const protocol = (edgeData?.protocol ?? '') as string;
  const status = edgeData?.status;
  const color = protocolEdgeColor(protocol);
  const showLabel = useStore((s) => s.transform[2] >= NODE.lodChip) || !!selected;
  const dimmed = useStudio2UI((s) => s.highlight !== null && !s.highlight.edgeIds.includes(id));

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
          opacity: dimmed ? 0.08 : selected ? 1 : 0.85,
          transition: 'opacity 120ms ease',
        }}
      />
      {showLabel && protocol && !dimmed && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              background: SURFACE.chrome,
              color: selected ? TEXT.primary : TEXT.muted,
              border: `1px solid ${status ? STATUS[status] : selected ? color : SURFACE.border}`,
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
