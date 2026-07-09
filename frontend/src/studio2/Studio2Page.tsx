/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 (Phase 1 foundation) — parallel route `/studio2?scenario=<id>`.
 *
 * Reads and writes the same backend scenario definition as v1, through the
 * single codec. Four docked regions frame the canvas: top bar, (rail — Phase
 * 1 cont.), inspector (Phase 1 cont.), bottom strip. Nothing floats.
 */

import React, { useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { message, Spin } from 'antd';
import { ReactFlowProvider } from '@xyflow/react';

import { scenariosApi } from '../api/scenarios';
import { scenarioVersionsApi } from '../api/scenarioVersions';
import { useDocumentStore } from './document/documentStore';
import { parseScenario, buildUpdatePayload } from './document/codec';
import Studio2Canvas from './canvas/Studio2Canvas';
import TopBar from './shell/TopBar';
import BottomStrip from './shell/BottomStrip';
import Rail from './shell/Rail';
import Inspector from './shell/Inspector';
import { useStudio2UI } from './uiState';
import { SURFACE } from './tokens';

const AUTOSAVE_DEBOUNCE_MS = 2000;

const Studio2Page: React.FC = () => {
  const [searchParams] = useSearchParams();
  const scenarioId = searchParams.get('scenario');
  const navigate = useNavigate();
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const loadDocument = useDocumentStore((s) => s.loadDocument);
  const closeDocument = useDocumentStore((s) => s.closeDocument);
  const dirty = useDocumentStore((s) => s.dirty);
  const docId = useDocumentStore((s) => s.doc?.meta.id ?? null);
  const railOpen = useStudio2UI((s) => s.railOpen);
  const inspectorOpen = useStudio2UI((s) => s.inspectorOpen);

  useEffect(() => {
    if (!scenarioId) navigate('/scenarios', { replace: true });
  }, [scenarioId, navigate]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['scenario', scenarioId],
    queryFn: () => scenariosApi.get(scenarioId!),
    enabled: !!scenarioId,
  });

  useEffect(() => {
    if (data && data.id === scenarioId) {
      try {
        loadDocument(parseScenario(data));
      } catch (e) {
        console.error('Failed to parse scenario', e);
        message.error('Failed to parse scenario definition');
      }
    }
  }, [data, scenarioId, loadDocument]);

  useEffect(() => () => closeDocument(), [closeDocument]);

  useEffect(() => {
    if (error) {
      message.error('Failed to load scenario');
      navigate('/scenarios');
    }
  }, [error, navigate]);

  // Auto-save: debounce on dirty, race-guarded by scenario id, one codec.
  useEffect(() => {
    if (!dirty || !docId) return;
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    const targetId = docId;
    saveTimeoutRef.current = setTimeout(async () => {
      const state = useDocumentStore.getState();
      if (!state.doc || state.doc.meta.id !== targetId) return;
      try {
        await scenariosApi.update(targetId, buildUpdatePayload(state.doc));
        if (useDocumentStore.getState().doc?.meta.id === targetId) {
          useDocumentStore.getState().markSaved();
          message.success('Scenario saved', 1);
        }
      } catch {
        message.error('Failed to save scenario');
      }
    }, AUTOSAVE_DEBOUNCE_MS);
    return () => {
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    };
  }, [dirty, docId]);

  // Keyboard: Ctrl+S save + version (same codec as autosave), Ctrl+Z/Y undo/redo.
  useEffect(() => {
    const handler = async (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey;
      if (!mod) return;
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.key === 's') {
        e.preventDefault();
        const state = useDocumentStore.getState();
        if (!state.doc) return;
        if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
        try {
          await scenariosApi.update(state.doc.meta.id, buildUpdatePayload(state.doc));
          state.markSaved();
          const version = await scenarioVersionsApi.create(state.doc.meta.id);
          message.success(`Version ${version.version_number} saved`);
        } catch {
          message.error('Failed to save version');
        }
      } else if (e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        useDocumentStore.getState().undo();
      } else if (e.key === 'y' || (e.key === 'z' && e.shiftKey) || (e.key === 'Z' && e.shiftKey)) {
        e.preventDefault();
        useDocumentStore.getState().redo();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  if (isLoading || !docId) {
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: SURFACE.ground,
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  return (
    <ReactFlowProvider>
      <div
        style={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          background: SURFACE.ground,
        }}
      >
        <TopBar />
        <div style={{ flex: 1, minHeight: 0, display: 'flex' }}>
          {railOpen && <Rail />}
          <div style={{ flex: 1, minWidth: 0 }}>
            <Studio2Canvas />
          </div>
          {inspectorOpen && <Inspector />}
        </div>
        <BottomStrip />
      </div>
    </ReactFlowProvider>
  );
};

export default Studio2Page;
