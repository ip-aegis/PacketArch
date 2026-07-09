/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 group-by cluster view — transforms the derived nodes/edges
 * into cluster aggregates when a grouping mode is active. Reuses the pure
 * grouping/layout utilities shared with v1 (utils/clusterGrouping).
 *
 * View-only: cluster positions are computed, never persisted, and the
 * canvas suppresses position dispatches while a grouping is active.
 */

import { useMemo } from 'react';
import type { Node, Edge } from '@xyflow/react';
import {
  groupByZone,
  groupByProtocol,
  groupByVendor,
  groupByPurdueLevel,
  groupByDeviceType,
  computeAggregateEdges,
  buildDeviceToClusterMap,
  layoutClusters,
  layoutClustersPurdue,
  layoutClustersZoneByPurdue,
  layoutExpandedDevices,
  type ClusterData,
} from '../../utils/clusterGrouping';
import { PROTOCOL_SHORT_NAMES } from '../../constants/protocols';
import type { ProtocolType } from '../../types';
import type { ScenarioDocument } from '../document/documentStore';
import type { GroupByMode } from '../uiState';
import type { ClusterNode2Data } from './ClusterNode2';
import type { AggregateEdge2Data } from './AggregateEdge2';

function computeClusters(
  mode: Exclude<GroupByMode, 'none'>,
  doc: ScenarioDocument,
): Map<string, ClusterData> {
  switch (mode) {
    case 'zone':
      return groupByZone(doc.devices, doc.zones);
    case 'protocol':
      return groupByProtocol(doc.devices);
    case 'vendor':
      return groupByVendor(doc.devices);
    case 'purdueLevel':
      return groupByPurdueLevel(doc.devices, doc.zones);
    case 'deviceType':
      return groupByDeviceType(doc.devices);
  }
}

export function useClusterView2(
  doc: ScenarioDocument | null,
  rawNodes: Node[],
  rawEdges: Edge[],
  groupBy: GroupByMode,
  expandedClusterIds: Set<string>,
): { nodes: Node[]; edges: Edge[] } {
  return useMemo(() => {
    if (!doc || groupBy === 'none') return { nodes: rawNodes, edges: rawEdges };

    const clusters = computeClusters(groupBy, doc);
    const deviceToCluster = buildDeviceToClusterMap(clusters);
    const clusterArray = Array.from(clusters.values());
    const positions =
      groupBy === 'purdueLevel'
        ? layoutClustersPurdue(clusterArray)
        : groupBy === 'zone'
          ? layoutClustersZoneByPurdue(clusterArray, doc.zones)
          : layoutClusters(clusterArray);

    const nodes: Node[] = [];
    for (const cluster of clusterArray) {
      const pos = positions[cluster.id] ?? { x: 100, y: 100 };

      if (expandedClusterIds.has(cluster.id)) {
        // Expanded in place: a quiet container + the member device nodes
        const devicePositions = layoutExpandedDevices(cluster.deviceIds, pos);
        const cols = Math.max(1, Math.ceil(Math.sqrt(cluster.deviceIds.length)));
        const rows = Math.ceil(cluster.deviceIds.length / cols);
        nodes.push({
          id: `${cluster.id}-container`,
          type: 'group',
          position: { x: pos.x - 20, y: pos.y - 30 },
          style: {
            width: cols * 220 + 40,
            height: rows * 260 + 90,
            background: `${cluster.color}0A`,
            border: `1px dashed ${cluster.color}55`,
            borderRadius: 12,
            zIndex: -1,
          },
          data: { label: cluster.label },
          draggable: false,
          selectable: false,
        });
        for (const deviceId of cluster.deviceIds) {
          const deviceNode = rawNodes.find((n) => n.id === deviceId);
          if (!deviceNode) continue;
          // Strip zone parenting — expanded positions are absolute
          const { parentId: _parentId, ...rest } = deviceNode;
          nodes.push({ ...rest, position: devicePositions[deviceId] ?? pos });
        }
      } else {
        const data: ClusterNode2Data = {
          clusterId: cluster.id,
          label: cluster.label,
          color: cluster.color,
          deviceCount: cluster.stats.deviceCount,
          deviceTypes: cluster.stats.deviceTypes,
          protocols: Object.keys(cluster.stats.protocols).map(
            (p) => PROTOCOL_SHORT_NAMES[p as ProtocolType] ?? p,
          ),
        };
        nodes.push({
          id: cluster.id,
          type: 'cluster2',
          position: pos,
          data,
          draggable: true,
          selectable: true,
        });
      }
    }

    const edges: Edge[] = [];
    const aggEdges = computeAggregateEdges(doc.flows, deviceToCluster, expandedClusterIds);
    for (const agg of aggEdges) {
      const sourceExists = nodes.some((n) => n.id === agg.sourceClusterId);
      const targetExists = nodes.some((n) => n.id === agg.targetClusterId);
      if (!sourceExists || !targetExists) continue;
      const data: AggregateEdge2Data = {
        flowCount: agg.flowCount,
        protocolLabel: agg.protocols
          .map((p) => PROTOCOL_SHORT_NAMES[p as ProtocolType] ?? p)
          .join(', '),
      };
      edges.push({
        id: agg.id,
        source: agg.sourceClusterId,
        target: agg.targetClusterId,
        type: 'aggregate2',
        data,
      });
    }

    // Device-level flow edges survive when both endpoints are visible
    for (const edge of rawEdges) {
      const srcCluster = deviceToCluster.get(edge.source);
      const tgtCluster = deviceToCluster.get(edge.target);
      if (!srcCluster || !tgtCluster) continue;
      if (expandedClusterIds.has(srcCluster) && expandedClusterIds.has(tgtCluster)) {
        edges.push(edge);
      }
    }

    return { nodes, edges };
  }, [doc, rawNodes, rawEdges, groupBy, expandedClusterIds]);
}
