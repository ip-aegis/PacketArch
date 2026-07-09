/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 zone node — near-neutral container: 4% tint, 1px border,
 * header tab with name + Purdue chip. Read-only in Phase 1; Phase 2 makes
 * zones true parent containers with resize and drag-in membership.
 */

import React from 'react';
import type { NodeProps } from '@xyflow/react';
import { SURFACE, TEXT, ZONE, FONT } from '../tokens';

export interface ZoneNode2Data extends Record<string, unknown> {
  name: string;
  purdueLevel?: number | string;
  subnet?: string;
  width: number;
  height: number;
}

const ZoneNode2: React.FC<NodeProps> = React.memo(({ data }) => {
  const d = data as ZoneNode2Data;
  return (
    <div
      role="group"
      aria-label={`Zone: ${d.name}`}
      style={{
        width: d.width,
        height: d.height,
        borderRadius: ZONE.radius,
        background: ZONE.fill,
        border: `1px solid ${ZONE.border}`,
        position: 'relative',
        fontFamily: FONT.ui,
        pointerEvents: 'none',
      }}
    >
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
          border: `1px solid ${ZONE.border}`,
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
