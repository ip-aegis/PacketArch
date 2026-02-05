/**
 * Hook to sync React Flow nodes/edges with scenarioStore
 * Transforms between store format and React Flow format
 */

import { useMemo } from 'react';
import type { Node, Edge } from '@xyflow/react';
import { useScenarioStore } from '../../../stores/scenarioStore';
import type { DeviceNodeData } from '../nodes/DeviceNode';
import type { FlowEdgeData } from '../edges/FlowEdge';
import type { ZoneNodeData } from '../nodes/ZoneNode';
import { useShallow } from 'zustand/react/shallow';

// Stable marker object to avoid recreation
const ARROW_MARKER = {
  type: 'arrowclosed' as const,
  width: 20,
  height: 20,
};

export const useCanvasSync = () => {
  // Subscribe to devices and zones with shallow comparison
  const devices = useScenarioStore(useShallow((state) => state.devices));
  const zones = useScenarioStore(useShallow((state) => state.zones));
  const flows = useScenarioStore(useShallow((state) => state.flows));

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
        x: 100 + (index % 5) * 180,
        y: 100 + Math.floor(index / 5) * 150,
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
          network: zone.network || {},
        },
      };
    });

    return [...zoneNodes, ...deviceNodes];
  }, [devices, zones]);

  // Convert flows to React Flow edges
  const edges = useMemo(() => {
    const flowEdges: Edge<FlowEdgeData>[] = Object.values(flows).map((flow) => ({
      id: flow.id,
      source: flow.sourceDeviceId,
      target: flow.targetDeviceId,
      type: 'flowEdge',
      data: {
        protocol: flow.protocol,
        name: flow.name,
      },
      animated: false,
      markerEnd: ARROW_MARKER,
    }));

    return flowEdges;
  }, [flows]);

  return { nodes, edges };
};

export default useCanvasSync;
