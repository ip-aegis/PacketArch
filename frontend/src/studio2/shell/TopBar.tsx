/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 top bar — scenario identity, save state, undo/redo, and the
 * workspace switcher. One of exactly four docked regions; nothing here
 * ever floats over the canvas.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useDocumentStore } from '../document/documentStore';
import { useStudio2UI } from '../uiState';
import { useHealth } from '../health/healthStore';
import { useFeatures } from '../../hooks/useFeatures';
import { SURFACE, TEXT, ACCENT, ACCENT_SOFT, STATUS, FONT, type StatusLevel } from '../tokens';

const barButton: React.CSSProperties = {
  background: 'transparent',
  border: `1px solid ${SURFACE.border}`,
  borderRadius: 6,
  color: TEXT.secondary,
  fontFamily: FONT.ui,
  fontSize: 12.5,
  padding: '4px 10px',
  cursor: 'pointer',
  lineHeight: 1.4,
};

const WORKSPACES = ['Build', 'Verify', 'Run'] as const;

const TopBar: React.FC = () => {
  const navigate = useNavigate();
  const name = useDocumentStore((s) => s.doc?.meta.name ?? '');
  const ipRange = useDocumentStore((s) => s.doc?.addressing?.ipRange);
  const dirty = useDocumentStore((s) => s.dirty);
  const undo = useDocumentStore((s) => s.undo);
  const redo = useDocumentStore((s) => s.redo);
  const canUndo = useDocumentStore((s) => s.undoStack.length > 0);
  const canRedo = useDocumentStore((s) => s.redoStack.length > 0);
  const railOpen = useStudio2UI((s) => s.railOpen);
  const inspectorOpen = useStudio2UI((s) => s.inspectorOpen);
  const toggleRail = useStudio2UI((s) => s.toggleRail);
  const toggleInspector = useStudio2UI((s) => s.toggleInspector);
  const workspace = useStudio2UI((s) => s.workspace);
  const setWorkspace = useStudio2UI((s) => s.setWorkspace);
  const copilotOpen = useStudio2UI((s) => s.copilotOpen);
  const toggleCopilot = useStudio2UI((s) => s.toggleCopilot);
  const { aiEnabled, liveTrafficEnabled } = useFeatures();
  const { score, counts } = useHealth();
  const scoreStatus: StatusLevel = score >= 85 ? 'ok' : score >= 60 ? 'warn' : 'crit';

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        height: 46,
        padding: '0 14px',
        background: SURFACE.chrome,
        borderBottom: `1px solid ${SURFACE.border}`,
        fontFamily: FONT.ui,
        flex: '0 0 auto',
      }}
    >
      <button style={barButton} onClick={() => navigate('/scenarios')} aria-label="Back to scenarios">
        ◂ Scenarios
      </button>

      <span
        style={{
          fontSize: 14,
          fontWeight: 650,
          color: TEXT.primary,
          maxWidth: 320,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
        title={name}
      >
        {name}
      </span>

      {ipRange && (
        <span style={{ fontFamily: FONT.mono, fontSize: 11, color: TEXT.faint }}>{ipRange}</span>
      )}

      <span
        style={{
          fontFamily: FONT.mono,
          fontSize: 10,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          color: dirty ? STATUS.warn : STATUS.ok,
        }}
      >
        {dirty ? 'Unsaved' : 'Saved'}
      </span>

      <div style={{ display: 'flex', gap: 4 }}>
        <button
          style={{ ...barButton, opacity: canUndo ? 1 : 0.4, cursor: canUndo ? 'pointer' : 'default' }}
          onClick={undo}
          disabled={!canUndo}
          aria-label="Undo"
          title="Undo (Ctrl+Z)"
        >
          ↶
        </button>
        <button
          style={{ ...barButton, opacity: canRedo ? 1 : 0.4, cursor: canRedo ? 'pointer' : 'default' }}
          onClick={redo}
          disabled={!canRedo}
          aria-label="Redo"
          title="Redo (Ctrl+Shift+Z)"
        >
          ↷
        </button>
      </div>

      {/* Health chip — summary of the Verify workspace */}
      <button
        onClick={() => setWorkspace('verify')}
        title={`${counts.crit} critical · ${counts.warn} warnings — open Verify`}
        style={{
          ...barButton,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          borderColor: STATUS[scoreStatus],
          color: STATUS[scoreStatus],
          fontFamily: FONT.mono,
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        ● {score}
      </button>

      <div style={{ display: 'flex', gap: 4, marginLeft: 'auto' }}>
        {aiEnabled && (
          <button
            style={{ ...barButton, color: copilotOpen ? ACCENT : TEXT.faint }}
            onClick={toggleCopilot}
            aria-pressed={copilotOpen}
            title="AI copilot (Ctrl+J)"
          >
            ✦ Copilot
          </button>
        )}
        <button
          style={{ ...barButton, color: railOpen ? ACCENT : TEXT.faint }}
          onClick={toggleRail}
          aria-pressed={railOpen}
          title="Toggle device palette"
        >
          ▤ Palette
        </button>
        <button
          style={{ ...barButton, color: inspectorOpen ? ACCENT : TEXT.faint }}
          onClick={toggleInspector}
          aria-pressed={inspectorOpen}
          title="Toggle inspector"
        >
          Inspector ▤
        </button>
      </div>

      {/* Workspace switcher — Build is live; Verify/Run land in Phases 3–4 */}
      <div
        style={{
          display: 'flex',
          gap: 2,
          background: SURFACE.raised,
          border: `1px solid ${SURFACE.border}`,
          borderRadius: 7,
          padding: 2,
        }}
        role="tablist"
        aria-label="Workspace"
      >
        {WORKSPACES.map((w) => {
          const key = w.toLowerCase() as 'build' | 'verify' | 'run';
          const available = key !== 'run' || liveTrafficEnabled;
          const active = workspace === key;
          return (
            <button
              key={w}
              role="tab"
              aria-selected={active}
              disabled={!available}
              title={available ? undefined : 'Live traffic is disabled in this build'}
              onClick={() => available && setWorkspace(key)}
              style={{
                background: active ? ACCENT_SOFT : 'transparent',
                color: active ? ACCENT : available ? TEXT.secondary : TEXT.faint,
                border: 'none',
                borderRadius: 5,
                fontFamily: FONT.ui,
                fontSize: 12,
                fontWeight: 600,
                padding: '3px 12px',
                cursor: available ? 'pointer' : 'default',
              }}
            >
              {w}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default TopBar;
