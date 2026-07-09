/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 health store + aggregation hook.
 *
 * Holds the fetched check results (backend validation, AI review) and
 * composes them with the always-on client checks (conduit compliance,
 * architecture rationality) into one findings list.
 */

import { useEffect, useMemo, useRef } from 'react';
import { create } from 'zustand';
import { useShallow } from 'zustand/react/shallow';
import { scenariosApi, type ScenarioValidationResponse } from '../../api/scenarios';
import { aiApi, type ScenarioReviewResponse, type RemediationAction } from '../../api/ai';
import {
  useRationalityStore,
  evaluateFlowRationality,
} from '../../stores/rationalityStore';
import { useDocumentStore, type ScenarioDocument } from '../document/documentStore';
import {
  conduitFindings,
  architectureFindings,
  readinessFindings,
  aiFindings,
  sortFindings,
  healthScore,
  statusMaps,
  type HealthFinding,
} from './health';

interface HealthState {
  validation: ScenarioValidationResponse | null;
  validationLoading: boolean;
  review: ScenarioReviewResponse | null;
  reviewLoading: boolean;
  reviewError: string | null;
  remediating: boolean;

  runValidation: (scenarioId: string) => Promise<void>;
  runReview: (scenarioId: string) => Promise<void>;
  remediate: (scenarioId: string, actions: RemediationAction[]) => Promise<boolean>;
  reset: () => void;
}

export const useHealthStore = create<HealthState>((set) => ({
  validation: null,
  validationLoading: false,
  review: null,
  reviewLoading: false,
  reviewError: null,
  remediating: false,

  runValidation: async (scenarioId) => {
    set({ validationLoading: true });
    try {
      const validation = await scenariosApi.validate(scenarioId);
      set({ validation, validationLoading: false });
    } catch {
      set({ validationLoading: false });
    }
  },

  runReview: async (scenarioId) => {
    set({ reviewLoading: true, reviewError: null });
    try {
      const review = await aiApi.reviewScenario(scenarioId);
      set({ review, reviewLoading: false });
    } catch (e) {
      set({
        reviewLoading: false,
        reviewError: e instanceof Error ? e.message : 'AI review failed',
      });
    }
  },

  remediate: async (scenarioId, actions) => {
    if (actions.length === 0) return false;
    set({ remediating: true });
    try {
      await aiApi.remediateScenario(scenarioId, actions);
      set({ remediating: false });
      return true;
    } catch {
      set({ remediating: false });
      return false;
    }
  },

  reset: () =>
    set({
      validation: null,
      validationLoading: false,
      review: null,
      reviewLoading: false,
      reviewError: null,
      remediating: false,
    }),
}));

/**
 * Drive architecture-rationality evaluation from the v2 document.
 * Reuses the shared rationality store/cache (same backend calls as v1).
 */
export function useRationalityEvaluator2(doc: ScenarioDocument | null): void {
  const flowsRef = useRef<string>('');
  useEffect(() => {
    if (!doc) return;
    const flowIds = Object.keys(doc.flows);
    const signature = `${doc.meta.vertical ?? ''}|${flowIds
      .map((id) => {
        const f = doc.flows[id];
        return `${id}:${f.protocol}:${f.sourceDeviceId}:${f.targetDeviceId}`;
      })
      .sort()
      .join(',')}`;
    if (signature === flowsRef.current) return;
    flowsRef.current = signature;

    useRationalityStore.getState().clearStale(new Set(flowIds));
    for (const flow of Object.values(doc.flows)) {
      void evaluateFlowRationality(flow, doc.devices, doc.meta.vertical);
    }
  }, [doc]);
}

export interface HealthSnapshot {
  findings: HealthFinding[];
  score: number;
  counts: { crit: number; warn: number; info: number };
  byDevice: Record<string, import('../tokens').StatusLevel>;
  byFlow: Record<string, import('../tokens').StatusLevel>;
}

/** Compose all sources into the unified health snapshot. */
export function useHealth(): HealthSnapshot {
  const doc = useDocumentStore((s) => s.doc);
  const rationality = useRationalityStore(useShallow((s) => s.results));
  const validation = useHealthStore((s) => s.validation);
  const review = useHealthStore((s) => s.review);

  return useMemo(() => {
    const findings = doc
      ? sortFindings([
          ...conduitFindings(doc),
          ...architectureFindings(doc, rationality),
          ...readinessFindings(validation),
          ...aiFindings(review),
        ])
      : [];
    const counts = {
      crit: findings.filter((f) => f.severity === 'crit').length,
      warn: findings.filter((f) => f.severity === 'warn').length,
      info: findings.filter((f) => f.severity === 'info').length,
    };
    const { byDevice, byFlow } = statusMaps(findings);
    return { findings, score: healthScore(findings), counts, byDevice, byFlow };
  }, [doc, rationality, validation, review]);
}
