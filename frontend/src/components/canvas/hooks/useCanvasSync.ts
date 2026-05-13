/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Hook to sync React Flow nodes/edges with scenarioStore
 * Transforms between store format and React Flow format
 */

import { useMemo } from 'react';
import type { Node, Edge } from '@xyflow/react';
import { useScenarioStore } from '../../../stores/scenarioStore';
import { useUIStore } from '../../../stores/uiStore';
import type { DeviceNodeData } from '../nodes/DeviceNode';
import type { FlowEdgeData } from '../edges/FlowEdge';
import type { ConduitEdgeData } from '../edges/ConduitEdge';
import type { ZoneNodeData } from '../nodes/ZoneNode';
import type { ComplianceStatus } from '../../../types';
import { useShallow } from 'zustand/react/shallow';
import { useConduitCompliance } from './useConduitCompliance';

type Side = 'top' | 'bottom' | 'left' | 'right';
type ZoneBox = { x: number; y: number; w: number; h: number };

/**
 * Pick the conduit edge sides (top/bottom/left/right) that minimize visual
 * length given the relative position of the two zones. Returns sides only —
 * the slot (0/1/2) is assigned later so multiple conduits sharing the same
 * side can fan out across three handle slots.
 */
function pickConduitSides(src: ZoneBox, tgt: ZoneBox): { srcSide: Side; tgtSide: Side } {
  const dx = (tgt.x + tgt.w / 2) - (src.x + src.w / 2);
  const dy = (tgt.y + tgt.h / 2) - (src.y + src.h / 2);
  if (Math.abs(dy) >= Math.abs(dx)) {
    return dy >= 0 ? { srcSide: 'bottom', tgtSide: 'top' } : { srcSide: 'top', tgtSide: 'bottom' };
  }
  return dx >= 0 ? { srcSide: 'right', tgtSide: 'left' } : { srcSide: 'left', tgtSide: 'right' };
}

/**
 * Assign 3-slot handle indices for every conduit so groups of conduits that
 * leave (or enter) the same side of a zone fan out across that side rather
 * than stacking on the centerline.
 *
 * Order within a side is determined by the relative position of the *other*
 * endpoint, so leftmost target gets slot 0, middle gets 1, rightmost gets 2.
 */
function assignConduitHandles(
  conduitList: Array<{ id: string; sourceZoneId: string; targetZoneId: string }>,
  zoneBoxes: Record<string, ZoneBox>,
): Record<string, { sourceHandle: string; targetHandle: string }> {
  // Group conduits by (zoneId, side, role) so we can sort and assign slots.
  type Group = { conduitId: string; otherCenter: number; side: Side; role: 'source' | 'target' };
  const groupBuckets = new Map<string, Group[]>();
  const sideMap: Record<string, { srcSide: Side; tgtSide: Side }> = {};

  for (const c of conduitList) {
    const src = zoneBoxes[c.sourceZoneId];
    const tgt = zoneBoxes[c.targetZoneId];
    if (!src || !tgt) continue;
    const sides = pickConduitSides(src, tgt);
    sideMap[c.id] = sides;

    // Source bucket
    const srcKey = `${c.sourceZoneId}::${sides.srcSide}::source`;
    const srcOther = sides.srcSide === 'top' || sides.srcSide === 'bottom'
      ? tgt.x + tgt.w / 2 : tgt.y + tgt.h / 2;
    if (!groupBuckets.has(srcKey)) groupBuckets.set(srcKey, []);
    groupBuckets.get(srcKey)!.push({ conduitId: c.id, otherCenter: srcOther, side: sides.srcSide, role: 'source' });

    // Target bucket
    const tgtKey = `${c.targetZoneId}::${sides.tgtSide}::target`;
    const tgtOther = sides.tgtSide === 'top' || sides.tgtSide === 'bottom'
      ? src.x + src.w / 2 : src.y + src.h / 2;
    if (!groupBuckets.has(tgtKey)) groupBuckets.set(tgtKey, []);
    groupBuckets.get(tgtKey)!.push({ conduitId: c.id, otherCenter: tgtOther, side: sides.tgtSide, role: 'target' });
  }

  // For each bucket, sort by the other endpoint's center coordinate, then
  // pick a slot from the 3-slot palette (or the legacy center handle if a
  // bucket has only one conduit, to keep things tidy).
  const result: Record<string, { sourceHandle: string; targetHandle: string }> = {};
  const ensure = (id: string) => {
    if (!result[id]) {
      const sides = sideMap[id];
      result[id] = sides
        ? { sourceHandle: `conduit-${sides.srcSide}`, targetHandle: `conduit-target-${sides.tgtSide}` }
        : { sourceHandle: 'conduit-bottom', targetHandle: 'conduit-target-top' };
    }
    return result[id];
  };

  for (const [, group] of groupBuckets) {
    if (group.length === 1) {
      ensure(group[0].conduitId);
      continue;
    }
    // Sort + pick slots evenly spread across [0,1,2].
    const sorted = [...group].sort((a, b) => a.otherCenter - b.otherCenter);
    sorted.forEach((g, idx) => {
      // Spread idx across 3 slots: idx=0 -> 0, last -> 2, middle interpolated.
      const slot = sorted.length === 2
        ? (idx === 0 ? 0 : 2)
        : Math.round((idx / (sorted.length - 1)) * 2);
      const handleId = g.role === 'source'
        ? `conduit-${g.side}-${slot}`
        : `conduit-target-${g.side}-${slot}`;
      const entry = ensure(g.conduitId);
      if (g.role === 'source') entry.sourceHandle = handleId;
      else entry.targetHandle = handleId;
    });
  }
  return result;
}

// Stable marker object to avoid recreation
const ARROW_MARKER = {
  type: 'arrowclosed' as const,
  width: 14,
  height: 14,
};

export const useCanvasSync = () => {
  // Subscribe to devices and zones with shallow comparison
  const devices = useScenarioStore(useShallow((state) => state.devices));
  const zones = useScenarioStore(useShallow((state) => state.zones));
  const flows = useScenarioStore(useShallow((state) => state.flows));
  const conduits = useScenarioStore(useShallow((state) => state.conduits));

  // Edge visibility / aggregation toggles
  const showFlows = useUIStore((s) => s.panels.showFlows);
  const showConduits = useUIStore((s) => s.panels.showConduits);
  const aggregateFlows = useUIStore((s) => s.panels.aggregateFlows);

  // Compliance data
  const { flowCompliance, conduitCompliance } = useConduitCompliance();

  // Convert devices to React Flow nodes
  const nodes = useMemo(() => {
    const deviceNodes: Node<DeviceNodeData>[] = Object.values(devices).map((device, index) => {
      const isConfigured = Boolean(
        device.name &&
        device.network?.ipAddress &&
        device.network?.macAddress &&
        device.protocols?.length > 0
      );

      // Calculate default position if not provided (grid layout)
      const defaultPosition = {
        x: 100 + (index % 4) * 250,
        y: 100 + Math.floor(index / 4) * 220,
      };

      return {
        id: device.id,
        type: 'deviceNode',
        position: device.position || defaultPosition,
        draggable: true,
        data: {
          id: device.id,
          name: device.name,
          type: device.type,
          role: device.role,
          protocols: device.protocols || [],
          isConfigured,
          ipAddress: device.network?.ipAddress,
          cveIds: device.cveIds,
          vendor: device.vendor,
        },
      };
    });

    const zoneNodes: Node<ZoneNodeData>[] = Object.values(zones).map((zone, index) => {
      // Default position for zones if not provided
      const defaultPosition = {
        x: 50 + index * 400,
        y: 50,
      };
      // Default dimensions if not provided
      const defaultDimensions = {
        width: 350,
        height: 300,
      };

      return {
        id: zone.id,
        type: 'zoneNode',
        position: zone.position || defaultPosition,
        draggable: true,
        style: {
          width: zone.dimensions?.width || defaultDimensions.width,
          height: zone.dimensions?.height || defaultDimensions.height,
          zIndex: -1,
        },
        data: {
          id: zone.id,
          name: zone.name,
          type: zone.type,
          level: zone.level,
          network: zone.network || {},
        },
      };
    });

    return [...zoneNodes, ...deviceNodes];
  }, [devices, zones]);

  // Convert flows to React Flow edges, computing parallel-edge indices
  const edges = useMemo(() => {
    const flowList = Object.values(flows);

    // ---- Flow edges --------------------------------------------------------
    let flowEdges: Edge<FlowEdgeData>[] = [];
    if (showFlows) {
      if (aggregateFlows) {
        // Group flows by ordered (sourceZone, targetZone) and emit one edge
        // per zone-pair with an aggregated count + protocol set.
        type Bucket = {
          source: string;
          target: string;
          flowIds: string[];
          protocols: Set<string>;
          first: typeof flowList[number];
        };
        const buckets = new Map<string, Bucket>();
        for (const flow of flowList) {
          const src = devices[flow.sourceDeviceId];
          const tgt = devices[flow.targetDeviceId];
          const sourceZone = src?.zoneId;
          const targetZone = tgt?.zoneId;
          if (!sourceZone || !targetZone) continue;
          const key = `${sourceZone}::${targetZone}`;
          const existing = buckets.get(key);
          if (existing) {
            existing.flowIds.push(flow.id);
            existing.protocols.add(flow.protocol);
          } else {
            buckets.set(key, {
              source: sourceZone,
              target: targetZone,
              flowIds: [flow.id],
              protocols: new Set([flow.protocol]),
              first: flow,
            });
          }
        }
        flowEdges = Array.from(buckets.values()).map((b) => ({
          id: `agg::${b.source}::${b.target}`,
          source: b.source,
          target: b.target,
          type: 'flowEdge',
          data: {
            protocol: b.first.protocol,
            name: `${b.flowIds.length} flow${b.flowIds.length > 1 ? 's' : ''}`,
            parallelIndex: 0,
            parallelCount: 1,
            flowCount: b.flowIds.length,
            protocolList: Array.from(b.protocols),
            complianceReason: undefined,
          },
          animated: false,
          markerEnd: ARROW_MARKER,
        }));
      } else {
        // Group flows by canonical node-pair key so parallel edges can be offset
        const pairCounts = new Map<string, number>();
        const pairIndices = new Map<string, number>();
        for (const flow of flowList) {
          const key = [flow.sourceDeviceId, flow.targetDeviceId].sort().join('::');
          pairCounts.set(key, (pairCounts.get(key) ?? 0) + 1);
        }

        flowEdges = flowList.map((flow) => {
          const key = [flow.sourceDeviceId, flow.targetDeviceId].sort().join('::');
          const parallelCount = pairCounts.get(key) ?? 1;
          const parallelIndex = pairIndices.get(key) ?? 0;
          pairIndices.set(key, parallelIndex + 1);

          // Attach compliance reason if available
          const compliance = flowCompliance[flow.id];
          const complianceReason = compliance?.reason;

          return {
            id: flow.id,
            source: flow.sourceDeviceId,
            target: flow.targetDeviceId,
            type: 'flowEdge',
            data: {
              protocol: flow.protocol,
              name: flow.name,
              parallelIndex,
              parallelCount,
              complianceReason,
            },
            animated: false,
            markerEnd: ARROW_MARKER,
          };
        });
      }
    }

    // ---- Conduit edges -----------------------------------------------------
    let conduitEdges: Edge<ConduitEdgeData>[] = [];
    if (showConduits) {
      // Pre-compute zone bounding boxes once for the slot assignment pass.
      const zoneBoxes: Record<string, { x: number; y: number; w: number; h: number }> = {};
      for (const z of Object.values(zones)) {
        zoneBoxes[z.id] = {
          x: z.position?.x ?? 0,
          y: z.position?.y ?? 0,
          w: z.dimensions?.width ?? 350,
          h: z.dimensions?.height ?? 300,
        };
      }
      const handleAssignments = assignConduitHandles(
        Object.values(conduits).map((c) => ({
          id: c.id,
          sourceZoneId: c.sourceZoneId,
          targetZoneId: c.targetZoneId,
        })),
        zoneBoxes,
      );

      conduitEdges = Object.values(conduits).map((conduit) => {
        const handles = handleAssignments[conduit.id]
          ?? { sourceHandle: 'conduit-bottom', targetHandle: 'conduit-target-top' };
        return {
          id: conduit.id,
          source: conduit.sourceZoneId,
          target: conduit.targetZoneId,
          type: 'conduitEdge',
          sourceHandle: handles.sourceHandle,
          targetHandle: handles.targetHandle,
          data: {
            conduitId: conduit.id,
            name: conduit.name,
            direction: conduit.direction,
            allowedProtocols: conduit.allowedProtocols,
            complianceStatus: (conduitCompliance[conduit.id] || 'unchecked') as ComplianceStatus,
            color: undefined,
          },
          animated: false,
          zIndex: 5,
        };
      });
    }

    return [...flowEdges, ...conduitEdges];
  }, [
    flows, conduits, devices, zones,
    flowCompliance, conduitCompliance,
    showFlows, showConduits, aggregateFlows,
  ]);

  return { nodes, edges };
};

export default useCanvasSync;
