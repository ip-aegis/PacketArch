/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Main React Flow canvas wrapper
 * Enhanced with keyboard shortcuts and device-colored minimap
 */

import React, { useCallback, useState, useEffect } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Panel,
  ReactFlowProvider,
  applyNodeChanges,
  applyEdgeChanges,
  useReactFlow,
} from '@xyflow/react';
import type { NodeChange, EdgeChange, Connection, Node, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import DeviceNode from './nodes/DeviceNode';
import ZoneNode from './nodes/ZoneNode';
import ClusterNode from './nodes/ClusterNode';
import type { ClusterNodeData } from './nodes/ClusterNode';
import FlowEdge from './edges/FlowEdge';
import type { FlowEdgeData } from './edges/FlowEdge';
import ConduitEdge from './edges/ConduitEdge';
import CanvasControls from './CanvasControls';
import DeviceContextMenu from './DeviceContextMenu';
import EmptyCanvasOverlay from './EmptyCanvasOverlay';
import { useCanvasSync } from './hooks/useCanvasSync';
import { useClusterView } from './hooks/useClusterView';
import { useNodeDrag } from './hooks/useNodeDrag';
import { useAutoLayout } from './hooks/useAutoLayout';
import { useRationalityEvaluator } from './hooks/useRationalityEvaluator';
import { evaluateFlowRationality } from '../../stores/rationalityStore';
import { useScenarioStore } from '../../stores/scenarioStore';
import { useHistoryStore } from '../../stores/historyStore';
import { useUIStore } from '../../stores/uiStore';
import type { ClusterViewMode } from '../../stores/uiStore';
import type { ScenarioFlow, ScenarioConduit } from '../../types';
import type { DeviceNodeData } from './nodes/DeviceNode';
import { getDeviceTypeColor } from '../../constants/deviceTypeRegistry';
import { validateProtocolVendorAffinity } from '../../utils/protocolVendorAffinity';
import { message } from 'antd';
import { registerCanvasDeps } from '../command-palette/CommandPalette';

const nodeTypes = {
  deviceNode: DeviceNode,
  zoneNode: ZoneNode,
  clusterNode: ClusterNode,
} as const satisfies Record<string, React.ComponentType<unknown>>;

const edgeTypes = {
  flowEdge: FlowEdge,
  conduitEdge: ConduitEdge,
} as const satisfies Record<string, React.ComponentType<unknown>>;

interface ScenarioCanvasProps {
  onDrop: (event: React.DragEvent<HTMLDivElement>) => void;
  onDragOver: (event: React.DragEvent<HTMLDivElement>) => void;
}

const ScenarioCanvas: React.FC<ScenarioCanvasProps> = ({ onDrop, onDragOver }) => {
  // Get nodes/edges from sync hook (source of truth from store)
  const { nodes: storeNodes, edges: storeEdges } = useCanvasSync();
  // Cluster view: transforms nodes/edges when a grouping mode is active
  const {
    nodes: viewNodes,
    edges: viewEdges,
    isClusterViewActive,
    toggleCluster,
  } = useClusterView(storeNodes, storeEdges);
  const { handleDrop: handleNodeDrop } = useNodeDrag();
  const { fitView, zoomIn, zoomOut } = useReactFlow();
  const moveDevice = useScenarioStore((state) => state.moveDevice);

  // Context menu state
  const [contextMenu, setContextMenu] = useState<{ deviceId: string; x: number; y: number } | null>(null);

  // Local state for React Flow to manage drag interactions
  const [nodes, setNodes] = useState<Node[]>(viewNodes);
  const [edges, setEdges] = useState<Edge[]>(viewEdges);

  // Sync local state when store or cluster view changes
  useEffect(() => {
    setNodes(viewNodes);
  }, [viewNodes]);

  useEffect(() => {
    setEdges(viewEdges);
  }, [viewEdges]);

  // Listen for device context menu events from DeviceNode
  useEffect(() => {
    const handler = (e: Event) => {
      const { deviceId, x, y } = (e as CustomEvent).detail;
      setContextMenu({ deviceId, x, y });
    };
    window.addEventListener('device-context-menu', handler);
    return () => window.removeEventListener('device-context-menu', handler);
  }, []);

  const addFlow = useScenarioStore((state) => state.addFlow);
  const removeFlow = useScenarioStore((state) => state.removeFlow);
  const removeDevice = useScenarioStore((state) => state.removeDevice);
  const addConduit = useScenarioStore((state) => state.addConduit);
  const removeConduit = useScenarioStore((state) => state.removeConduit);
  const pushHistory = useHistoryStore((state) => state.push);
  const setPropertyContext = useUIStore((state) => state.setPropertyContext);
  const setSelectedAggregateEdge = useUIStore((state) => state.setSelectedAggregateEdge);
  const activeTool = useUIStore((state) => state.tool.activeTool);
  const setActiveTool = useUIStore((state) => state.setActiveTool);
  const setSelection = useUIStore((state) => state.setSelection);
  const minimapVisible = useUIStore((state) => state.panels.minimapVisible);
  const pendingFitToNode = useUIStore((state) => state.pendingFitToNode);
  const setPendingFitToNode = useUIStore((state) => state.setPendingFitToNode);
  const selectedNodeIds = useUIStore((state) => state.selectedNodeIds);
  const { applyLayout } = useAutoLayout();
  // Phase 7: evaluate every flow against the architecture comm matrix
  // and stash results in rationalityStore for FlowEdge / CanvasControls
  // to render. Caches by (src_role, tgt_role, vertical, protocol).
  useRationalityEvaluator();

  // Auto-apply Purdue layout the first time a scenario is shown if it has
  // never been laid out (i.e. no zone or device has a saved position). This
  // catches templated scenarios that arrive with default {0,0}-ish state and
  // leaves manually-arranged scenarios alone.
  const scenarioId = useScenarioStore((s) => s.id);
  const deviceCount = useScenarioStore((s) => Object.keys(s.devices).length);
  const autoLaidOutForRef = React.useRef<string | null>(null);
  useEffect(() => {
    if (!scenarioId || autoLaidOutForRef.current === scenarioId) return;
    const { devices: ds, zones: zs } = useScenarioStore.getState();
    const deviceList = Object.values(ds);
    const zoneList = Object.values(zs);
    if (deviceList.length === 0) return; // nothing to lay out yet
    const anyDevicePos = deviceList.some((d) => d.position && (d.position.x !== 0 || d.position.y !== 0));
    const anyZonePos = zoneList.some((z) => z.position && (z.position.x !== 0 || z.position.y !== 0));
    if (anyDevicePos || anyZonePos) {
      // Already laid out — respect the saved positions.
      autoLaidOutForRef.current = scenarioId;
      return;
    }
    autoLaidOutForRef.current = scenarioId;
    applyLayout('purdue');
    // Center on the result after the next frame.
    requestAnimationFrame(() => fitView({ padding: 0.15, duration: 300 }));
  }, [scenarioId, applyLayout, fitView, storeNodes.length]);

  // Register canvas deps for command palette (lives outside ReactFlowProvider)
  useEffect(() => {
    registerCanvasDeps({
      zoomIn: () => zoomIn(),
      zoomOut: () => zoomOut(),
      fitView: () => fitView({ padding: 0.15, duration: 300 }),
      applyLayout: (type: string) => applyLayout(type as 'purdue' | 'dataflow' | 'grid' | 'circular'),
      deleteSelected: () => {
        const ids = useUIStore.getState().selectedNodeIds;
        ids.forEach((id) => removeDevice(id));
      },
      saveVersion: () => {
        // Dispatch Ctrl+S event to trigger existing handler in ScenarioStudioPage
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true }));
      },
      openVersionHistory: () => {
        // Dispatch custom event for CanvasControls to open its drawer
        window.dispatchEvent(new CustomEvent('command-palette:open-version-history'));
      },
      openCustomizeNames: () => {
        window.dispatchEvent(new CustomEvent('command-palette:open-customize-names'));
      },
    });
    return () => registerCanvasDeps(null);
  }, [fitView, zoomIn, zoomOut, applyLayout, removeDevice]);

  // Command palette device search → navigate to device
  useEffect(() => {
    if (pendingFitToNode) {
      setSelection([pendingFitToNode], []);
      setPropertyContext('device', [pendingFitToNode]);
      fitView({ nodes: [{ id: pendingFitToNode }], padding: 0.3, duration: 300 });
      setPendingFitToNode(null);
    }
  }, [pendingFitToNode, fitView, setSelection, setPropertyContext, setPendingFitToNode]);

  // Handle drop from palette
  const onCanvasDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      const deviceData = event.dataTransfer.getData('application/json');
      if (deviceData) {
        try {
          const deviceProfile = JSON.parse(deviceData);
          handleNodeDrop(event, deviceProfile);
        } catch (error) {
          console.error('Failed to parse device data:', error);
        }
      }
      onDrop(event);
    },
    [handleNodeDrop, onDrop]
  );

  // Handle node changes - apply all changes for smooth dragging
  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      // Apply all changes to local state for smooth React Flow interaction
      setNodes((nds) => applyNodeChanges(changes, nds));

      // When drag ends, sync the final position to the store
      // Skip store sync for cluster/container nodes (computed positions, not persisted)
      if (!isClusterViewActive) {
        changes.forEach((change) => {
          if (change.type === 'position' && change.position && !change.dragging) {
            moveDevice(change.id, change.position);
          }
        });
      }
    },
    [moveDevice, isClusterViewActive]
  );

  // Handle edge changes
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      // Apply changes to local state
      setEdges((eds) => applyEdgeChanges(changes, eds));

      // Handle removals in store
      changes.forEach((change) => {
        if (change.type === 'remove') {
          const flow = useScenarioStore.getState().flows[change.id];
          if (flow) {
            removeFlow(change.id);
            pushHistory({
              type: 'REMOVE_FLOW',
              undo: () => addFlow(flow),
              redo: () => removeFlow(change.id),
              timestamp: Date.now(),
            });
          }
        }
      });
    },
    [removeFlow, addFlow, pushHistory]
  );

  // Handle new connections (flows or conduits depending on active tool)
  const onConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return;

      const currentTool = useUIStore.getState().tool.activeTool;

      // --- Conduit creation mode ---
      if (currentTool === 'conduit') {
        const zones = useScenarioStore.getState().zones;
        const zoneA = zones[connection.source];
        const zoneB = zones[connection.target];

        if (!zoneA || !zoneB) {
          message.warning('Conduits must connect two zones');
          return;
        }
        if (connection.source === connection.target) {
          message.warning('Cannot create a conduit from a zone to itself');
          return;
        }

        // Check for duplicate
        const existingConduits = useScenarioStore.getState().conduits;
        const duplicate = Object.values(existingConduits).find(
          (c) =>
            (c.sourceZoneId === connection.source && c.targetZoneId === connection.target) ||
            (c.sourceZoneId === connection.target && c.targetZoneId === connection.source)
        );
        if (duplicate) {
          message.info(`Conduit already exists: ${duplicate.name}`);
          setPropertyContext('conduit', [duplicate.id]);
          return;
        }

        const conduitId = `conduit-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const newConduit: ScenarioConduit = {
          id: conduitId,
          name: `${zoneA.name} \u2194 ${zoneB.name}`,
          sourceZoneId: connection.source,
          targetZoneId: connection.target,
          direction: 'bidirectional',
          allowedProtocols: [],
        };

        addConduit(newConduit);
        pushHistory({
          type: 'ADD_CONDUIT',
          undo: () => removeConduit(conduitId),
          redo: () => addConduit(newConduit),
          timestamp: Date.now(),
        });
        setPropertyContext('conduit', [conduitId]);
        setActiveTool('select');
        return;
      }

      // --- Standard flow creation ---
      const devices = useScenarioStore.getState().devices;
      const sourceDevice = devices[connection.source];
      const targetDevice = devices[connection.target];

      if (!sourceDevice || !targetDevice) return;

      // Find common protocol
      const commonProtocols = sourceDevice.protocols.filter((p) =>
        targetDevice.protocols.includes(p)
      );

      const protocol = commonProtocols[0] || sourceDevice.protocols[0];
      if (!protocol) return;

      // Warn on unusual protocol-vendor combinations
      for (const dev of [sourceDevice, targetDevice]) {
        if (dev.vendor) {
          const warnings = validateProtocolVendorAffinity(dev.vendor, [protocol]);
          if (warnings.length > 0) {
            message.warning(warnings[0]);
          }
        }
      }

      const flowId = `flow-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const newFlow: ScenarioFlow = {
        id: flowId,
        name: `${sourceDevice.name} -> ${targetDevice.name}`,
        sourceDeviceId: connection.source,
        targetDeviceId: connection.target,
        protocol,
        protocolConfig: {},
        timing: {
          intervalMs: 1000,
          jitterMs: 100,
        },
        phases: {
          startup: true,
          steadyState: true,
          maintenance: true,
          shutdown: true,
        },
      };

      addFlow(newFlow);
      pushHistory({
        type: 'ADD_FLOW',
        undo: () => removeFlow(flowId),
        redo: () => addFlow(newFlow),
        timestamp: Date.now(),
      });

      // Phase 7: live rationality check. Non-blocking — surfaces a
      // toast hint when the user-drawn flow falls outside the
      // architecture comm matrix, but the flow stands.
      const verticalNow = useScenarioStore.getState().vertical;
      void evaluateFlowRationality(
        newFlow,
        useScenarioStore.getState().devices,
        verticalNow,
      ).then((res) => {
        if (!res) return;
        if (res.status === 'off-rail' && res.suggestion) {
          message.info({
            content: `Architecture rail: ${res.suggestion}`,
            duration: 6,
          });
        } else if (res.status === 'mismatch' && res.suggestion) {
          message.info({
            content: `Architecture rail: ${res.suggestion}`,
            duration: 6,
          });
        }
      });

      // Check cross-zone conduit compliance
      const storeState = useScenarioStore.getState();
      const sourceZoneId = sourceDevice.zoneId;
      const targetZoneId = targetDevice.zoneId;
      if (sourceZoneId && targetZoneId && sourceZoneId !== targetZoneId) {
        const conduits = storeState.conduits;
        const coveringConduit = Object.values(conduits).find(
          (c) =>
            (c.sourceZoneId === sourceZoneId && c.targetZoneId === targetZoneId) ||
            (c.sourceZoneId === targetZoneId && c.targetZoneId === sourceZoneId)
        );

        if (!coveringConduit) {
          const zones = storeState.zones;
          message.warning(
            `No conduit defined between "${zones[sourceZoneId]?.name || sourceZoneId}" and "${zones[targetZoneId]?.name || targetZoneId}". Flow is non-compliant.`,
            5
          );
        } else if (!coveringConduit.allowedProtocols.includes(protocol)) {
          message.warning(
            `Protocol ${protocol} is not allowed by conduit "${coveringConduit.name}". Flow is non-compliant.`,
            5
          );
        }
      }
    },
    [addFlow, removeFlow, addConduit, removeConduit, pushHistory, setPropertyContext, setActiveTool]
  );

  // Handle node selection
  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (node.type === 'deviceNode') {
        setPropertyContext('device', [node.id]);
        setSelection([node.id], []);
      } else if (node.type === 'zoneNode') {
        setPropertyContext('zone', [node.id]);
        setSelection([node.id], []);
      }
    },
    [setPropertyContext, setSelection]
  );

  // Handle double-click on cluster nodes to expand/collapse
  const onNodeDoubleClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (node.type === 'clusterNode' && node.data) {
        const clusterData = node.data as ClusterNodeData;
        toggleCluster(clusterData.clusterId);
        // Re-center view after expand/collapse
        setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 50);
      }
    },
    [toggleCluster, fitView]
  );

  // Handle edge selection (flow, conduit, or aggregate cluster-to-cluster edge)
  const onEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      if (edge.type === 'conduitEdge') {
        setPropertyContext('conduit', [edge.id]);
        setSelectedAggregateEdge(null);
      } else {
        const edgeData = edge.data as FlowEdgeData | undefined;
        if (edgeData?.aggregateInfo) {
          // Cluster-to-cluster aggregate edge (group-by view): show its info
          setSelectedAggregateEdge(edgeData.aggregateInfo);
          setPropertyContext('clusterEdge', [edge.id]);
        } else {
          setSelectedAggregateEdge(null);
          setPropertyContext('flow', [edge.id]);
        }
      }
      setSelection([], [edge.id]);
    },
    [setPropertyContext, setSelection, setSelectedAggregateEdge]
  );

  // Handle canvas click (deselect)
  const onPaneClick = useCallback(() => {
    setPropertyContext(null, []);
    setSelectedAggregateEdge(null);
    setSelection([], []);
    setContextMenu(null);
  }, [setPropertyContext, setSelection, setSelectedAggregateEdge]);

  // Handle delete key
  const onNodesDelete = useCallback(
    (nodesToDelete: Node[]) => {
      nodesToDelete.forEach((node) => {
        if (node.type === 'deviceNode') {
          const device = useScenarioStore.getState().devices[node.id];
          if (device) {
            removeDevice(node.id);
            pushHistory({
              type: 'REMOVE_DEVICE',
              undo: () => useScenarioStore.getState().addDevice(device),
              redo: () => removeDevice(node.id),
              timestamp: Date.now(),
            });
          }
        }
      });
    },
    [removeDevice, pushHistory]
  );

  // Duplicate selected device (Ctrl+D)
  const duplicateSelectedDevice = useCallback(() => {
    const { selectedNodeIds } = useUIStore.getState();
    if (selectedNodeIds.length === 0) return;

    const devices = useScenarioStore.getState().devices;
    const addDevice = useScenarioStore.getState().addDevice;

    selectedNodeIds.forEach((nodeId) => {
      const device = devices[nodeId];
      if (device) {
        const newId = `device-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const newDevice = {
          ...device,
          id: newId,
          name: `${device.name} (copy)`,
          position: {
            x: device.position.x + 40,
            y: device.position.y + 40,
          },
          network: {
            ...device.network,
            // Clear IP so it can be auto-assigned
            ipAddress: '',
            macAddress: '',
          },
        };
        addDevice(newDevice);
        pushHistory({
          type: 'ADD_DEVICE',
          undo: () => removeDevice(newId),
          redo: () => addDevice(newDevice),
          timestamp: Date.now(),
        });
      }
    });
  }, [pushHistory, removeDevice]);

  // Keyboard shortcuts
  useEffect(() => {
    const GROUP_MODES: ClusterViewMode[] = ['none', 'zone', 'protocol', 'vendor', 'purdueLevel', 'deviceType'];

    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      // Ctrl+D or Cmd+D - Duplicate
      if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
        e.preventDefault();
        duplicateSelectedDevice();
      }

      // Ctrl+A or Cmd+A - Select all devices
      if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
        e.preventDefault();
        const deviceIds = Object.keys(useScenarioStore.getState().devices);
        setSelection(deviceIds, []);
      }

      // G - Cycle through group-by modes
      if (e.key === 'g' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const current = useUIStore.getState().clusterViewMode;
        const idx = GROUP_MODES.indexOf(current);
        const next = GROUP_MODES[(idx + 1) % GROUP_MODES.length];
        useUIStore.getState().setClusterViewMode(next);
        setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 50);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [duplicateSelectedDevice, setSelection, fitView]);

  // Get node color for minimap based on device type or cluster color
  const getNodeColor = useCallback((node: Node) => {
    if (node.type === 'zoneNode' || node.type === 'group') return 'rgba(255,255,255,0.2)';
    if (node.type === 'clusterNode' && node.data) {
      return (node.data as ClusterNodeData).color || '#6a9fd4';
    }
    if (node.type === 'deviceNode' && node.data) {
      const deviceType = (node.data as DeviceNodeData).type;
      return getDeviceTypeColor(deviceType);
    }
    return '#6a9fd4';
  }, []);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      {/* CSS for smooth layout transitions */}
      <style>{`
        .react-flow__node {
          transition: transform 300ms ease-out !important;
        }
        .react-flow__node.dragging {
          transition: none !important;
        }
      `}</style>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onNodeDoubleClick={onNodeDoubleClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        onNodesDelete={onNodesDelete}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onDrop={onCanvasDrop}
        onDragOver={onDragOver}
        snapToGrid={true}
        snapGrid={[20, 20]}
        defaultEdgeOptions={{
          type: 'flowEdge',
          animated: false,
        }}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        attributionPosition="bottom-left"
        minZoom={0.1}
        maxZoom={2}
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        style={{ background: '#1a2332' }}
      >
        <Background color="#2a3a4d" gap={20} />
        {minimapVisible && (
          <MiniMap
            nodeColor={getNodeColor}
            maskColor="rgba(0, 0, 0, 0.5)"
            position="bottom-right"
            style={{ background: '#1a2332', borderRadius: '8px' }}
          />
        )}
        <Controls
          position="top-right"
          showInteractive={false}
          style={{
            background: '#1a2734',
            border: '1px solid #2a3f54',
            borderRadius: '8px',
          }}
          className="dark-controls"
        />
        <Panel position="top-left">
          <CanvasControls />
        </Panel>
      </ReactFlow>
      {deviceCount === 0 && <EmptyCanvasOverlay />}
      {contextMenu && (
        <DeviceContextMenu
          deviceId={contextMenu.deviceId}
          position={{ x: contextMenu.x, y: contextMenu.y }}
          onClose={() => setContextMenu(null)}
        />
      )}
    </div>
  );
};

// Wrap with ReactFlowProvider
const ScenarioCanvasWrapper: React.FC<ScenarioCanvasProps> = (props) => {
  return (
    <ReactFlowProvider>
      <ScenarioCanvas {...props} />
    </ReactFlowProvider>
  );
};

export default ScenarioCanvasWrapper;
