/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 device node — neutral card, category-colored OT glyph, one
 * status dot, handles that materialize on hover. Three level-of-detail
 * tiers by zoom: dot (<0.45), chip (<0.9), full card.
 */

import React from 'react';
import { Handle, Position, useStore } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { DeviceGlyph, accentForType } from '../glyphs';
import { getDeviceTypeMeta } from '../../constants/deviceTypeRegistry';
import { useStudio2UI } from '../uiState';
import { SURFACE, TEXT, ACCENT, STATUS, NODE, FONT, type StatusLevel } from '../tokens';

export interface DeviceNode2Data extends Record<string, unknown> {
  name: string;
  deviceType: string;
  ipAddress?: string;
  status?: StatusLevel;
}

type LodTier = 'dot' | 'chip' | 'card';

function useLodTier(): LodTier {
  return useStore((s) => {
    const zoom = s.transform[2];
    if (zoom < NODE.lodDot) return 'dot';
    if (zoom < NODE.lodChip) return 'chip';
    return 'card';
  });
}

const handleStyle: React.CSSProperties = {
  width: 9,
  height: 9,
  background: ACCENT,
  border: `2px solid ${SURFACE.ground}`,
  opacity: 0,
  transition: 'opacity 120ms ease',
};

const DeviceNode2: React.FC<NodeProps> = React.memo(({ id, data, selected }) => {
  const d = data as DeviceNode2Data;
  const rawTier = useLodTier();
  // A selected node always shows full detail
  const tier: LodTier = selected ? 'card' : rawTier;
  const accent = accentForType(d.deviceType);
  const typeLabel = getDeviceTypeMeta(d.deviceType).label;
  // Health spotlight: dim everything a hovered finding doesn't touch
  const dimmed = useStudio2UI((s) => s.highlight !== null && !s.highlight.nodeIds.includes(id));
  const dimStyle: React.CSSProperties = {
    opacity: dimmed ? 0.18 : 1,
    transition: 'opacity 120ms ease',
  };

  const handles = (
    <>
      <Handle type="target" position={Position.Top} className="s2-handle" style={handleStyle} />
      <Handle type="source" position={Position.Bottom} className="s2-handle" style={handleStyle} />
      <Handle type="target" position={Position.Left} className="s2-handle" style={handleStyle} />
      <Handle type="source" position={Position.Right} className="s2-handle" style={handleStyle} />
    </>
  );

  const statusDot = d.status && (
    <span
      style={{
        position: 'absolute',
        top: -4,
        right: -4,
        width: 10,
        height: 10,
        borderRadius: '50%',
        background: STATUS[d.status],
        border: `2px solid ${SURFACE.ground}`,
      }}
    />
  );

  if (tier === 'dot') {
    return (
      <div
        className="s2-node"
        role="treeitem"
        aria-label={`${typeLabel}: ${d.name}`}
        aria-selected={selected}
        style={{
          width: 18,
          height: 18,
          borderRadius: '50%',
          background: SURFACE.iconWell,
          border: `2px solid ${d.status ? STATUS[d.status] : accent}`,
          position: 'relative',
          cursor: 'pointer',
          ...dimStyle,
        }}
      >
        {handles}
      </div>
    );
  }

  if (tier === 'chip') {
    return (
      <div
        className="s2-node"
        role="treeitem"
        aria-label={`${typeLabel}: ${d.name}`}
        aria-selected={selected}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 7,
          padding: '5px 11px 5px 7px',
          borderRadius: 999,
          background: SURFACE.node,
          border: `1px solid ${SURFACE.border}`,
          position: 'relative',
          cursor: 'pointer',
          fontFamily: FONT.ui,
          ...dimStyle,
        }}
      >
        {handles}
        {statusDot}
        <DeviceGlyph deviceType={d.deviceType} size={15} />
        <span
          style={{
            fontSize: 11.5,
            fontWeight: 600,
            color: TEXT.primary,
            maxWidth: 130,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {d.name}
        </span>
      </div>
    );
  }

  return (
    <div
      className="s2-node"
      role="treeitem"
      aria-label={`${typeLabel}: ${d.name}${d.ipAddress ? `, IP ${d.ipAddress}` : ''}`}
      aria-selected={selected}
      title={d.name}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 11,
        padding: '9px 13px 9px 10px',
        borderRadius: NODE.radius,
        background: SURFACE.node,
        border: `1px solid ${SURFACE.border}`,
        minWidth: NODE.minWidth,
        maxWidth: 220,
        position: 'relative',
        cursor: 'pointer',
        fontFamily: FONT.ui,
        outline: selected ? `1.5px solid ${ACCENT}` : 'none',
        outlineOffset: 2,
        ...dimStyle,
      }}
    >
      {handles}
      {statusDot}
      <div
        style={{
          flex: '0 0 auto',
          width: NODE.iconWellSize,
          height: NODE.iconWellSize,
          borderRadius: 8,
          background: SURFACE.iconWell,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <DeviceGlyph deviceType={d.deviceType} size={NODE.glyphSize} />
      </div>
      <div style={{ flex: '1 1 auto', minWidth: 0 }}>
        <div
          style={{
            fontSize: NODE.nameSize,
            fontWeight: 600,
            color: TEXT.primary,
            lineHeight: 1.25,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {d.name}
        </div>
        <div
          style={{
            fontFamily: FONT.mono,
            fontSize: NODE.subSize,
            color: TEXT.muted,
            marginTop: 2,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {typeLabel}
          {d.ipAddress ? ` · ${d.ipAddress}` : ''}
        </div>
      </div>
    </div>
  );
});

DeviceNode2.displayName = 'DeviceNode2';

export default DeviceNode2;
