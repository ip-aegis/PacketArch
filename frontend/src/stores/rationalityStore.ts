/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Rationality cache for flow rationality hints (Phase 7).
 *
 * The canvas evaluates every flow against `/architecture/check-flow`
 * and caches results here. Cache key: `flowId` — re-checks fire
 * automatically when (src_role, tgt_role, vertical, protocol) change.
 *
 * Why a store: the FlowEdge component needs the result to render a
 * color hint, and the CanvasControls panel needs aggregate counts.
 * Both subscribe to this store; the hook below populates it lazily.
 */

import { create } from 'zustand';
import { useShallow } from 'zustand/react/shallow';
import { architectureApi, type FlowCheckResponse } from '../api/architecture';
import { resolveArchitecturalRole } from '../utils/architecturalRole';
import type { ScenarioDevice, ScenarioFlow } from '../types';

export interface FlowRationality {
  flowId: string;
  inMatrix: boolean;
  suggestion: string | null;
  // 'ok'      — matrix entry exists for this role pair AND protocol matches
  // 'mismatch'— matrix entry exists for the role pair but protocol doesn't
  // 'off-rail'— no matrix entry for the role pair (or roles unknown)
  status: 'ok' | 'mismatch' | 'off-rail' | 'unknown';
  /** Diagnostic key: snapshot of inputs the result was computed from. */
  cacheKey: string;
  /** Last-error string if the API call failed. */
  error?: string;
}

interface RationalityState {
  results: Record<string, FlowRationality>;
  evaluating: Set<string>;
  setResult: (r: FlowRationality) => void;
  markEvaluating: (flowId: string) => void;
  clearStale: (validFlowIds: Set<string>) => void;
  reset: () => void;
}

export const useRationalityStore = create<RationalityState>((set) => ({
  results: {},
  evaluating: new Set<string>(),
  setResult: (r) =>
    set((s) => {
      const evaluating = new Set(s.evaluating);
      evaluating.delete(r.flowId);
      return { results: { ...s.results, [r.flowId]: r }, evaluating };
    }),
  markEvaluating: (flowId) =>
    set((s) => {
      const evaluating = new Set(s.evaluating);
      evaluating.add(flowId);
      return { evaluating };
    }),
  clearStale: (validFlowIds) =>
    set((s) => {
      // No-op fast path: if every key in current results is still
      // valid, return the existing state object so subscribers don't
      // see a fake change. This prevents the "summary recomputes on
      // every effect run even when nothing changed" cascade that
      // pegged React (#185 max-update-depth) when the studio loads.
      const currentKeys = Object.keys(s.results);
      let hasStale = false;
      for (const k of currentKeys) {
        if (!validFlowIds.has(k)) {
          hasStale = true;
          break;
        }
      }
      if (!hasStale) return {};
      const out: Record<string, FlowRationality> = {};
      for (const [fid, r] of Object.entries(s.results)) {
        if (validFlowIds.has(fid)) out[fid] = r;
      }
      return { results: out };
    }),
  reset: () =>
    set({ results: {}, evaluating: new Set<string>() }),
}));


// ---------------------------------------------------------------------------
// Cache key + evaluator
// ---------------------------------------------------------------------------

function cacheKey(
  srcRole: string | null,
  tgtRole: string | null,
  vertical: string,
  protocol: string,
): string {
  return `${srcRole || '_'}|${tgtRole || '_'}|${vertical}|${protocol}`;
}


/**
 * Evaluate one flow against the matrix and write the result to the
 * store. Cheap-cached: re-runs only when `cacheKey` changes.
 */
export async function evaluateFlowRationality(
  flow: ScenarioFlow,
  devices: Record<string, ScenarioDevice>,
  vertical: string | undefined,
): Promise<FlowRationality | null> {
  const src = devices[flow.sourceDeviceId];
  const tgt = devices[flow.targetDeviceId];
  if (!src || !tgt || !vertical) return null;

  const srcRole = resolveArchitecturalRole(src);
  const tgtRole = resolveArchitecturalRole(tgt);
  const protocol = flow.protocol;

  if (!srcRole || !tgtRole) {
    const out: FlowRationality = {
      flowId: flow.id,
      inMatrix: false,
      suggestion: null,
      status: 'unknown',
      cacheKey: cacheKey(srcRole, tgtRole, vertical, protocol),
    };
    useRationalityStore.getState().setResult(out);
    return out;
  }

  const key = cacheKey(srcRole, tgtRole, vertical, protocol);
  const existing = useRationalityStore.getState().results[flow.id];
  if (existing && existing.cacheKey === key) return existing;

  try {
    const res: FlowCheckResponse = await architectureApi.checkFlow({
      src_role: srcRole,
      tgt_role: tgtRole,
      vertical,
      protocol,
    });
    let status: FlowRationality['status'];
    if (!res.in_matrix) {
      status = 'off-rail';
    } else if (res.suggestion) {
      // in_matrix but suggestion present → protocol mismatch
      status = 'mismatch';
    } else {
      status = 'ok';
    }
    const out: FlowRationality = {
      flowId: flow.id,
      inMatrix: res.in_matrix,
      suggestion: res.suggestion,
      status,
      cacheKey: key,
    };
    useRationalityStore.getState().setResult(out);
    return out;
  } catch (e) {
    const err = e instanceof Error ? e.message : String(e);
    const out: FlowRationality = {
      flowId: flow.id,
      inMatrix: false,
      suggestion: null,
      status: 'unknown',
      cacheKey: key,
      error: err,
    };
    useRationalityStore.getState().setResult(out);
    return out;
  }
}


// ---------------------------------------------------------------------------
// Selectors
// ---------------------------------------------------------------------------

export const useFlowRationality = (flowId: string) =>
  useRationalityStore((s) => s.results[flowId]);

/**
 * Aggregate score for the Studio canvas badge. Wrapped in `useShallow`
 * so the selector's freshly-built object is shallow-compared against
 * the previous value — re-renders only fire when one of the counts
 * actually changed, not on every store mutation.
 *
 * This is the load-bearing fix for the React #185 (max-update-depth)
 * loop that hit when studio loaded a scenario with many flows: each
 * setResult would otherwise trigger a re-render of every component
 * consuming the summary, even when no count changed.
 */
export const useRationalitySummary = () =>
  useRationalityStore(
    useShallow((s) => {
      let ok = 0;
      let mismatch = 0;
      let offRail = 0;
      let unknown = 0;
      for (const r of Object.values(s.results)) {
        if (r.status === 'ok') ok += 1;
        else if (r.status === 'mismatch') mismatch += 1;
        else if (r.status === 'off-rail') offRail += 1;
        else unknown += 1;
      }
      const total = ok + mismatch + offRail + unknown;
      return {
        ok,
        mismatch,
        offRail,
        unknown,
        total,
        score: total === 0 ? 100 : Math.round((ok / total) * 100),
      };
    }),
  );
