/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 codec — the ONLY place scenario data crosses the API boundary.
 *
 * Load, auto-save, explicit save (Ctrl+S), and version snapshots all go
 * through `parseScenario` / `buildUpdatePayload`, so a field can never be
 * saved by one path and dropped by another (the v1 Ctrl+S bug: the backend
 * replaces `definition` wholesale, and a hand-rolled second serializer
 * omitted three mode fields — wiping them and baking the loss into the
 * version snapshot).
 *
 * Validation is deliberately shallow (`passthrough`): the codec guarantees
 * structure — records keyed by entity id, arrays where expected — and
 * round-trips every unknown field untouched so v1 and v2 can share
 * scenarios during the migration.
 */

import { z } from 'zod';
import type { ScenarioDetail } from '../../api/scenarios';
import type {
  ScenarioDevice,
  ScenarioFlow,
  ScenarioZone,
  ScenarioConduit,
  Phase,
  CellIsolationConfig,
  VerticalType,
} from '../../types';
import type { ScenarioDocument } from './documentStore';

// ---------------------------------------------------------------------------
// Schemas — shallow by design; unknown fields pass through
// ---------------------------------------------------------------------------

const entity = z.object({ id: z.string() }).passthrough();

/**
 * Entity records re-keyed by each object's own `id`. The legacy AI
 * freeform builder keyed zones by slugified name while the object's `id`
 * differed — lookups by id must always work.
 */
const entityRecord = z
  .record(z.string(), entity)
  .default({})
  .transform((records) => {
    const out: Record<string, z.infer<typeof entity>> = {};
    for (const [key, value] of Object.entries(records)) {
      out[value.id ?? key] = value;
    }
    return out;
  });

const definitionSchema = z
  .object({
    devices: entityRecord,
    flows: entityRecord,
    zones: entityRecord,
    conduits: entityRecord,
    phases: z.array(z.unknown()).default([]),
    cell_isolation: z.unknown().optional(),
    broadcast_traffic_enabled: z.boolean().optional(),
    clean_demo_mode: z.boolean().optional(),
  })
  .passthrough();

const addressingSchema = z
  .object({
    ip_range: z.string().optional(),
    auto_assign_enabled: z.boolean().optional(),
  })
  .passthrough()
  .nullable()
  .optional();

// ---------------------------------------------------------------------------
// API → document
// ---------------------------------------------------------------------------

const KNOWN_DEFINITION_KEYS = new Set([
  'devices',
  'flows',
  'zones',
  'conduits',
  'phases',
  'cell_isolation',
  'broadcast_traffic_enabled',
  'clean_demo_mode',
]);

export function parseScenario(detail: ScenarioDetail): ScenarioDocument {
  const definition = definitionSchema.parse(detail.definition ?? {});
  const addressing = addressingSchema.parse(detail.addressing_config);

  const definitionExtras: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(definition)) {
    if (!KNOWN_DEFINITION_KEYS.has(key)) definitionExtras[key] = value;
  }

  return {
    meta: {
      id: detail.id,
      name: detail.name,
      description: detail.description ?? '',
      vertical: (detail.vertical ?? undefined) as VerticalType | undefined,
      totalDurationMs: detail.total_duration_ms,
      cellIsolation: definition.cell_isolation as CellIsolationConfig | undefined,
      broadcastTrafficEnabled: definition.broadcast_traffic_enabled,
      cleanDemoMode: definition.clean_demo_mode,
    },
    devices: definition.devices as unknown as Record<string, ScenarioDevice>,
    flows: definition.flows as unknown as Record<string, ScenarioFlow>,
    zones: definition.zones as unknown as Record<string, ScenarioZone>,
    conduits: definition.conduits as unknown as Record<string, ScenarioConduit>,
    phases: definition.phases as Phase[],
    addressing: addressing
      ? { ipRange: addressing.ip_range, autoAssignEnabled: addressing.auto_assign_enabled }
      : null,
    definitionExtras,
  };
}

// ---------------------------------------------------------------------------
// Document → API
// ---------------------------------------------------------------------------

export function buildUpdatePayload(doc: ScenarioDocument) {
  return {
    name: doc.meta.name,
    description: doc.meta.description,
    vertical: doc.meta.vertical,
    total_duration_ms: doc.meta.totalDurationMs,
    definition: {
      ...doc.definitionExtras,
      devices: doc.devices,
      flows: doc.flows,
      zones: doc.zones,
      conduits: doc.conduits,
      phases: doc.phases,
      cell_isolation: doc.meta.cellIsolation,
      broadcast_traffic_enabled: doc.meta.broadcastTrafficEnabled,
      clean_demo_mode: doc.meta.cleanDemoMode,
    },
  };
}
