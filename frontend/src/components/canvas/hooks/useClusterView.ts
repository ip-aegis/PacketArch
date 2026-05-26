/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Hook that transforms raw canvas nodes/edges into clustered views.
 *
 * Sits between useCanvasSync (raw data) and React Flow rendering.
 * When clusterViewMode !== 'none', replaces individual device nodes
 * with ClusterNode aggregates and merges edges into aggregate edges.
 */

import { useMemo, useState, useCallback, useEffect } from 'react';
import type { Node, Edge } from '@xyflow/react';
import { useShallow } from 'zustand/react/shallow';
import { useUIStore } from '../../../stores/uiStore';
import type { ClusterViewMode } from '../../../stores/uiStore';
import { useScenarioStore } from '../../../stores/scenarioStore';
import type { ClusterNodeData } from '../nodes/ClusterNode';
import type { FlowEdgeData, AggregateEdgeInfo } from '../edges/FlowEdge';
import type { ProtocolType } from '../../../types';
import { PROTOCOL_SHORT_NAMES } from '../../../constants/protocols';

const GROUP_MODE_LABELS: Record<ClusterViewMode, string> = {
  none: 'None',
  zone: 'Zone',
  protocol: 'Protocol',
  vendor: 'Vendor',
  purdueLevel: 'Purdue Level',
  deviceType: 'Device Type',
};
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
} from '../../../utils/clusterGrouping';

// ---------------------------------------------------------------------------
// Compute clusters for the active mode
// ---------------------------------------------------------------------------

function computeClusters(
  mode: ClusterViewMode,
  devices: ReturnType<typeof useScenarioStore.getState>['devices'],
  zones: ReturnType<typeof useScenarioStore.getState>['zones'],
): Map<string, ClusterData> {
  switch (mode) {
    case 'zone':
      return groupByZone(devices, zones);
    case 'protocol':
      return groupByProtocol(devices);
    case 'vendor':
      return groupByVendor(devices);
    case 'purdueLevel':
      return groupByPurdueLevel(devices, zones);
    case 'deviceType':
      return groupByDeviceType(devices);
    default:
      return new Map();
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface ClusterViewResult {
  nodes: Node[];
  edges: Edge[];
  isClusterViewActive: boolean;
  expandedClusterIds: Set<string>;
  toggleCluster: (clusterId: string) => void;
  collapseAll: () => void;
  expandAll: () => void;
}

export function useClusterView(
  rawNodes: Node[],
  rawEdges: Edge[],
): ClusterViewResult {
  const clusterViewMode = useUIStore((s) => s.clusterViewMode);
  const devices = useScenarioStore(useShallow((s) => s.devices));
  const flows = useScenarioStore(useShallow((s) => s.flows));
  const zones = useScenarioStore(useShallow((s) => s.zones));

  const [expandedClusterIds, setExpandedClusterIds] = useState<Set<string>>(new Set());

  // Reset expanded state when mode changes
  useEffect(() => {
    setExpandedClusterIds(new Set());
  }, [clusterViewMode]);

  const toggleCluster = useCallback((clusterId: string) => {
    setExpandedClusterIds((prev) => {
      const next = new Set(prev);
      if (next.has(clusterId)) {
        next.delete(clusterId);
      } else {
        next.add(clusterId);
      }
      return next;
    });
  }, []);

  const collapseAll = useCallback(() => {
    setExpandedClusterIds(new Set());
  }, []);

  const expandAll = useCallback(() => {
    // Will be populated after clusters are computed
    const allClusters = computeClusters(clusterViewMode, devices, zones);
    setExpandedClusterIds(new Set(Array.from(allClusters.values()).map((c) => c.id)));
  }, [clusterViewMode, devices, zones]);

  const result = useMemo(() => {
    if (clusterViewMode === 'none') {
      return { nodes: rawNodes, edges: rawEdges };
    }

    // 1. Compute clusters
    const clusters = computeClusters(clusterViewMode, devices, zones);
    const deviceToCluster = buildDeviceToClusterMap(clusters);

    // 2. Compute cluster positions
    //    - purdueLevel mode: horizontal bands keyed off the level itself.
    //    - zone mode: horizontal bands keyed off each zone's Purdue
    //      level so the canvas reads like a whiteboard Purdue diagram
    //      (L0 at the bottom, L4 at the top).
    //    - everything else: weighted grid.
    const clusterArray = Array.from(clusters.values());
    const clusterPositions =
      clusterViewMode === 'purdueLevel'
        ? layoutClustersPurdue(clusterArray)
        : clusterViewMode === 'zone'
        ? layoutClustersZoneByPurdue(clusterArray, zones)
        : layoutClusters(clusterArray);

    // 3. Build nodes
    const nodes: Node[] = [];

    for (const cluster of clusters.values()) {
      const pos = clusterPositions[cluster.id] || { x: 100, y: 100 };

      if (expandedClusterIds.has(cluster.id)) {
        // Expanded: show member devices positioned in a grid
        const devicePositions = layoutExpandedDevices(cluster.deviceIds, pos);

        // Add a container "zone-like" node for the expanded cluster
        const cols = Math.max(1, Math.ceil(Math.sqrt(cluster.deviceIds.length)));
        const rows = Math.ceil(cluster.deviceIds.length / cols);
        nodes.push({
          id: `${cluster.id}-container`,
          type: 'group',
          position: { x: pos.x - 20, y: pos.y - 30 },
          style: {
            width: cols * 220 + 40,
            height: rows * 260 + 90,
            background: `${cluster.color}08`,
            border: `2px dashed ${cluster.color}40`,
            borderRadius: '14px',
            zIndex: -1,
          },
          data: { label: cluster.label },
          draggable: false,
          selectable: false,
        });

        // Add the actual device nodes at computed positions
        for (const deviceId of cluster.deviceIds) {
          const deviceNode = rawNodes.find((n) => n.id === deviceId);
          if (deviceNode) {
            const dPos = devicePositions[deviceId] || pos;
            nodes.push({
              ...deviceNode,
              position: dPos,
            });
          }
        }
      } else {
        // Collapsed: emit a cluster node
        const clusterNodeData: ClusterNodeData = {
          clusterId: cluster.id,
          label: cluster.label,
          groupKey: cluster.groupKey,
          color: cluster.color,
          deviceCount: cluster.stats.deviceCount,
          deviceTypes: cluster.stats.deviceTypes,
          protocols: Object.keys(cluster.stats.protocols),
          vendors: cluster.stats.vendors,
          isExpanded: false,
        };

        nodes.push({
          id: cluster.id,
          type: 'clusterNode',
          position: pos,
          data: clusterNodeData,
          draggable: true,
          selectable: true,
        });
      }
    }

    // 4. Build edges
    const edges: Edge[] = [];

    // Build a reverse map id → ClusterData for quick aggregate-info lookup
    const clustersById = new Map<string, typeof clusterArray[number]>();
    for (const c of clusterArray) clustersById.set(c.id, c);

    // Aggregate edges between collapsed clusters
    const aggEdges = computeAggregateEdges(flows, deviceToCluster, expandedClusterIds);
    for (const agg of aggEdges) {
      // Check if both clusters exist as nodes (one might be expanded)
      const sourceExists = nodes.some((n) => n.id === agg.sourceClusterId);
      const targetExists = nodes.some((n) => n.id === agg.targetClusterId);
      if (!sourceExists || !targetExists) continue;

      const protocolLabel = agg.protocols
        .map((p) => `${PROTOCOL_SHORT_NAMES[p as ProtocolType] || p}`)
        .join(', ');

      const sourceCluster = clustersById.get(agg.sourceClusterId);
      const targetCluster = clustersById.get(agg.targetClusterId);

      const aggregateInfo: AggregateEdgeInfo = {
        sourceClusterId: agg.sourceClusterId,
        sourceClusterLabel: sourceCluster?.label ?? agg.sourceClusterId,
        sourceClusterColor: sourceCluster?.color ?? '#6a9fd4',
        targetClusterId: agg.targetClusterId,
        targetClusterLabel: targetCluster?.label ?? agg.targetClusterId,
        targetClusterColor: targetCluster?.color ?? '#6a9fd4',
        flowIds: agg.flowIds,
        protocols: agg.protocols,
        groupMode: clusterViewMode,
        groupModeLabel: GROUP_MODE_LABELS[clusterViewMode],
      };

      const edgeData: FlowEdgeData = {
        protocol: (agg.protocols[0] ?? 'modbus_tcp') as ProtocolType,
        name: `${agg.flowCount} flows`,
        flowCount: agg.flowCount,
        protocolList: agg.protocols,
        aggregateInfo,
      };

      edges.push({
        id: agg.id,
        source: agg.sourceClusterId,
        target: agg.targetClusterId,
        type: 'flowEdge',
        data: edgeData,
        label: `${agg.flowCount}x ${protocolLabel}`,
        animated: false,
        markerEnd: { type: 'arrowclosed' as const, width: 14, height: 14 },
      });
    }

    // Keep individual edges for devices in expanded clusters
    for (const edge of rawEdges) {
      const srcCluster = deviceToCluster.get(edge.source);
      const tgtCluster = deviceToCluster.get(edge.target);

      if (!srcCluster || !tgtCluster) continue;

      // Both devices are in expanded clusters → keep the original edge
      if (expandedClusterIds.has(srcCluster) && expandedClusterIds.has(tgtCluster)) {
        edges.push(edge);
      }
    }

    return { nodes, edges };
  }, [clusterViewMode, rawNodes, rawEdges, devices, flows, zones, expandedClusterIds]);

  return {
    ...result,
    isClusterViewActive: clusterViewMode !== 'none',
    expandedClusterIds,
    toggleCluster,
    collapseAll,
    expandAll,
  };
}

export default useClusterView;
