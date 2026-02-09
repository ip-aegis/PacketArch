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
import CanvasControls from './CanvasControls';
import DeviceContextMenu from './DeviceContextMenu';
import { useCanvasSync } from './hooks/useCanvasSync';
import { useClusterView } from './hooks/useClusterView';
import { useNodeDrag } from './hooks/useNodeDrag';
import { useAutoLayout } from './hooks/useAutoLayout';
import { useScenarioStore } from '../../stores/scenarioStore';
import { useHistoryStore } from '../../stores/historyStore';
import { useUIStore } from '../../stores/uiStore';
import type { ClusterViewMode } from '../../stores/uiStore';
import type { ScenarioFlow } from '../../types';
import type { DeviceNodeData } from './nodes/DeviceNode';
import { DEVICE_TYPE_COLORS } from '../../constants/protocols';
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
  const pushHistory = useHistoryStore((state) => state.push);
  const setPropertyContext = useUIStore((state) => state.setPropertyContext);
  const setSelection = useUIStore((state) => state.setSelection);
  const minimapVisible = useUIStore((state) => state.panels.minimapVisible);
  const pendingFitToNode = useUIStore((state) => state.pendingFitToNode);
  const setPendingFitToNode = useUIStore((state) => state.setPendingFitToNode);
  const selectedNodeIds = useUIStore((state) => state.selectedNodeIds);
  const { applyLayout } = useAutoLayout();

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

  // Handle new connections
  const onConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return;

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
    },
    [addFlow, removeFlow, pushHistory]
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

  // Handle edge selection
  const onEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      setPropertyContext('flow', [edge.id]);
      setSelection([], [edge.id]);
    },
    [setPropertyContext, setSelection]
  );

  // Handle canvas click (deselect)
  const onPaneClick = useCallback(() => {
    setPropertyContext(null, []);
    setSelection([], []);
    setContextMenu(null);
  }, [setPropertyContext, setSelection]);

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
      return DEVICE_TYPE_COLORS[deviceType] || '#6a9fd4';
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
