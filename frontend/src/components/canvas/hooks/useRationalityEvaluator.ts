/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Background evaluator for canvas flow rationality (Phase 7).
 *
 * Watches flows + devices + vertical, calls
 * `architectureApi.checkFlow()` for each flow, and writes results to
 * `rationalityStore`. The FlowEdge component and CanvasControls panel
 * subscribe to those results.
 */

import { useEffect } from 'react';
import { useScenarioStore } from '../../../stores/scenarioStore';
import {
  evaluateFlowRationality,
  useRationalityStore,
} from '../../../stores/rationalityStore';

/**
 * Subscribes to the scenario store; on every flow / device / vertical
 * change, re-evaluates affected flows. Cheap because the store caches
 * results by `cacheKey` and skips re-evaluation when inputs haven't
 * changed.
 *
 * Mounted once at the top of `ScenarioCanvas`.
 */
export function useRationalityEvaluator(): void {
  const flows = useScenarioStore((s) => s.flows);
  const devices = useScenarioStore((s) => s.devices);
  const vertical = useScenarioStore((s) => s.vertical);

  useEffect(() => {
    if (!vertical) return;
    // Snapshot the current set of valid flow ids; clearStale is a
    // no-op when nothing changed (rationalityStore enforces that).
    const flowIds = new Set(Object.keys(flows));
    useRationalityStore.getState().clearStale(flowIds);
    // Evaluate each flow. The evaluator caches by (src_role, tgt_role,
    // vertical, protocol) and skips writes when nothing changed.
    for (const flow of Object.values(flows)) {
      void evaluateFlowRationality(flow, devices, vertical);
    }
  }, [flows, devices, vertical]);
}
