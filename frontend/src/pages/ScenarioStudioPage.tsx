/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Scenario Studio Page - Complete Canvas Implementation
 * Main page integrating canvas, palette, property panel, and timeline
 */

import React, { useEffect, useCallback, useRef, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { message, Spin, Button, Tooltip, Alert, Progress } from 'antd';
import { DoubleLeftOutlined } from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useShallow } from 'zustand/react/shallow';

import ScenarioCanvas from '../components/canvas/ScenarioCanvas';
import DevicePalette from '../components/palette/DevicePalette';
import RightSidePanel from '../components/panels/RightSidePanel';
import TimelineEditor from '../components/timeline/TimelineEditor';
import { useScenarioStore } from '../stores/scenarioStore';
import { useUIStore } from '../stores/uiStore';
import { scenariosApi } from '../api/scenarios';
import { scenarioVersionsApi } from '../api/scenarioVersions';
import { useScenarioLifecycle } from '../hooks/useScenarioLifecycle';

const ScenarioStudioPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const scenarioId = searchParams.get('scenario');
  const navigate = useNavigate();
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Lifecycle manager for coordinated store resets
  const lifecycle = useScenarioLifecycle();

  // Store state - use individual selectors to avoid creating new object references
  const loadScenario = useScenarioStore((state) => state.loadScenario);
  const isDirty = useScenarioStore((state) => state.isDirty);
  const setDirty = useScenarioStore((state) => state.setDirty);
  const storeScenarioId = useScenarioStore((state) => state.id);

  // Use shallow comparison for the scenario state object (for auto-save)
  const scenarioState = useScenarioStore(
    useShallow((state) => ({
      id: state.id,
      name: state.name,
      description: state.description,
      vertical: state.vertical,
      totalDurationMs: state.totalDurationMs,
      devices: state.devices,
      flows: state.flows,
      zones: state.zones,
      phases: state.phases,
    }))
  );

  // UI state
  const leftSidebarOpen = useUIStore((state) => state.panels.leftSidebarOpen);
  const rightSidebarOpen = useUIStore((state) => state.panels.rightSidebarOpen);
  const bottomPanelOpen = useUIStore((state) => state.panels.bottomPanelOpen);
  const toggleLeftSidebar = useUIStore((state) => state.toggleLeftSidebar);
  const toggleRightSidebar = useUIStore((state) => state.toggleRightSidebar);

  // Auto-collapse the global left nav while in the Studio so the canvas has
  // more horizontal room. Restore the user's previous preference on exit.
  useEffect(() => {
    const wasOpen = useUIStore.getState().panels.leftSidebarOpen;
    if (wasOpen) toggleLeftSidebar();
    return () => {
      const isOpen = useUIStore.getState().panels.leftSidebarOpen;
      if (wasOpen && !isOpen) toggleLeftSidebar();
    };
    // Run once on mount / cleanup on unmount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Redirect blank /studio to /scenarios
  useEffect(() => {
    if (!scenarioId) {
      navigate('/scenarios', { replace: true });
    }
  }, [scenarioId, navigate]);

  // Handle scenario switching with lifecycle manager
  useEffect(() => {
    if (scenarioId) {
      // Reset all stores and get new abort signal
      lifecycle.switchScenario(scenarioId);

      // Create new abort controller for this scenario's operations
      abortControllerRef.current = new AbortController();
    }

    return () => {
      // Cancel any pending operations when switching away
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [scenarioId, lifecycle]);

  // While background AI device-naming is in progress, poll the scenario
  // so the canvas swaps in the LLM-generated names when they land. Capped
  // at 3 min so a stuck/disabled worker doesn't poll forever — the
  // deterministic names already in place remain the fallback.
  const namingPollStartRef = useRef<number | null>(null);

  // Load scenario if editing existing one
  const { data: scenarioData, isLoading, error } = useQuery({
    queryKey: ['scenario', scenarioId],
    queryFn: () => scenariosApi.get(scenarioId!),
    enabled: !!scenarioId,
    refetchInterval: (query) => {
      const status = query.state.data?.naming_status;
      const active = status === 'pending' || status === 'running';
      if (!active) {
        namingPollStartRef.current = null;
        return false;
      }
      const now = Date.now();
      if (namingPollStartRef.current === null) {
        namingPollStartRef.current = now;
      }
      if (now - namingPollStartRef.current > 180_000) {
        return false;
      }
      return 2000;
    },
  });
  const namingInProgress =
    scenarioData?.naming_status === 'pending' ||
    scenarioData?.naming_status === 'running';
  const namingFailed = scenarioData?.naming_status === 'failed';

  // Client-side progress estimate: the LLM calls are opaque, so we creep
  // toward 95% over the typical ~150s and let the 'done' transition snap
  // it to 100%. Purely cosmetic — the real gate is naming_status.
  const queryClient = useQueryClient();
  const [namingPct, setNamingPct] = useState(0);
  const [retryingNaming, setRetryingNaming] = useState(false);

  useEffect(() => {
    if (!namingInProgress) {
      setNamingPct(0);
      return;
    }
    setNamingPct((p) => (p > 0 ? p : 8));
    const t = setInterval(() => {
      setNamingPct((p) => (p < 95 ? Math.min(95, p + 3) : p));
    }, 5000);
    return () => clearInterval(t);
  }, [namingInProgress]);

  const handleRetryNaming = useCallback(async () => {
    if (!scenarioId) return;
    setRetryingNaming(true);
    try {
      await scenariosApi.retryNaming(scenarioId);
      await queryClient.invalidateQueries({ queryKey: ['scenario', scenarioId] });
    } catch {
      message.error('Failed to restart device naming');
    } finally {
      setRetryingNaming(false);
    }
  }, [scenarioId, queryClient]);

  // Load scenario data when query succeeds - with race condition protection
  useEffect(() => {
    if (scenarioData) {
      // Race condition protection: ensure this data is for the current scenario
      if (scenarioData.id !== scenarioId) {
        console.warn('Ignoring stale scenario data', { received: scenarioData.id, expected: scenarioId });
        return;
      }

      const definition = scenarioData.definition as {
        devices?: Record<string, unknown>;
        flows?: Record<string, unknown>;
        zones?: Record<string, unknown>;
        conduits?: Record<string, unknown>;
        phases?: unknown[];
        cell_isolation?: import('../types').CellIsolationConfig;
        broadcast_traffic_enabled?: boolean;
        clean_demo_mode?: boolean;
      };

      // Defensive shim: ensure devices / flows / zones / conduits are
      // keyed by their `id` field, not by some other key the backend
      // happened to use. The legacy AI freeform builder keys zones by
      // their slugified name (e.g. "Mixing_Cell") while the zone object
      // itself has `id="zone_mixing"` — that mismatch makes
      // `state.zones[zoneId]` lookups fail in property forms when the
      // canvas reports clicks by `zone.id`.
      const rekey = <T extends { id?: string }>(
        records: Record<string, T> | undefined,
      ): Record<string, T> => {
        if (!records) return {};
        const out: Record<string, T> = {};
        for (const [k, v] of Object.entries(records)) {
          const id = (v && (v.id ?? k)) as string;
          out[id] = v;
        }
        return out;
      };

      loadScenario({
        id: scenarioData.id,
        name: scenarioData.name,
        description: scenarioData.description || '',
        vertical: scenarioData.vertical || undefined,
        totalDurationMs: scenarioData.total_duration_ms,
        devices: rekey(definition?.devices as Record<string, import('../types').ScenarioDevice>),
        flows: rekey(definition?.flows as Record<string, import('../types').ScenarioFlow>),
        zones: rekey(definition?.zones as Record<string, import('../types').ScenarioZone>),
        conduits: rekey(definition?.conduits as Record<string, import('../types').ScenarioConduit>),
        phases: (definition?.phases || []) as import('../types').Phase[],
        cellIsolation: definition?.cell_isolation,
        broadcastTrafficEnabled: definition?.broadcast_traffic_enabled,
        cleanDemoMode: definition?.clean_demo_mode,
        // Include addressingConfig for IP range info
        addressingConfig: scenarioData.addressing_config as {
          ip_range?: string;
          range_index?: number;
          auto_assign_enabled?: boolean;
        } | null,
      });
    }
  }, [scenarioData, scenarioId, loadScenario]);

  // Handle errors
  useEffect(() => {
    if (error) {
      message.error('Failed to load scenario');
      navigate('/scenarios');
    }
  }, [error, navigate]);

  // Race-safe auto-save with debounce
  useEffect(() => {
    if (!isDirty || !storeScenarioId) return;

    // Clear previous timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    // Capture the scenario ID at the time of scheduling
    const targetScenarioId = storeScenarioId;

    // Set new timeout
    saveTimeoutRef.current = setTimeout(async () => {
      // Get CURRENT state at save time (not stale closure)
      const currentState = useScenarioStore.getState();

      // Race condition protection: verify still on the same scenario
      if (currentState.id !== targetScenarioId) {
        console.warn('Auto-save skipped: scenario changed');
        return;
      }

      try {
        await scenariosApi.update(targetScenarioId, {
          name: currentState.name,
          description: currentState.description,
          vertical: currentState.vertical,
          total_duration_ms: currentState.totalDurationMs,
          definition: {
            devices: currentState.devices,
            flows: currentState.flows,
            zones: currentState.zones,
            conduits: currentState.conduits,
            phases: currentState.phases,
            cell_isolation: currentState.cellIsolation,
            broadcast_traffic_enabled: currentState.broadcastTrafficEnabled,
            clean_demo_mode: currentState.cleanDemoMode,
          },
        });

        // Only clear dirty if still on the same scenario
        if (useScenarioStore.getState().id === targetScenarioId) {
          setDirty(false);
          message.success('Scenario saved', 1);
        }
      } catch (error) {
        if ((error as Error).name !== 'AbortError') {
          message.error('Failed to save scenario');
        }
      }
    }, 2000);

    // Register timeout with lifecycle for cleanup on scenario switch
    lifecycle.setSaveTimeout(saveTimeoutRef.current);

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [isDirty, storeScenarioId, setDirty, lifecycle]);

  // Ctrl+S / Cmd+S: save explicit version
  useEffect(() => {
    const handleKeyDown = async (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();

        const currentState = useScenarioStore.getState();
        if (!currentState.id) return;

        try {
          // Flush pending changes first
          if (saveTimeoutRef.current) {
            clearTimeout(saveTimeoutRef.current);
          }
          await scenariosApi.update(currentState.id, {
            name: currentState.name,
            description: currentState.description,
            vertical: currentState.vertical,
            total_duration_ms: currentState.totalDurationMs,
            definition: {
              devices: currentState.devices,
              flows: currentState.flows,
              zones: currentState.zones,
              conduits: currentState.conduits,
              phases: currentState.phases,
            },
          });
          setDirty(false);

          // Create explicit version
          const version = await scenarioVersionsApi.create(currentState.id);
          message.success(`Version ${version.version_number} saved`);
        } catch {
          message.error('Failed to save version');
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setDirty]);

  // Handle canvas drag/drop - actual drop is handled inside canvas
  const onCanvasDrop = useCallback(
    (_event: React.DragEvent<HTMLDivElement>) => {
      // The actual drop handling is done inside the canvas component
      // which has access to React Flow context
    },
    []
  );

  const onCanvasDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
  }, []);

  if (isLoading) {
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin size="large" tip="Loading scenario..." />
      </div>
    );
  }

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Background AI-naming progress banner */}
      {namingInProgress && (
        <Alert
          type="info"
          showIcon
          banner
          message={
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ whiteSpace: 'nowrap' }}>
                Generating descriptive device names… deploy is disabled until
                this finishes (usually 1–2 min).
              </span>
              <Progress
                percent={namingPct}
                status="active"
                showInfo={false}
                style={{ flex: 1, marginBottom: 0 }}
              />
            </div>
          }
        />
      )}

      {/* Naming failed — offer a retry */}
      {namingFailed && (
        <Alert
          type="warning"
          showIcon
          banner
          message="Device naming didn't finish. The scenario is usable with basic names; you can retry the descriptive naming."
          action={
            <Button
              size="small"
              loading={retryingNaming}
              onClick={handleRetryNaming}
            >
              Retry naming
            </Button>
          }
        />
      )}

      {/* Main content area */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* Left sidebar - Device Palette */}
        {leftSidebarOpen && <DevicePalette />}

        {/* Center - Canvas */}
        <div
          style={{
            flex: 1,
            position: 'relative',
            background: '#dce4ed',
          }}
        >
          {/* Key prop forces remount when scenario changes, resetting local state */}
          <ScenarioCanvas
            key={scenarioId || 'new'}
            onDrop={onCanvasDrop}
            onDragOver={onCanvasDragOver}
          />

          {/* Peek tab to bring the right panel back when hidden */}
          {!rightSidebarOpen && (
            <Tooltip title="Show right panel" placement="left">
              <Button
                size="small"
                icon={<DoubleLeftOutlined />}
                onClick={toggleRightSidebar}
                style={{
                  position: 'absolute',
                  top: 96,
                  right: 0,
                  zIndex: 10,
                  borderTopRightRadius: 0,
                  borderBottomRightRadius: 0,
                  background: '#1a2734',
                  borderColor: '#2a3f54',
                  color: '#b8c9dc',
                }}
              />
            </Tooltip>
          )}
        </div>

        {/* Right sidebar - Combined Properties & AI Panel */}
        {rightSidebarOpen && <RightSidePanel scenarioId={scenarioState.id || scenarioId} />}
      </div>

      {/* Bottom panel - Timeline Editor */}
      {bottomPanelOpen && <TimelineEditor />}
    </div>
  );
};

export default ScenarioStudioPage;
