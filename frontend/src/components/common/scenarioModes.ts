/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Helpers for building a `Modes` object from various scenario shapes.
 * Kept separate from the badge component so the component module only
 * exports components (Vite fast-refresh constraint).
 */
import type { Modes } from './ScenarioModeBadges';

/** Convenience: build a Modes object from a backend ScenarioSummary.modes. */
export function modesFromSummary(
  summary: { modes?: { clean_demo_mode?: boolean; broadcast_traffic_enabled?: boolean; cell_isolation_mode?: string } } | null | undefined,
): Modes {
  if (!summary?.modes) return {};
  return {
    cleanDemoMode: summary.modes.clean_demo_mode,
    broadcastTrafficEnabled: summary.modes.broadcast_traffic_enabled,
    cellIsolationMode: summary.modes.cell_isolation_mode,
  };
}

/** Convenience: build a Modes object from a raw scenario.definition object. */
export function modesFromDefinition(
  definition: Record<string, unknown> | null | undefined,
): Modes {
  if (!definition) return {};
  const ci = definition.cell_isolation as { mode?: string } | undefined;
  return {
    cleanDemoMode: definition.clean_demo_mode === true,
    broadcastTrafficEnabled: definition.broadcast_traffic_enabled !== false,
    cellIsolationMode: ci?.mode ?? 'off',
  };
}
