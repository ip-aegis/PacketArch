/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Reactive hook that computes conduit compliance for every flow.
 * Determines if cross-zone flows are covered by conduits and if
 * the flow's protocol is in the conduit's allowed list.
 */

import { useMemo } from 'react';
import { useScenarioStore } from '../../../stores/scenarioStore';
import { useShallow } from 'zustand/react/shallow';
import type { ComplianceStatus, ScenarioConduit } from '../../../types';

/** Protocol aliases: variant names → canonical parent protocol */
const PROTOCOL_ALIASES: Record<string, string> = {
  profisafe: 'profinet',
  s7comm_plus: 's7comm',
  cip_safety: 'ethernet_ip',
  modbus: 'modbus_tcp',
  enip: 'ethernet_ip',
  bacnet_ip: 'bacnet',
};

function normalizeProtocol(protocol: string): string {
  return PROTOCOL_ALIASES[protocol] ?? protocol;
}

export interface FlowComplianceInfo {
  conduitId?: string;
  isCompliant: boolean;
  reason: 'same_zone' | 'compliant' | 'no_conduit' | 'protocol_not_allowed' | 'wrong_direction' | 'no_zone_info';
}

/**
 * Find a device's zone by checking which zone contains it.
 * Checks device.zoneId first, then zone.deviceIds membership.
 */
function getDeviceZoneId(
  deviceId: string,
  devices: Record<string, { zoneId?: string }>,
  zones: Record<string, { deviceIds?: string[] }>,
): string | null {
  const device = devices[deviceId];
  if (!device) return null;

  // Direct zoneId on device
  if (device.zoneId) return device.zoneId;

  // Check zone membership via deviceIds array
  for (const [zoneId, zone] of Object.entries(zones)) {
    if (zone.deviceIds?.includes(deviceId)) return zoneId;
  }

  return null;
}

/**
 * Check if a conduit covers a given zone pair + protocol.
 */
function findMatchingConduit(
  sourceZoneId: string,
  targetZoneId: string,
  protocol: string,
  conduits: Record<string, ScenarioConduit>,
): { conduitId: string; protocolAllowed: boolean; directionAllowed: boolean } | null {
  const normalizedProtocol = normalizeProtocol(protocol);

  for (const [conduitId, conduit] of Object.entries(conduits)) {
    // Check zone pair match (either direction)
    const forwardMatch = conduit.sourceZoneId === sourceZoneId && conduit.targetZoneId === targetZoneId;
    const reverseMatch = conduit.sourceZoneId === targetZoneId && conduit.targetZoneId === sourceZoneId;

    if (!forwardMatch && !reverseMatch) continue;

    // Check direction
    let directionAllowed = conduit.direction === 'bidirectional';
    if (!directionAllowed) {
      if (conduit.direction === 'a_to_b' && forwardMatch) directionAllowed = true;
      if (conduit.direction === 'b_to_a' && reverseMatch) directionAllowed = true;
    }

    // Check protocol (normalize both sides)
    const normalizedAllowed = conduit.allowedProtocols.map(normalizeProtocol);
    const protocolAllowed = normalizedAllowed.includes(normalizedProtocol) ||
                            conduit.allowedProtocols.includes(protocol);

    return { conduitId, protocolAllowed, directionAllowed };
  }

  return null;
}

export function useConduitCompliance() {
  const devices = useScenarioStore(useShallow((state) => state.devices));
  const flows = useScenarioStore(useShallow((state) => state.flows));
  const zones = useScenarioStore(useShallow((state) => state.zones));
  const conduits = useScenarioStore(useShallow((state) => state.conduits));

  const flowCompliance = useMemo(() => {
    const result: Record<string, FlowComplianceInfo> = {};

    for (const [flowId, flow] of Object.entries(flows)) {
      const sourceZone = getDeviceZoneId(flow.sourceDeviceId, devices, zones);
      const targetZone = getDeviceZoneId(flow.targetDeviceId, devices, zones);

      // No zone info — can't determine compliance
      if (!sourceZone || !targetZone) {
        result[flowId] = { isCompliant: true, reason: 'no_zone_info' };
        continue;
      }

      // Same zone — always compliant
      if (sourceZone === targetZone) {
        result[flowId] = { isCompliant: true, reason: 'same_zone' };
        continue;
      }

      // Cross-zone — check conduits
      const match = findMatchingConduit(sourceZone, targetZone, flow.protocol, conduits);

      if (!match) {
        result[flowId] = { isCompliant: false, reason: 'no_conduit' };
        continue;
      }

      if (!match.directionAllowed) {
        result[flowId] = { conduitId: match.conduitId, isCompliant: false, reason: 'wrong_direction' };
        continue;
      }

      if (!match.protocolAllowed) {
        result[flowId] = { conduitId: match.conduitId, isCompliant: false, reason: 'protocol_not_allowed' };
        continue;
      }

      result[flowId] = { conduitId: match.conduitId, isCompliant: true, reason: 'compliant' };
    }

    return result;
  }, [flows, devices, zones, conduits]);

  // Aggregate conduit compliance status
  const conduitCompliance = useMemo(() => {
    const result: Record<string, ComplianceStatus> = {};

    // Only compute if there are conduits
    if (Object.keys(conduits).length === 0) return result;

    // Initialize all conduits as unchecked
    for (const conduitId of Object.keys(conduits)) {
      result[conduitId] = 'unchecked';
    }

    // Track per-conduit: has compliant flows? has non-compliant flows?
    const conduitHasCompliant: Record<string, boolean> = {};
    const conduitHasNonCompliant: Record<string, boolean> = {};

    for (const info of Object.values(flowCompliance)) {
      if (!info.conduitId) continue;
      if (info.isCompliant) {
        conduitHasCompliant[info.conduitId] = true;
      } else {
        conduitHasNonCompliant[info.conduitId] = true;
      }
    }

    for (const conduitId of Object.keys(conduits)) {
      const hasCompliant = conduitHasCompliant[conduitId] ?? false;
      const hasNonCompliant = conduitHasNonCompliant[conduitId] ?? false;

      if (hasNonCompliant && hasCompliant) {
        result[conduitId] = 'partial';
      } else if (hasNonCompliant) {
        result[conduitId] = 'non_compliant';
      } else if (hasCompliant) {
        result[conduitId] = 'compliant';
      }
      // else stays 'unchecked'
    }

    return result;
  }, [conduits, flowCompliance]);

  return { flowCompliance, conduitCompliance };
}

export default useConduitCompliance;
