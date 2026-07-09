/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 zone node — a real container. Devices are React Flow children
 * of the zone (drag in to join, out to leave); resize handles appear on
 * selection. Near-neutral visuals: 4% tint, 1px border, header tab with
 * name + Purdue chip.
 */

import React from 'react';
import { Handle, Position, NodeResizer } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { useDocumentStore, commands } from '../document/documentStore';
import { SURFACE, TEXT, ZONE, ACCENT, FONT } from '../tokens';

export interface ZoneNode2Data extends Record<string, unknown> {
  name: string;
  purdueLevel?: number | string;
  subnet?: string;
}

const hiddenHandle: React.CSSProperties = {
  opacity: 0,
  pointerEvents: 'none',
  width: 6,
  height: 6,
};

const ZoneNode2: React.FC<NodeProps> = React.memo(({ id, data, selected }) => {
  const d = data as ZoneNode2Data;
  return (
    <div
      role="group"
      aria-label={`Zone: ${d.name}`}
      style={{
        width: '100%',
        height: '100%',
        borderRadius: ZONE.radius,
        background: ZONE.fill,
        border: `1px solid ${selected ? ACCENT : ZONE.border}`,
        position: 'relative',
        fontFamily: FONT.ui,
        cursor: 'grab',
      }}
    >
      <NodeResizer
        isVisible={!!selected}
        minWidth={200}
        minHeight={140}
        lineStyle={{ borderColor: ACCENT }}
        handleStyle={{
          width: 8,
          height: 8,
          borderRadius: 2,
          background: SURFACE.node,
          border: `1.5px solid ${ACCENT}`,
        }}
        onResizeEnd={(_event, params) => {
          const state = useDocumentStore.getState();
          if (!state.doc) return;
          const cmd = commands.updateZone(state.doc, id, {
            position: { x: params.x, y: params.y },
            dimensions: { width: params.width, height: params.height },
          });
          if (cmd) state.dispatch(cmd);
        }}
      />

      {/* Anchor points for conduit edges (invisible; conduit tool arrives
          with the conduit editor) */}
      <Handle type="target" position={Position.Top} id="conduit-t" style={hiddenHandle} />
      <Handle type="source" position={Position.Bottom} id="conduit-s" style={hiddenHandle} />

      <div
        style={{
          position: 'absolute',
          top: -1,
          left: -1,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '3px 12px',
          background: ZONE.headerBg,
          border: `1px solid ${selected ? ACCENT : ZONE.border}`,
          borderRadius: `${ZONE.radius}px 0 ${ZONE.radius}px 0`,
          maxWidth: '90%',
        }}
      >
        <span
          style={{
            fontSize: 11.5,
            fontWeight: 600,
            color: TEXT.secondary,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {d.name}
        </span>
        {d.purdueLevel !== undefined && d.purdueLevel !== null && (
          <span
            style={{
              fontFamily: FONT.mono,
              fontSize: 9,
              color: TEXT.muted,
              border: `1px solid ${SURFACE.border}`,
              borderRadius: 3,
              padding: '0 4px',
              whiteSpace: 'nowrap',
            }}
          >
            L{d.purdueLevel}
          </span>
        )}
        {d.subnet && (
          <span
            style={{
              fontFamily: FONT.mono,
              fontSize: 9,
              color: TEXT.faint,
              whiteSpace: 'nowrap',
            }}
          >
            {d.subnet}
          </span>
        )}
      </div>
    </div>
  );
});

ZoneNode2.displayName = 'ZoneNode2';

export default ZoneNode2;
