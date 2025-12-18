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
import FlowEdge from './edges/FlowEdge';
import CanvasControls from './CanvasControls';
import { useCanvasSync } from './hooks/useCanvasSync';
import { useNodeDrag } from './hooks/useNodeDrag';
import { useScenarioStore } from '../../stores/scenarioStore';
import { useHistoryStore } from '../../stores/historyStore';
import { useUIStore } from '../../stores/uiStore';
import type { ScenarioFlow, DeviceType } from '../../types';

// Device type colors for minimap - matching DeviceNode
const DEVICE_TYPE_COLORS: Record<DeviceType, string> = {
  plc: '#049FD9',
  hmi: '#6CC04A',
  rtu: '#FBAB18',
  drive: '#FF7043',
  sensor: '#00BCEB',
  relay: '#E53935',
  ews: '#9C27B0',
  historian: '#607D8B',
};

const nodeTypes = {
  deviceNode: DeviceNode as any,
  zoneNode: ZoneNode as any,
};

const edgeTypes = {
  flowEdge: FlowEdge as any,
};

interface ScenarioCanvasProps {
  onDrop: (event: React.DragEvent<HTMLDivElement>) => void;
  onDragOver: (event: React.DragEvent<HTMLDivElement>) => void;
}

const ScenarioCanvas: React.FC<ScenarioCanvasProps> = ({ onDrop, onDragOver }) => {
  // Get nodes/edges from sync hook (source of truth from store)
  const { nodes: storeNodes, edges: storeEdges } = useCanvasSync();
  const { handleDrop: handleNodeDrop } = useNodeDrag();
  const moveDevice = useScenarioStore((state) => state.moveDevice);

  // Local state for React Flow to manage drag interactions
  const [nodes, setNodes] = useState<Node[]>(storeNodes);
  const [edges, setEdges] = useState<Edge[]>(storeEdges);

  // Sync local state when store changes (e.g., new devices added)
  useEffect(() => {
    setNodes(storeNodes);
  }, [storeNodes]);

  useEffect(() => {
    setEdges(storeEdges);
  }, [storeEdges]);
  const addFlow = useScenarioStore((state) => state.addFlow);
  const removeFlow = useScenarioStore((state) => state.removeFlow);
  const removeDevice = useScenarioStore((state) => state.removeDevice);
  const pushHistory = useHistoryStore((state) => state.push);
  const setPropertyContext = useUIStore((state) => state.setPropertyContext);
  const setSelection = useUIStore((state) => state.setSelection);
  const minimapVisible = useUIStore((state) => state.panels.minimapVisible);

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
      changes.forEach((change) => {
        if (change.type === 'position' && change.position && !change.dragging) {
          moveDevice(change.id, change.position);
        }
      });
    },
    [moveDevice]
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
    (_event: React.MouseEvent, node: any) => {
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

  // Handle edge selection
  const onEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: any) => {
      setPropertyContext('flow', [edge.id]);
      setSelection([], [edge.id]);
    },
    [setPropertyContext, setSelection]
  );

  // Handle canvas click (deselect)
  const onPaneClick = useCallback(() => {
    setPropertyContext(null, []);
    setSelection([], []);
  }, [setPropertyContext, setSelection]);

  // Handle delete key
  const onNodesDelete = useCallback(
    (nodesToDelete: any[]) => {
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
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [duplicateSelectedDevice, setSelection]);

  // Get node color for minimap based on device type
  const getNodeColor = useCallback((node: Node) => {
    if (node.type === 'zoneNode') return 'rgba(255,255,255,0.2)';
    if (node.type === 'deviceNode' && node.data) {
      const deviceType = (node.data as any).type as DeviceType;
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
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        onNodesDelete={onNodesDelete}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onDrop={onCanvasDrop}
        onDragOver={onDragOver}
        snapToGrid={true}
        snapGrid={[16, 16]}
        defaultEdgeOptions={{
          type: 'flowEdge',
          animated: false,
        }}
        fitView={false}
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
