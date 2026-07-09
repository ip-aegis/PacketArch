/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 AI copilot flyout (Cmd/Ctrl+J) — a summonable chat surface
 * over the canvas, replacing v1's persistent AI tab. Reuses the proven
 * ChatInterface/ChatInput and the shared assistant store/session.
 */

import React, { useEffect } from 'react';
import ChatInterface from '../../components/ai/ChatInterface';
import ChatInput from '../../components/ai/ChatInput';
import { useAIAssistantStore } from '../../stores/aiAssistantStore';
import { useDocumentStore } from '../document/documentStore';
import { useStudio2UI } from '../uiState';
import { SURFACE, TEXT, ACCENT, FONT, STATUS } from '../tokens';

const CopilotFlyout: React.FC = () => {
  const scenarioId = useDocumentStore((s) => s.doc?.meta.id ?? null);
  const toggleCopilot = useStudio2UI((s) => s.toggleCopilot);
  const isConnected = useAIAssistantStore((s) => s.isConnected);
  const isProcessing = useAIAssistantStore((s) => s.isProcessing);
  const openPanel = useAIAssistantStore((s) => s.openPanel);

  useEffect(() => {
    if (scenarioId && !isConnected) {
      void openPanel(scenarioId);
    }
  }, [scenarioId, isConnected, openPanel]);

  return (
    <div
      role="dialog"
      aria-label="AI copilot"
      style={{
        position: 'absolute',
        top: 10,
        right: 10,
        bottom: 10,
        width: 370,
        zIndex: 30,
        display: 'flex',
        flexDirection: 'column',
        background: SURFACE.chrome,
        border: `1px solid ${SURFACE.border}`,
        borderRadius: 12,
        boxShadow: '0 10px 40px rgba(0,0,0,0.55)',
        overflow: 'hidden',
        fontFamily: FONT.ui,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '9px 12px',
          borderBottom: `1px solid ${SURFACE.border}`,
        }}
      >
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: isConnected ? STATUS.ok : TEXT.faint,
          }}
        />
        <span style={{ fontSize: 12.5, fontWeight: 650, color: TEXT.primary }}>AI copilot</span>
        <span style={{ fontFamily: FONT.mono, fontSize: 9.5, color: TEXT.faint }}>⌘J</span>
        <button
          onClick={toggleCopilot}
          aria-label="Close copilot"
          style={{
            marginLeft: 'auto',
            background: 'transparent',
            border: 'none',
            color: TEXT.muted,
            fontSize: 14,
            cursor: 'pointer',
            padding: '0 4px',
          }}
        >
          ✕
        </button>
      </div>
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
          <ChatInterface />
        </div>
        <div style={{ borderTop: `1px solid ${ACCENT}22`, padding: 8 }}>
          <ChatInput disabled={!isConnected || isProcessing} />
        </div>
      </div>
    </div>
  );
};

export default CopilotFlyout;
