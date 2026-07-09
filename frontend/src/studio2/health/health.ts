/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 Scenario Health — ONE findings model over the four check
 * surfaces that were separate UIs in v1 (rationality popover, per-edge
 * compliance emoji, deploy readiness checklist, AI review drawer).
 *
 * Everything is normalized to a HealthFinding with one severity scale;
 * the Verify workspace renders the list, Build mode shows only a status
 * dot per element (worst finding wins).
 */

import type { ScenarioDocument } from '../document/documentStore';
import type { FlowRationality } from '../../stores/rationalityStore';
import type { ScenarioValidationResponse } from '../../api/scenarios';
import type { ScenarioReviewResponse, RemediationAction } from '../../api/ai';
import type { StatusLevel } from '../tokens';

export type HealthSeverity = 'crit' | 'warn' | 'info';

export type HealthSource = 'conduits' | 'architecture' | 'readiness' | 'ai';

export const SOURCE_LABELS: Record<HealthSource, string> = {
  conduits: 'Conduits',
  architecture: 'Architecture',
  readiness: 'Readiness',
  ai: 'AI review',
};

export interface HealthFinding {
  id: string;
  source: HealthSource;
  severity: HealthSeverity;
  title: string;
  detail?: string;
  deviceIds: string[];
  flowIds: string[];
  /** AI findings may carry a one-click remediation */
  remediation?: RemediationAction | null;
}

// ---------------------------------------------------------------------------
// Conduit compliance (pure port of v1 useConduitCompliance rules)
// ---------------------------------------------------------------------------

const PROTOCOL_ALIASES: Record<string, string> = {
  profisafe: 'profinet',
  s7comm_plus: 's7comm',
  cip_safety: 'ethernet_ip',
  modbus: 'modbus_tcp',
  enip: 'ethernet_ip',
  bacnet_ip: 'bacnet',
};

const normalizeProtocol = (p: string): string => PROTOCOL_ALIASES[p] ?? p;

function deviceZoneId(doc: ScenarioDocument, deviceId: string): string | null {
  const device = doc.devices[deviceId];
  if (!device) return null;
  if (device.zoneId) return device.zoneId;
  for (const [zoneId, zone] of Object.entries(doc.zones)) {
    if (zone.deviceIds?.includes(deviceId)) return zoneId;
  }
  return null;
}

export function conduitFindings(doc: ScenarioDocument): HealthFinding[] {
  const findings: HealthFinding[] = [];

  for (const flow of Object.values(doc.flows)) {
    const sourceZone = deviceZoneId(doc, flow.sourceDeviceId);
    const targetZone = deviceZoneId(doc, flow.targetDeviceId);
    if (!sourceZone || !targetZone || sourceZone === targetZone) continue;

    const sourceName = doc.devices[flow.sourceDeviceId]?.name ?? flow.sourceDeviceId;
    const targetName = doc.devices[flow.targetDeviceId]?.name ?? flow.targetDeviceId;
    const zoneAName = doc.zones[sourceZone]?.name ?? sourceZone;
    const zoneBName = doc.zones[targetZone]?.name ?? targetZone;

    const normalized = normalizeProtocol(flow.protocol);
    let match: { conduitId: string; protocolAllowed: boolean; directionAllowed: boolean } | null = null;
    for (const [conduitId, conduit] of Object.entries(doc.conduits)) {
      const forward = conduit.sourceZoneId === sourceZone && conduit.targetZoneId === targetZone;
      const reverse = conduit.sourceZoneId === targetZone && conduit.targetZoneId === sourceZone;
      if (!forward && !reverse) continue;
      const directionAllowed =
        conduit.direction === 'bidirectional' ||
        (conduit.direction === 'a_to_b' && forward) ||
        (conduit.direction === 'b_to_a' && reverse);
      const protocolAllowed =
        conduit.allowedProtocols.map(normalizeProtocol).includes(normalized) ||
        conduit.allowedProtocols.includes(flow.protocol);
      match = { conduitId, protocolAllowed, directionAllowed };
      break;
    }

    const base = {
      source: 'conduits' as const,
      deviceIds: [flow.sourceDeviceId, flow.targetDeviceId],
      flowIds: [flow.id],
    };
    if (!match) {
      findings.push({
        ...base,
        id: `conduit-none-${flow.id}`,
        severity: 'crit',
        title: `No conduit between ${zoneAName} and ${zoneBName}`,
        detail: `${sourceName} → ${targetName} (${flow.protocol}) crosses zones without an IEC 62443 conduit. Draw one with the conduit tool, or move the devices into one zone.`,
      });
    } else if (!match.directionAllowed) {
      findings.push({
        ...base,
        id: `conduit-dir-${flow.id}`,
        severity: 'warn',
        title: `Flow direction not allowed by conduit`,
        detail: `${sourceName} → ${targetName} runs against the conduit's declared direction between ${zoneAName} and ${zoneBName}.`,
      });
    } else if (!match.protocolAllowed) {
      findings.push({
        ...base,
        id: `conduit-proto-${flow.id}`,
        severity: 'crit',
        title: `${flow.protocol} not allowed by conduit`,
        detail: `The conduit between ${zoneAName} and ${zoneBName} does not allow ${flow.protocol}. Add it to the conduit's protocol list or change the flow.`,
      });
    }
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Architecture rationality (results from the shared rationality store)
// ---------------------------------------------------------------------------

export function architectureFindings(
  doc: ScenarioDocument,
  results: Record<string, FlowRationality>,
): HealthFinding[] {
  const findings: HealthFinding[] = [];
  for (const flow of Object.values(doc.flows)) {
    const r = results[flow.id];
    if (!r || r.status === 'ok' || r.status === 'unknown') continue;
    const sourceName = doc.devices[flow.sourceDeviceId]?.name ?? '?';
    const targetName = doc.devices[flow.targetDeviceId]?.name ?? '?';
    findings.push({
      id: `arch-${flow.id}`,
      source: 'architecture',
      severity: 'warn',
      title:
        r.status === 'off-rail'
          ? `Off the architecture rail: ${sourceName} → ${targetName}`
          : `Protocol mismatch on the rail: ${sourceName} → ${targetName}`,
      detail: r.suggestion ?? undefined,
      deviceIds: [flow.sourceDeviceId, flow.targetDeviceId],
      flowIds: [flow.id],
    });
  }
  return findings;
}

// ---------------------------------------------------------------------------
// Readiness (backend validation)
// ---------------------------------------------------------------------------

export function readinessFindings(validation: ScenarioValidationResponse | null): HealthFinding[] {
  if (!validation) return [];
  return validation.warnings.map((w, i) => ({
    id: `readiness-${w.code}-${i}`,
    source: 'readiness' as const,
    severity: w.severity === 'error' ? ('crit' as const) : ('warn' as const),
    title: w.message,
    detail: w.details ?? undefined,
    deviceIds: [],
    flowIds: [],
  }));
}

// ---------------------------------------------------------------------------
// AI review
// ---------------------------------------------------------------------------

const AI_SEVERITY: Record<string, HealthSeverity> = {
  critical: 'crit',
  warning: 'warn',
  suggestion: 'info',
  info: 'info',
};

export function aiFindings(review: ScenarioReviewResponse | null): HealthFinding[] {
  if (!review) return [];
  return review.findings.map((f, i) => ({
    id: `ai-${i}-${f.title}`,
    source: 'ai' as const,
    severity: AI_SEVERITY[f.severity] ?? 'info',
    title: f.title,
    detail: [f.description, f.suggestion].filter(Boolean).join(' — '),
    deviceIds: f.affected_device_ids ?? [],
    flowIds: f.affected_flow_ids ?? [],
    remediation: f.remediation,
  }));
}

// ---------------------------------------------------------------------------
// Aggregation
// ---------------------------------------------------------------------------

const SEVERITY_ORDER: Record<HealthSeverity, number> = { crit: 0, warn: 1, info: 2 };

export function sortFindings(findings: HealthFinding[]): HealthFinding[] {
  return [...findings].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);
}

export function healthScore(findings: HealthFinding[]): number {
  let score = 100;
  for (const f of findings) {
    score -= f.severity === 'crit' ? 12 : f.severity === 'warn' ? 4 : 1;
  }
  return Math.max(0, Math.round(score));
}

/** Worst finding per element, for the Build-mode status dots. */
export function statusMaps(findings: HealthFinding[]): {
  byDevice: Record<string, StatusLevel>;
  byFlow: Record<string, StatusLevel>;
} {
  const byDevice: Record<string, StatusLevel> = {};
  const byFlow: Record<string, StatusLevel> = {};
  const rank: Record<StatusLevel, number> = { crit: 0, warn: 1, ok: 2 };
  const asStatus = (s: HealthSeverity): StatusLevel | null =>
    s === 'crit' ? 'crit' : s === 'warn' ? 'warn' : null;

  for (const f of findings) {
    const status = asStatus(f.severity);
    if (!status) continue;
    for (const id of f.deviceIds) {
      if (!byDevice[id] || rank[status] < rank[byDevice[id]]) byDevice[id] = status;
    }
    for (const id of f.flowIds) {
      if (!byFlow[id] || rank[status] < rank[byFlow[id]]) byFlow[id] = status;
    }
  }
  return { byDevice, byFlow };
}
