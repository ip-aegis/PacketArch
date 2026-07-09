/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 bottom strip — view state lives here, once: zoom, fit, grid.
 * (v1 had two zoom clusters in opposite corners.) Must be rendered inside
 * the ReactFlowProvider so it can drive the viewport.
 */

import React from 'react';
import { useReactFlow, useViewport } from '@xyflow/react';
import { useDocumentStore } from '../document/documentStore';
import { SURFACE, TEXT, FONT } from '../tokens';

const stripButton: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  color: TEXT.secondary,
  fontFamily: FONT.mono,
  fontSize: 11,
  padding: '2px 8px',
  cursor: 'pointer',
  borderRadius: 4,
};

const BottomStrip: React.FC = () => {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  const { zoom } = useViewport();
  const deviceCount = useDocumentStore((s) => (s.doc ? Object.keys(s.doc.devices).length : 0));
  const flowCount = useDocumentStore((s) => (s.doc ? Object.keys(s.doc.flows).length : 0));

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        height: 30,
        padding: '0 10px',
        background: SURFACE.chrome,
        borderTop: `1px solid ${SURFACE.border}`,
        fontFamily: FONT.mono,
        fontSize: 11,
        color: TEXT.muted,
        flex: '0 0 auto',
      }}
    >
      <button style={stripButton} onClick={() => zoomOut()} aria-label="Zoom out">
        −
      </button>
      <span style={{ minWidth: 42, textAlign: 'center', fontVariantNumeric: 'tabular-nums' }}>
        {Math.round(zoom * 100)}%
      </span>
      <button style={stripButton} onClick={() => zoomIn()} aria-label="Zoom in">
        +
      </button>
      <button
        style={stripButton}
        onClick={() => fitView({ padding: 0.15, duration: 300 })}
        aria-label="Fit view"
      >
        fit
      </button>
      <span style={{ color: SURFACE.border }}>│</span>
      <span>grid 20</span>
      <span style={{ marginLeft: 'auto', color: TEXT.faint }}>
        {deviceCount} devices · {flowCount} flows
      </span>
    </div>
  );
};

export default BottomStrip;
