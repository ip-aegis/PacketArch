/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Hook for auto-layout functionality in the scenario canvas
 * Provides multiple layout algorithms and integrates with history for undo/redo
 */

import { useCallback } from 'react';
import { useScenarioStore } from '../../../stores/scenarioStore';
import { useHistoryStore } from '../../../stores/historyStore';
import { useShallow } from 'zustand/react/shallow';
import type { ScenarioDevice, ScenarioFlow, ScenarioZone } from '../../../types';
import { inferPurdueLevel } from '../../../utils/clusterGrouping';

export type LayoutType = 'manual' | 'purdue' | 'dataflow' | 'grid' | 'circular';

export interface LayoutResult {
  devicePositions: Record<string, { x: number; y: number }>;
  zonePositions: Record<string, { x: number; y: number; width: number; height: number }>;
}

// Layout configuration constants
const LAYOUT_CONFIG = {
  deviceSpacing: 200,
  zoneSpacing: 80,
  zonePadding: 80,
  minZoneWidth: 350,
  minZoneHeight: 280,
  gridStartX: 100,
  gridStartY: 100,
};

// Purdue model level positions (Y-axis) - 300px spacing between levels
const PURDUE_LEVELS: Record<number, number> = {
  5: 50,      // Enterprise Network
  4: 350,     // Site Business
  3.5: 650,   // Industrial DMZ
  3: 950,     // Site Operations
  2: 1250,    // Area Supervisory Control
  1: 1550,    // Basic Control
  0: 1850,    // Process (Field Devices)
};

// Group devices by zone
function groupDevicesByZone(
  devices: Record<string, ScenarioDevice>,
  zones: Record<string, ScenarioZone>
): { zoned: Record<string, ScenarioDevice[]>; unzoned: ScenarioDevice[] } {
  const zoned: Record<string, ScenarioDevice[]> = {};
  const unzoned: ScenarioDevice[] = [];

  // Initialize zone groups
  Object.keys(zones).forEach(zoneId => {
    zoned[zoneId] = [];
  });

  // Sort devices into zones
  Object.values(devices).forEach(device => {
    if (device.zoneId && zones[device.zoneId]) {
      zoned[device.zoneId].push(device);
    } else {
      unzoned.push(device);
    }
  });

  return { zoned, unzoned };
}

// Calculate grid layout - zone-aware version (uses the same wrapping-grid
// packer as the Purdue layout so cells stack vertically with the right size).
function calculateGridLayout(
  devices: Record<string, ScenarioDevice>,
  zones: Record<string, ScenarioZone>
): LayoutResult {
  const deviceCount = Object.keys(devices).length;
  if (deviceCount === 0) {
    return { devicePositions: {}, zonePositions: {} };
  }

  const { zoned, unzoned } = groupDevicesByZone(devices, zones);
  const devicePositions: Record<string, { x: number; y: number }> = {};
  const zonePositions: Record<string, { x: number; y: number; width: number; height: number }> = {};

  let currentY = LAYOUT_CONFIG.gridStartY;
  const zoneList = Object.values(zones);

  for (const zone of zoneList) {
    const zoneDevices = zoned[zone.id] || [];
    const size = packZoneDevices(zoneDevices.length);

    zonePositions[zone.id] = {
      x: LAYOUT_CONFIG.gridStartX,
      y: currentY,
      width: size.w,
      height: size.h,
    };

    zoneDevices.forEach((device, idx) => {
      const col = idx % Math.max(1, size.cols);
      const row = Math.floor(idx / Math.max(1, size.cols));
      devicePositions[device.id] = {
        x: LAYOUT_CONFIG.gridStartX + LAYOUT_CONFIG.zonePadding + col * DEVICE_CELL_W,
        y: currentY + ZONE_HEADER_H + row * DEVICE_CELL_H,
      };
    });

    currentY += size.h + LAYOUT_CONFIG.zoneSpacing;
  }

  if (unzoned.length > 0) {
    const cols = Math.ceil(Math.sqrt(unzoned.length));
    unzoned.forEach((device, index) => {
      const col = index % cols;
      const row = Math.floor(index / cols);
      devicePositions[device.id] = {
        x: LAYOUT_CONFIG.gridStartX + col * DEVICE_CELL_W,
        y: currentY + row * DEVICE_CELL_H,
      };
    });
  }

  return { devicePositions, zonePositions };
}

// Calculate circular layout - concentric rings per zone
// Radius scales based on device count to prevent overlap
function calculateCircularLayout(
  devices: Record<string, ScenarioDevice>,
  zones: Record<string, ScenarioZone>
): LayoutResult {
  const deviceList = Object.values(devices);
  const deviceCount = deviceList.length;

  if (deviceCount === 0) {
    return { devicePositions: {}, zonePositions: {} };
  }

  const { zoned, unzoned } = groupDevicesByZone(devices, zones);
  const devicePositions: Record<string, { x: number; y: number }> = {};
  const zonePositions: Record<string, { x: number; y: number; width: number; height: number }> = {};

  const minDeviceArcSpacing = LAYOUT_CONFIG.deviceSpacing; // Min arc distance between devices
  const minRingSpacing = 250; // Min distance between rings
  const zoneList = Object.values(zones);

  // Helper: calculate minimum radius for N devices to not overlap
  // Circumference = 2πr, arc per device = 2πr/N >= minSpacing
  // So r >= N * minSpacing / (2π)
  const calcMinRadius = (numDevices: number): number => {
    if (numDevices <= 1) return 150;
    return Math.max(150, (numDevices * minDeviceArcSpacing) / (2 * Math.PI));
  };

  // Calculate radii for all rings first to position center correctly
  let currentRadius = 0;

  // Unzoned devices go in center
  if (unzoned.length > 0) {
    currentRadius = calcMinRadius(unzoned.length);
  }

  // Calculate all zone radii
  const zoneRadii: Record<string, number> = {};
  zoneList.forEach(zone => {
    const zoneDevices = zoned[zone.id] || [];
    const neededRadius = calcMinRadius(zoneDevices.length);
    currentRadius = Math.max(currentRadius + minRingSpacing, neededRadius);
    zoneRadii[zone.id] = currentRadius;
  });

  // Calculate center based on total size
  const totalRadius = currentRadius + 100;
  const centerX = totalRadius + 100;
  const centerY = totalRadius + 100;

  // Position unzoned devices in the center
  if (unzoned.length > 0) {
    const unzonedRadius = calcMinRadius(unzoned.length);
    unzoned.forEach((device, index) => {
      const angle = (2 * Math.PI * index) / unzoned.length - Math.PI / 2;
      devicePositions[device.id] = {
        x: centerX + unzonedRadius * Math.cos(angle),
        y: centerY + unzonedRadius * Math.sin(angle),
      };
    });
  }

  // Position each zone as a concentric ring
  zoneList.forEach(zone => {
    const zoneDevices = zoned[zone.id] || [];
    const radius = zoneRadii[zone.id];

    if (zoneDevices.length === 0) {
      // Empty zone - create a small zone marker
      zonePositions[zone.id] = {
        x: centerX - 50,
        y: centerY - radius - 30,
        width: 100,
        height: 40,
      };
      return;
    }

    // Position devices evenly around this ring
    zoneDevices.forEach((device, deviceIndex) => {
      const angle = (2 * Math.PI * deviceIndex) / zoneDevices.length - Math.PI / 2;
      devicePositions[device.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      };
    });

    // Position zone label at top of its ring
    const zoneWidth = Math.max(LAYOUT_CONFIG.minZoneWidth, zoneDevices.length * 40);
    zonePositions[zone.id] = {
      x: centerX - zoneWidth / 2,
      y: centerY - radius - 80,
      width: zoneWidth,
      height: 60,
    };
  });

  return { devicePositions, zonePositions };
}

/**
 * Wrapping grid for the slim device cards (~140w × 56h).
 * Picks columns to target a roughly 1.6 wide aspect ratio so a 7-device cell
 * lays out 3×3 (one slot empty) instead of 7×1.
 */
const DEVICE_CELL_W = 200;
const DEVICE_CELL_H = 90;
const ZONE_HEADER_H = 50;

function packZoneDevices(deviceCount: number): { cols: number; rows: number; w: number; h: number } {
  if (deviceCount === 0) {
    return {
      cols: 0,
      rows: 0,
      w: LAYOUT_CONFIG.minZoneWidth,
      h: LAYOUT_CONFIG.minZoneHeight,
    };
  }
  // Solve cols so that (cols * cellW) / (rows * cellH + header) ≈ 1.6.
  // rows = ceil(n / cols). Just pick the cols that's closest.
  let bestCols = 1;
  let bestScore = Infinity;
  for (let c = 1; c <= deviceCount; c++) {
    const r = Math.ceil(deviceCount / c);
    const w = c * DEVICE_CELL_W;
    const h = r * DEVICE_CELL_H + ZONE_HEADER_H;
    const aspect = w / h;
    const score = Math.abs(Math.log(aspect / 1.6));
    if (score < bestScore) {
      bestScore = score;
      bestCols = c;
    }
  }
  const cols = bestCols;
  const rows = Math.ceil(deviceCount / cols);
  const w = Math.max(LAYOUT_CONFIG.minZoneWidth, cols * DEVICE_CELL_W + LAYOUT_CONFIG.zonePadding * 2);
  const h = Math.max(
    LAYOUT_CONFIG.minZoneHeight,
    rows * DEVICE_CELL_H + ZONE_HEADER_H + LAYOUT_CONFIG.zonePadding,
  );
  return { cols, rows, w, h };
}

// Calculate Purdue Model layout
function calculatePurdueLayout(
  devices: Record<string, ScenarioDevice>,
  zones: Record<string, ScenarioZone>
): LayoutResult {
  const { zoned, unzoned } = groupDevicesByZone(devices, zones);
  const devicePositions: Record<string, { x: number; y: number }> = {};
  const zonePositions: Record<string, { x: number; y: number; width: number; height: number }> = {};

  // Group zones by Purdue level
  const zonesByLevel: Record<number, ScenarioZone[]> = {};
  Object.values(zones).forEach(zone => {
    const level = inferPurdueLevel(zone);
    if (!zonesByLevel[level]) {
      zonesByLevel[level] = [];
    }
    zonesByLevel[level].push(zone);
  });

  // Sort levels descending (enterprise at top)
  const sortedLevels = Object.keys(zonesByLevel)
    .map(Number)
    .sort((a, b) => b - a);

  // First pass: compute sizes for every zone so we can position rows on the
  // tallest zone in each level (otherwise zones overlap when the level row
  // is shorter than its packed zones).
  const zoneSize: Record<string, ReturnType<typeof packZoneDevices>> = {};
  for (const level of sortedLevels) {
    for (const zone of zonesByLevel[level]) {
      zoneSize[zone.id] = packZoneDevices((zoned[zone.id] || []).length);
    }
  }

  // Second pass: walk levels top-down, placing zones left-to-right on the
  // band corresponding to their Purdue level, advancing Y by the row height.
  let cursorY = LAYOUT_CONFIG.gridStartY;
  for (const level of sortedLevels) {
    const levelZones = zonesByLevel[level];
    let cursorX = LAYOUT_CONFIG.gridStartX;
    let rowHeight = 0;

    for (const zone of levelZones) {
      const size = zoneSize[zone.id];
      const zoneDevices = zoned[zone.id] || [];

      zonePositions[zone.id] = {
        x: cursorX,
        y: cursorY,
        width: size.w,
        height: size.h,
      };

      // Pack devices into a wrapping grid inside the zone.
      zoneDevices.forEach((device, idx) => {
        const col = idx % Math.max(1, size.cols);
        const row = Math.floor(idx / Math.max(1, size.cols));
        devicePositions[device.id] = {
          x: cursorX + LAYOUT_CONFIG.zonePadding + col * DEVICE_CELL_W,
          y: cursorY + ZONE_HEADER_H + row * DEVICE_CELL_H,
        };
      });

      cursorX += size.w + LAYOUT_CONFIG.zoneSpacing;
      rowHeight = Math.max(rowHeight, size.h);
    }

    // Advance Y by the tallest zone in this row + a generous inter-level
    // gutter (3× the standard zone spacing). The extra room lets the
    // orthogonal smooth-step conduit bends land in empty space rather than
    // inside a neighbouring zone's body — and gives the halo enough
    // background to read as a "passing over" cue.
    cursorY += rowHeight + LAYOUT_CONFIG.zoneSpacing * 3;
  }

  // Position unzoned devices at the bottom
  const unzonedY = cursorY + 50;
  unzoned.forEach((device, index) => {
    devicePositions[device.id] = {
      x: LAYOUT_CONFIG.gridStartX + index * DEVICE_CELL_W,
      y: unzonedY,
    };
  });

  return { devicePositions, zonePositions };
}

// Calculate Data Flow (hierarchical) layout - zone-aware version
function calculateDataFlowLayout(
  devices: Record<string, ScenarioDevice>,
  zones: Record<string, ScenarioZone>,
  flows: Record<string, ScenarioFlow>
): LayoutResult {
  const deviceList = Object.values(devices);
  const deviceCount = deviceList.length;

  if (deviceCount === 0) {
    return { devicePositions: {}, zonePositions: {} };
  }

  const { zoned, unzoned } = groupDevicesByZone(devices, zones);
  const devicePositions: Record<string, { x: number; y: number }> = {};
  const zonePositions: Record<string, { x: number; y: number; width: number; height: number }> = {};

  // Build adjacency lists
  const outgoing: Record<string, string[]> = {};
  const incoming: Record<string, string[]> = {};

  deviceList.forEach(device => {
    outgoing[device.id] = [];
    incoming[device.id] = [];
  });

  Object.values(flows).forEach(flow => {
    if (outgoing[flow.sourceDeviceId] && incoming[flow.targetDeviceId]) {
      outgoing[flow.sourceDeviceId].push(flow.targetDeviceId);
      incoming[flow.targetDeviceId].push(flow.sourceDeviceId);
    }
  });

  // Find root devices (no incoming flows)
  const roots = deviceList.filter(d => incoming[d.id].length === 0);
  const startNodes = roots.length > 0 ? roots : deviceList;

  // BFS to assign flow levels to each device
  const deviceLevels: Record<string, number> = {};
  const queue: { id: string; level: number }[] = startNodes.map(d => ({ id: d.id, level: 0 }));
  const visited = new Set<string>();

  while (queue.length > 0) {
    const { id, level } = queue.shift()!;
    if (visited.has(id)) continue;
    visited.add(id);
    deviceLevels[id] = level;

    for (const targetId of outgoing[id] || []) {
      if (!visited.has(targetId)) {
        queue.push({ id: targetId, level: level + 1 });
      }
    }
  }

  // Handle disconnected devices
  deviceList.forEach(device => {
    if (!visited.has(device.id)) {
      deviceLevels[device.id] = 0;
    }
  });

  // Calculate zone's dominant flow level (minimum level of its devices)
  const zoneLevels: Record<string, number> = {};
  const zoneList = Object.values(zones);

  zoneList.forEach(zone => {
    const zoneDevices = zoned[zone.id] || [];
    if (zoneDevices.length === 0) {
      zoneLevels[zone.id] = 0;
    } else {
      const levels = zoneDevices.map(d => deviceLevels[d.id] ?? 0);
      zoneLevels[zone.id] = Math.min(...levels);
    }
  });

  // Sort zones by their flow level
  const sortedZones = [...zoneList].sort((a, b) => zoneLevels[a.id] - zoneLevels[b.id]);

  // Position zones left-to-right by flow level
  const horizontalSpacing = 350;
  const verticalSpacing = 200;
  let currentX = LAYOUT_CONFIG.gridStartX;

  sortedZones.forEach(zone => {
    const zoneDevices = zoned[zone.id] || [];
    const deviceCount = zoneDevices.length;

    // Calculate zone dimensions
    const zoneHeight = Math.max(
      LAYOUT_CONFIG.minZoneHeight,
      deviceCount * verticalSpacing + LAYOUT_CONFIG.zonePadding
    );
    const zoneWidth = LAYOUT_CONFIG.minZoneWidth;

    zonePositions[zone.id] = {
      x: currentX,
      y: LAYOUT_CONFIG.gridStartY,
      width: zoneWidth,
      height: zoneHeight,
    };

    // Position devices vertically within zone
    zoneDevices.forEach((device, index) => {
      devicePositions[device.id] = {
        x: currentX + LAYOUT_CONFIG.zonePadding,
        y: LAYOUT_CONFIG.gridStartY + 60 + index * verticalSpacing,
      };
    });

    currentX += zoneWidth + LAYOUT_CONFIG.zoneSpacing;
  });

  // Position unzoned devices to the right of all zones
  if (unzoned.length > 0) {
    unzoned.forEach((device, index) => {
      devicePositions[device.id] = {
        x: currentX,
        y: LAYOUT_CONFIG.gridStartY + index * verticalSpacing,
      };
    });
  }

  return { devicePositions, zonePositions };
}

export const useAutoLayout = () => {
  const devices = useScenarioStore(useShallow(state => state.devices));
  const zones = useScenarioStore(useShallow(state => state.zones));
  const flows = useScenarioStore(useShallow(state => state.flows));
  const bulkMoveDevices = useScenarioStore(state => state.bulkMoveDevices);
  const bulkUpdateZones = useScenarioStore(state => state.bulkUpdateZones);
  const pushHistory = useHistoryStore(state => state.push);

  const calculateLayout = useCallback((layoutType: LayoutType): LayoutResult => {
    switch (layoutType) {
      case 'grid':
        return calculateGridLayout(devices, zones);
      case 'circular':
        return calculateCircularLayout(devices, zones);
      case 'purdue':
        return calculatePurdueLayout(devices, zones);
      case 'dataflow':
        return calculateDataFlowLayout(devices, zones, flows);
      case 'manual':
      default:
        return { devicePositions: {}, zonePositions: {} };
    }
  }, [devices, zones, flows]);

  const applyLayout = useCallback((layoutType: LayoutType) => {
    if (layoutType === 'manual') return;

    // Capture current state for undo
    const previousDevicePositions: Record<string, { x: number; y: number }> = {};
    const previousZonePositions: Record<string, { x: number; y: number; width: number; height: number }> = {};

    Object.entries(devices).forEach(([id, device]) => {
      // Handle devices without position (use default)
      const pos = device.position || { x: 100, y: 100 };
      previousDevicePositions[id] = { x: pos.x, y: pos.y };
    });

    Object.entries(zones).forEach(([id, zone]) => {
      const pos = zone.position || { x: 50, y: 50 };
      const dims = zone.dimensions || { width: 350, height: 300 };
      previousZonePositions[id] = {
        x: pos.x,
        y: pos.y,
        width: dims.width,
        height: dims.height,
      };
    });

    // Calculate new layout
    const newLayout = calculateLayout(layoutType);

    // Apply new positions
    if (Object.keys(newLayout.devicePositions).length > 0) {
      bulkMoveDevices(newLayout.devicePositions);
    }

    if (Object.keys(newLayout.zonePositions).length > 0) {
      const zoneUpdates: Record<string, { position: { x: number; y: number }; dimensions: { width: number; height: number } }> = {};
      Object.entries(newLayout.zonePositions).forEach(([id, pos]) => {
        zoneUpdates[id] = {
          position: { x: pos.x, y: pos.y },
          dimensions: { width: pos.width, height: pos.height },
        };
      });
      bulkUpdateZones(zoneUpdates);
    }

    // Push to history for undo/redo
    pushHistory({
      type: 'APPLY_LAYOUT',
      timestamp: Date.now(),
      undo: () => {
        bulkMoveDevices(previousDevicePositions);
        const prevZoneUpdates: Record<string, { position: { x: number; y: number }; dimensions: { width: number; height: number } }> = {};
        Object.entries(previousZonePositions).forEach(([id, pos]) => {
          prevZoneUpdates[id] = {
            position: { x: pos.x, y: pos.y },
            dimensions: { width: pos.width, height: pos.height },
          };
        });
        bulkUpdateZones(prevZoneUpdates);
      },
      redo: () => {
        if (Object.keys(newLayout.devicePositions).length > 0) {
          bulkMoveDevices(newLayout.devicePositions);
        }
        if (Object.keys(newLayout.zonePositions).length > 0) {
          const zoneUpdates: Record<string, { position: { x: number; y: number }; dimensions: { width: number; height: number } }> = {};
          Object.entries(newLayout.zonePositions).forEach(([id, pos]) => {
            zoneUpdates[id] = {
              position: { x: pos.x, y: pos.y },
              dimensions: { width: pos.width, height: pos.height },
            };
          });
          bulkUpdateZones(zoneUpdates);
        }
      },
    });
  }, [devices, zones, calculateLayout, bulkMoveDevices, bulkUpdateZones, pushHistory]);

  return { calculateLayout, applyLayout };
};

export default useAutoLayout;
