/**
 * Pure grouping functions for spatial clustering views.
 *
 * Each groupBy* function takes scenario data and returns a Map of ClusterData.
 * None of these functions mutate state or use React hooks.
 */

import type { ScenarioDevice, ScenarioFlow, ScenarioZone, ProtocolType } from '../types';
import { PROTOCOL_COLORS, PROTOCOL_SHORT_NAMES } from '../constants/protocols';
import { getDeviceTypeColor, getDeviceTypeLabel } from '../constants/deviceTypeRegistry';
import {
  vendorColor,
  PURDUE_LEVEL_COLORS,
  PURDUE_LEVEL_LABELS,
  ZONE_BORDER_COLORS,
} from '../constants/clusterColors';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ClusterStats {
  deviceCount: number;
  deviceTypes: Record<string, number>;
  protocols: Record<string, number>;
  vendors: string[];
}

export interface ClusterData {
  id: string;
  label: string;
  groupKey: string;
  deviceIds: string[];
  color: string;
  stats: ClusterStats;
}

export interface AggregateEdgeData {
  id: string;
  sourceClusterId: string;
  targetClusterId: string;
  flowCount: number;
  protocols: ProtocolType[];
}

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

function computeStats(
  deviceIds: string[],
  devices: Record<string, ScenarioDevice>,
): ClusterStats {
  const deviceTypes: Record<string, number> = {};
  const protocols: Record<string, number> = {};
  const vendorSet = new Set<string>();

  for (const id of deviceIds) {
    const d = devices[id];
    if (!d) continue;
    deviceTypes[d.type] = (deviceTypes[d.type] || 0) + 1;
    for (const p of d.protocols) {
      protocols[p] = (protocols[p] || 0) + 1;
    }
    if (d.vendor) vendorSet.add(d.vendor);
  }

  return {
    deviceCount: deviceIds.length,
    deviceTypes,
    protocols,
    vendors: Array.from(vendorSet),
  };
}

// ---------------------------------------------------------------------------
// inferPurdueLevel — extracted from useAutoLayout.ts for reuse
// ---------------------------------------------------------------------------

export function inferPurdueLevel(zone: ScenarioZone): number {
  // Use explicit level from backend/template if available
  if (zone.level !== undefined) return zone.level;

  // Fallback: infer from zone name and type (for legacy scenarios)
  const nameLower = zone.name.toLowerCase();

  if (nameLower.includes('enterprise') || nameLower.includes('corporate')) return 4;
  if (nameLower.includes('dmz')) return 3.5;
  if (nameLower.includes('scada') || nameLower.includes('operations')) return 3;
  if (nameLower.includes('process') || nameLower.includes('control')) return 2;
  if (nameLower.includes('field') || nameLower.includes('device') || nameLower.includes('sensor')) return 1;

  switch (zone.type) {
    case 'vertical': return 3;
    case 'network': return 2;
    case 'vlan': return 2;
    case 'logical': return 1;
    default: return 2;
  }
}

// ---------------------------------------------------------------------------
// Group-by functions
// ---------------------------------------------------------------------------

export function groupByZone(
  devices: Record<string, ScenarioDevice>,
  zones: Record<string, ScenarioZone>,
): Map<string, ClusterData> {
  const clusters = new Map<string, ClusterData>();

  for (const [deviceId, device] of Object.entries(devices)) {
    const zoneId = device.zoneId || '__unzoned__';
    let cluster = clusters.get(zoneId);
    if (!cluster) {
      const zone = zones[zoneId];
      cluster = {
        id: `cluster-zone-${zoneId}`,
        label: zone ? zone.name : 'Unassigned',
        groupKey: zoneId,
        deviceIds: [],
        color: zone ? (ZONE_BORDER_COLORS[zone.type] || '#6a9fd4') : '#6a9fd4',
        stats: { deviceCount: 0, deviceTypes: {}, protocols: {}, vendors: [] },
      };
      clusters.set(zoneId, cluster);
    }
    cluster.deviceIds.push(deviceId);
  }

  // Compute stats
  for (const cluster of clusters.values()) {
    cluster.stats = computeStats(cluster.deviceIds, devices);
  }

  return clusters;
}

export function groupByProtocol(
  devices: Record<string, ScenarioDevice>,
): Map<string, ClusterData> {
  const clusters = new Map<string, ClusterData>();

  for (const [deviceId, device] of Object.entries(devices)) {
    const protos = device.protocols.length > 0 ? device.protocols : ['__unconfigured__' as ProtocolType];

    for (const proto of protos) {
      let cluster = clusters.get(proto);
      if (!cluster) {
        const isUnconfigured = proto === '__unconfigured__';
        cluster = {
          id: `cluster-protocol-${proto}`,
          label: isUnconfigured ? 'Unconfigured' : (PROTOCOL_SHORT_NAMES[proto] ? proto.replace('_', ' ').toUpperCase() : proto),
          groupKey: proto,
          deviceIds: [],
          color: isUnconfigured ? '#6a9fd4' : (PROTOCOL_COLORS[proto] || '#6a9fd4'),
          stats: { deviceCount: 0, deviceTypes: {}, protocols: {}, vendors: [] },
        };
        clusters.set(proto, cluster);
      }
      // Avoid adding the same device twice to the same cluster
      if (!cluster.deviceIds.includes(deviceId)) {
        cluster.deviceIds.push(deviceId);
      }
    }
  }

  for (const cluster of clusters.values()) {
    cluster.stats = computeStats(cluster.deviceIds, devices);
  }

  return clusters;
}

export function groupByVendor(
  devices: Record<string, ScenarioDevice>,
): Map<string, ClusterData> {
  const clusters = new Map<string, ClusterData>();
  // Track first-seen vendor casing for labels
  const vendorLabels = new Map<string, string>();

  for (const [deviceId, device] of Object.entries(devices)) {
    const key = device.vendor ? device.vendor.toLowerCase().trim() : '__unknown__';
    if (device.vendor && !vendorLabels.has(key)) {
      vendorLabels.set(key, device.vendor);
    }

    let cluster = clusters.get(key);
    if (!cluster) {
      cluster = {
        id: `cluster-vendor-${key}`,
        label: key === '__unknown__' ? 'Unknown' : (vendorLabels.get(key) || key),
        groupKey: key,
        deviceIds: [],
        color: key === '__unknown__' ? '#6a9fd4' : vendorColor(key),
        stats: { deviceCount: 0, deviceTypes: {}, protocols: {}, vendors: [] },
      };
      clusters.set(key, cluster);
    }
    cluster.deviceIds.push(deviceId);
  }

  for (const cluster of clusters.values()) {
    cluster.stats = computeStats(cluster.deviceIds, devices);
  }

  return clusters;
}

export function groupByPurdueLevel(
  devices: Record<string, ScenarioDevice>,
  zones: Record<string, ScenarioZone>,
): Map<string, ClusterData> {
  const clusters = new Map<string, ClusterData>();

  for (const [deviceId, device] of Object.entries(devices)) {
    let levelKey: string;
    if (device.zoneId && zones[device.zoneId]) {
      levelKey = String(inferPurdueLevel(zones[device.zoneId]));
    } else {
      levelKey = '__unassigned__';
    }

    let cluster = clusters.get(levelKey);
    if (!cluster) {
      const isUnassigned = levelKey === '__unassigned__';
      const level = isUnassigned ? -1 : Number(levelKey);
      cluster = {
        id: `cluster-purdue-${levelKey}`,
        label: isUnassigned ? 'Unassigned' : (PURDUE_LEVEL_LABELS[level] || `Level ${levelKey}`),
        groupKey: levelKey,
        deviceIds: [],
        color: isUnassigned ? '#6a9fd4' : (PURDUE_LEVEL_COLORS[level] || '#6a9fd4'),
        stats: { deviceCount: 0, deviceTypes: {}, protocols: {}, vendors: [] },
      };
      clusters.set(levelKey, cluster);
    }
    cluster.deviceIds.push(deviceId);
  }

  for (const cluster of clusters.values()) {
    cluster.stats = computeStats(cluster.deviceIds, devices);
  }

  return clusters;
}

export function groupByDeviceType(
  devices: Record<string, ScenarioDevice>,
): Map<string, ClusterData> {
  const clusters = new Map<string, ClusterData>();

  for (const [deviceId, device] of Object.entries(devices)) {
    const key = device.type;
    let cluster = clusters.get(key);
    if (!cluster) {
      cluster = {
        id: `cluster-type-${key}`,
        label: getDeviceTypeLabel(key),
        groupKey: key,
        deviceIds: [],
        color: getDeviceTypeColor(key),
        stats: { deviceCount: 0, deviceTypes: {}, protocols: {}, vendors: [] },
      };
      clusters.set(key, cluster);
    }
    cluster.deviceIds.push(deviceId);
  }

  for (const cluster of clusters.values()) {
    cluster.stats = computeStats(cluster.deviceIds, devices);
  }

  return clusters;
}

// ---------------------------------------------------------------------------
// Aggregate edges
// ---------------------------------------------------------------------------

/**
 * Merge individual device-to-device flows into cluster-to-cluster aggregate edges.
 * Flows within the same cluster are skipped.
 * If a cluster is expanded, its devices keep individual edges.
 */
export function computeAggregateEdges(
  flows: Record<string, ScenarioFlow>,
  deviceToCluster: Map<string, string>,
  expandedClusterIds: Set<string>,
): AggregateEdgeData[] {
  // key: "sourceCluster->targetCluster", value: { count, protocols set }
  const edgeMap = new Map<string, { sourceClusterId: string; targetClusterId: string; count: number; protocols: Set<ProtocolType> }>();

  for (const flow of Object.values(flows)) {
    const srcCluster = deviceToCluster.get(flow.sourceDeviceId);
    const tgtCluster = deviceToCluster.get(flow.targetDeviceId);
    if (!srcCluster || !tgtCluster) continue;

    // Skip intra-cluster edges (unless cluster is expanded — those stay as device edges)
    if (srcCluster === tgtCluster) continue;

    // If both sides are expanded, we'll keep individual edges
    if (expandedClusterIds.has(srcCluster) && expandedClusterIds.has(tgtCluster)) continue;

    // Use canonical ordering for the key so A→B and B→A merge
    const [lo, hi] = srcCluster < tgtCluster ? [srcCluster, tgtCluster] : [tgtCluster, srcCluster];
    const key = `${lo}->${hi}`;

    let entry = edgeMap.get(key);
    if (!entry) {
      entry = { sourceClusterId: lo, targetClusterId: hi, count: 0, protocols: new Set() };
      edgeMap.set(key, entry);
    }
    entry.count++;
    entry.protocols.add(flow.protocol);
  }

  return Array.from(edgeMap.values()).map((e) => ({
    id: `agg-edge-${e.sourceClusterId}-${e.targetClusterId}`,
    sourceClusterId: e.sourceClusterId,
    targetClusterId: e.targetClusterId,
    flowCount: e.count,
    protocols: Array.from(e.protocols),
  }));
}

// ---------------------------------------------------------------------------
// Cluster layout
// ---------------------------------------------------------------------------

/**
 * Position clusters in a weighted grid (largest clusters first).
 */
export function layoutClusters(
  clusters: ClusterData[],
): Record<string, { x: number; y: number }> {
  if (clusters.length === 0) return {};

  // Sort largest first for visual hierarchy
  const sorted = [...clusters].sort((a, b) => b.stats.deviceCount - a.stats.deviceCount);
  const cols = Math.max(1, Math.ceil(Math.sqrt(sorted.length)));
  const spacingX = 320;
  const spacingY = 340;
  const startX = 100;
  const startY = 100;

  const positions: Record<string, { x: number; y: number }> = {};
  sorted.forEach((cluster, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    positions[cluster.id] = {
      x: startX + col * spacingX,
      y: startY + row * spacingY,
    };
  });

  return positions;
}

/**
 * Special layout for Purdue level grouping: horizontal bands.
 */
const PURDUE_Y_POSITIONS: Record<number, number> = {
  5: 50,
  4: 350,
  3.5: 650,
  3: 950,
  2: 1250,
  1: 1550,
  0: 1850,
};

export function layoutClustersPurdue(
  clusters: ClusterData[],
): Record<string, { x: number; y: number }> {
  if (clusters.length === 0) return {};

  const positions: Record<string, { x: number; y: number }> = {};
  // Group clusters by their Purdue level
  const byLevel = new Map<number, ClusterData[]>();

  for (const cluster of clusters) {
    const level = cluster.groupKey === '__unassigned__' ? -1 : Number(cluster.groupKey);
    if (!byLevel.has(level)) byLevel.set(level, []);
    byLevel.get(level)!.push(cluster);
  }

  for (const [level, levelClusters] of byLevel) {
    const y = level === -1 ? 2150 : (PURDUE_Y_POSITIONS[level] ?? 1250);
    levelClusters.forEach((cluster, i) => {
      positions[cluster.id] = {
        x: 100 + i * 320,
        y,
      };
    });
  }

  return positions;
}

// ---------------------------------------------------------------------------
// Expand layout — position member devices in a grid around cluster center
// ---------------------------------------------------------------------------

export function layoutExpandedDevices(
  deviceIds: string[],
  clusterPosition: { x: number; y: number },
): Record<string, { x: number; y: number }> {
  const cols = Math.max(1, Math.ceil(Math.sqrt(deviceIds.length)));
  const spacingX = 220;
  const spacingY = 260;
  const positions: Record<string, { x: number; y: number }> = {};

  deviceIds.forEach((id, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    positions[id] = {
      x: clusterPosition.x + col * spacingX,
      y: clusterPosition.y + 60 + row * spacingY,
    };
  });

  return positions;
}

// ---------------------------------------------------------------------------
// Build device → cluster mapping
// ---------------------------------------------------------------------------

export function buildDeviceToClusterMap(
  clusters: Map<string, ClusterData>,
): Map<string, string> {
  const map = new Map<string, string>();
  for (const cluster of clusters.values()) {
    for (const deviceId of cluster.deviceIds) {
      // For protocol grouping a device can be in multiple clusters;
      // use the first one encountered for edge aggregation.
      if (!map.has(deviceId)) {
        map.set(deviceId, cluster.id);
      }
    }
  }
  return map;
}
