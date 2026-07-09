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
import { layoutDocument, resolveOverlaps } from '../canvas/layout';
import { useStudio2UI, GROUP_BY_MODES, GROUP_BY_LABELS, type GroupByMode } from '../uiState';
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

const GroupBySelect: React.FC = () => {
  const groupBy = useStudio2UI((s) => s.groupBy);
  const setGroupBy = useStudio2UI((s) => s.setGroupBy);
  return (
    <select
      value={groupBy}
      onChange={(e) => setGroupBy(e.target.value as GroupByMode)}
      aria-label="Group devices by"
      title="Group devices into clusters (G cycles modes; double-click a cluster to expand)"
      style={{
        background: 'transparent',
        border: 'none',
        color: groupBy === 'none' ? TEXT.muted : TEXT.primary,
        fontFamily: FONT.mono,
        fontSize: 11,
        cursor: 'pointer',
        outline: 'none',
      }}
    >
      {GROUP_BY_MODES.map((m) => (
        <option key={m} value={m} style={{ background: SURFACE.raised }}>
          {GROUP_BY_LABELS[m]}
        </option>
      ))}
    </select>
  );
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
      <button
        style={stripButton}
        title="Nudge overlapping devices apart (keeps your arrangement, undoable)"
        onClick={() => {
          const state = useDocumentStore.getState();
          if (!state.doc) return;
          const cmd = resolveOverlaps(state.doc);
          if (cmd) {
            state.dispatch(cmd);
            setTimeout(() => fitView({ padding: 0.15, duration: 300 }), 50);
          }
        }}
      >
        tidy
      </button>
      <button
        style={stripButton}
        title="Re-layout all zones and devices in Purdue bands (undoable)"
        onClick={() => {
          const state = useDocumentStore.getState();
          if (!state.doc) return;
          const cmd = layoutDocument(state.doc);
          if (cmd) {
            state.dispatch(cmd);
            setTimeout(() => fitView({ padding: 0.15, duration: 300 }), 50);
          }
        }}
      >
        layout
      </button>
      <span style={{ color: SURFACE.border }}>│</span>
      <GroupBySelect />
      <span style={{ color: SURFACE.border }}>│</span>
      <span>grid 20</span>
      <span style={{ marginLeft: 'auto', color: TEXT.faint }}>
        {deviceCount} devices · {flowCount} flows
      </span>
    </div>
  );
};

export default BottomStrip;
