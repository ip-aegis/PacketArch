/**
 * Scenario Studio Page - Complete Canvas Implementation
 * Main page integrating canvas, palette, property panel, and timeline
 */

import React, { useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { message, Spin } from 'antd';
import { useQuery } from '@tanstack/react-query';
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

  // Load scenario if editing existing one
  const { data: scenarioData, isLoading, error } = useQuery({
    queryKey: ['scenario', scenarioId],
    queryFn: () => scenariosApi.get(scenarioId!),
    enabled: !!scenarioId,
  });

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
        phases?: unknown[];
      };

      loadScenario({
        id: scenarioData.id,
        name: scenarioData.name,
        description: scenarioData.description || '',
        vertical: scenarioData.vertical || undefined,
        totalDurationMs: scenarioData.total_duration_ms,
        devices: (definition?.devices || {}) as Record<string, import('../types').ScenarioDevice>,
        flows: (definition?.flows || {}) as Record<string, import('../types').ScenarioFlow>,
        zones: (definition?.zones || {}) as Record<string, import('../types').ScenarioZone>,
        phases: (definition?.phases || []) as import('../types').Phase[],
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
            phases: currentState.phases,
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
