/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 canvas — a controlled React Flow view over the scenario
 * document. All mutations dispatch through the command bus, so every
 * gesture (move, delete, connect) is undoable by construction. React
 * Flow's own selection is the single selection source.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  applyNodeChanges,
  applyEdgeChanges,
} from '@xyflow/react';
import type {
  Node,
  Edge,
  NodeChange,
  EdgeChange,
  Connection,
  OnSelectionChangeParams,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import DeviceNode2 from './DeviceNode2';
import ZoneNode2 from './ZoneNode2';
import FlowEdge2 from './FlowEdge2';
import { useDocumentStore, commands } from '../document/documentStore';
import type { ScenarioFlow } from '../../types';
import { SURFACE, ACCENT } from '../tokens';

const nodeTypes = { device2: DeviceNode2, zone2: ZoneNode2 };
const edgeTypes = { flow2: FlowEdge2 };

function newId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

/** Must be rendered inside a ReactFlowProvider (Studio2Page owns it). */
const Studio2Canvas: React.FC = () => {
  const doc = useDocumentStore((s) => s.doc);
  const dispatch = useDocumentStore((s) => s.dispatch);
  const setSelection = useDocumentStore((s) => s.setSelection);

  // Derive React Flow nodes/edges from the document
  const derivedNodes = useMemo<Node[]>(() => {
    if (!doc) return [];
    const zoneNodes: Node[] = Object.values(doc.zones).map((z) => ({
      id: z.id,
      type: 'zone2',
      position: z.position ?? { x: 0, y: 0 },
      draggable: false,
      selectable: false,
      zIndex: -1,
      data: {
        name: z.name,
        purdueLevel: z.level,
        subnet: z.network?.subnet,
        width: z.dimensions?.width ?? 350,
        height: z.dimensions?.height ?? 300,
      },
    }));
    const deviceNodes: Node[] = Object.values(doc.devices).map((d) => ({
      id: d.id,
      type: 'device2',
      position: d.position ?? { x: 0, y: 0 },
      data: {
        name: d.name,
        deviceType: d.type as string,
        ipAddress: d.network?.ipAddress,
      },
    }));
    return [...zoneNodes, ...deviceNodes];
  }, [doc]);

  const derivedEdges = useMemo<Edge[]>(() => {
    if (!doc) return [];
    return Object.values(doc.flows).map((f) => ({
      id: f.id,
      type: 'flow2',
      source: f.sourceDeviceId,
      target: f.targetDeviceId,
      data: { protocol: f.protocol as string },
    }));
  }, [doc]);

  // Local mirror for smooth dragging; document remains the source of truth.
  // Selection flags live in the mirror — carry them across doc rebuilds so
  // finishing a drag (which dispatches a command) doesn't deselect.
  const [nodes, setNodes] = useState<Node[]>(derivedNodes);
  const [edges, setEdges] = useState<Edge[]>(derivedEdges);
  useEffect(() => {
    setNodes((prev) => {
      const selected = new Set(prev.filter((n) => n.selected).map((n) => n.id));
      return derivedNodes.map((n) => (selected.has(n.id) ? { ...n, selected: true } : n));
    });
  }, [derivedNodes]);
  useEffect(() => {
    setEdges((prev) => {
      const selected = new Set(prev.filter((e) => e.selected).map((e) => e.id));
      return derivedEdges.map((e) => (selected.has(e.id) ? { ...e, selected: true } : e));
    });
  }, [derivedEdges]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      setNodes((nds) => applyNodeChanges(changes, nds));
      const state = useDocumentStore.getState();
      if (!state.doc) return;
      const moves = changes
        .filter(
          (c): c is Extract<NodeChange, { type: 'position' }> =>
            c.type === 'position' && !!c.position && !c.dragging,
        )
        .filter((c) => state.doc!.devices[c.id])
        .map((c) => ({ id: c.id, position: c.position! }));
      if (moves.length > 0) {
        state.dispatch(commands.moveDevices(state.doc, moves));
      }
    },
    [],
  );

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges((eds) => applyEdgeChanges(changes, eds));
    const state = useDocumentStore.getState();
    if (!state.doc) return;
    const removed = changes
      .filter((c): c is Extract<EdgeChange, { type: 'remove' }> => c.type === 'remove')
      .map((c) => c.id)
      .filter((id) => state.doc!.flows[id]);
    if (removed.length > 0) {
      state.dispatch(commands.deleteFlows(state.doc, removed));
    }
  }, []);

  const onNodesDelete = useCallback((deleted: Node[]) => {
    const state = useDocumentStore.getState();
    if (!state.doc) return;
    const deviceIds = deleted.filter((n) => n.type === 'device2').map((n) => n.id);
    if (deviceIds.length > 0) {
      state.dispatch(commands.deleteDevices(state.doc, deviceIds));
    }
  }, []);

  const onConnect = useCallback((connection: Connection) => {
    const state = useDocumentStore.getState();
    if (!state.doc || !connection.source || !connection.target) return;
    const source = state.doc.devices[connection.source];
    const target = state.doc.devices[connection.target];
    if (!source || !target) return;

    const common = source.protocols.filter((p) => target.protocols.includes(p));
    const protocol = common[0] ?? source.protocols[0];
    if (!protocol) return;

    const flow: ScenarioFlow = {
      id: newId('flow'),
      name: `${source.name} -> ${target.name}`,
      sourceDeviceId: source.id,
      targetDeviceId: target.id,
      protocol,
      protocolConfig: {},
      timing: { intervalMs: 1000, jitterMs: 100 },
      phases: { startup: true, steadyState: true, maintenance: true, shutdown: true },
    };
    state.dispatch(commands.addFlow(flow));
  }, []);

  const onSelectionChange = useCallback(
    ({ nodes: selNodes, edges: selEdges }: OnSelectionChangeParams) => {
      setSelection(
        selNodes.filter((n) => n.type === 'device2').map((n) => n.id),
        selEdges.map((e) => e.id),
      );
    },
    [setSelection],
  );

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <style>{`
        .s2-node:hover .s2-handle, .s2-node .s2-handle.connectingto, .react-flow__node:hover .s2-handle { opacity: 1 !important; }
        .react-flow__pane { cursor: default; }
        .s2-flow .react-flow__edge.selected .react-flow__edge-path { filter: none; }
        .s2-flow .react-flow__attribution { background: transparent; color: ${SURFACE.border}; }
      `}</style>
      <ReactFlow
        className="s2-flow"
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodesDelete={onNodesDelete}
        onConnect={onConnect}
        onSelectionChange={onSelectionChange}
        snapToGrid
        snapGrid={[20, 20]}
        minZoom={0.1}
        maxZoom={2}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        proOptions={{ hideAttribution: false }}
        defaultEdgeOptions={{ type: 'flow2' }}
        connectionLineStyle={{ stroke: ACCENT, strokeWidth: 1.5 }}
        style={{ background: SURFACE.ground }}
      >
        <Background variant={BackgroundVariant.Dots} color={SURFACE.grid} gap={22} size={1} />
      </ReactFlow>
    </div>
  );
};

export default Studio2Canvas;
