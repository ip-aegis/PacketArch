/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Phase constants for deployment configuration.
 * Values match PHASE_TEMPLATES in backend/app/scenario_templates/phases.py.
 */

/** Map frontend phase name to backend phase_id. */
export const PHASE_NAME_MAP: Record<string, string> = {
  startup: 'startup',
  'steady-state': 'steady_state',
  maintenance: 'maintenance',
  shutdown: 'shutdown',
  custom: 'custom',
};

/** Default live durations per phase type (seconds). */
export const DEFAULT_LIVE_DURATIONS: Record<string, number> = {
  startup: 300,
  'steady-state': 3600,
  maintenance: 900,
  shutdown: 300,
  custom: 600,
};
