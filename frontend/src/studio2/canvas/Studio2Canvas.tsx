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

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  applyNodeChanges,
  applyEdgeChanges,
  useReactFlow,
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

import { message } from 'antd';

import DeviceNode2 from './DeviceNode2';
import ZoneNode2 from './ZoneNode2';
import FlowEdge2 from './FlowEdge2';
import { useDocumentStore, commands } from '../document/documentStore';
import { placeDevice } from '../document/createDevice';
import { useStudio2UI } from '../uiState';
import { layoutDocument, isUnpositioned } from './layout';
import { PROTOCOL_EDGE_LABELS } from '../../constants/protocols';
import type { PaletteDeviceResponse } from '../../api/fingerprints';
import type { ScenarioFlow, ProtocolType } from '../../types';
import { SURFACE, TEXT, FONT, ACCENT, protocolEdgeColor } from '../tokens';

interface PendingConnection {
  sourceId: string;
  targetId: string;
  options: ProtocolType[];
  /** Position within the canvas wrapper, px */
  x: number;
  y: number;
}

const nodeTypes = { device2: DeviceNode2, zone2: ZoneNode2 };
const edgeTypes = { flow2: FlowEdge2 };

function newId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

function createFlow(sourceId: string, targetId: string, protocol: ProtocolType): void {
  const state = useDocumentStore.getState();
  if (!state.doc) return;
  const source = state.doc.devices[sourceId];
  const target = state.doc.devices[targetId];
  if (!source || !target) return;
  const flow: ScenarioFlow = {
    id: newId('flow'),
    name: `${source.name} -> ${target.name}`,
    sourceDeviceId: sourceId,
    targetDeviceId: targetId,
    protocol,
    protocolConfig: {},
    timing: { intervalMs: 1000, jitterMs: 100 },
    phases: { startup: true, steadyState: true, maintenance: true, shutdown: true },
  };
  state.dispatch(commands.addFlow(flow));
}

/** Must be rendered inside a ReactFlowProvider (Studio2Page owns it). */
const Studio2Canvas: React.FC = () => {
  const doc = useDocumentStore((s) => s.doc);
  const setSelection = useDocumentStore((s) => s.setSelection);
  const { fitView, screenToFlowPosition, flowToScreenPosition } = useReactFlow();
  const armedTemplate = useStudio2UI((s) => s.armedTemplate);
  const setArmedTemplate = useStudio2UI((s) => s.setArmedTemplate);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [pending, setPending] = useState<PendingConnection | null>(null);

  // Escape cancels click-to-place arming and the protocol picker
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setArmedTemplate(null);
        setPending(null);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [setArmedTemplate]);

  // Auto-layout scenarios that arrive with no saved positions (templated /
  // AI-generated ones would otherwise pile every node at the origin).
  // One undoable command; runs once per loaded scenario.
  const autoLaidRef = useRef<string | null>(null);
  const docMetaId = useDocumentStore((s) => s.doc?.meta.id ?? null);
  useEffect(() => {
    if (!docMetaId || autoLaidRef.current === docMetaId) return;
    autoLaidRef.current = docMetaId;
    const state = useDocumentStore.getState();
    if (!state.doc || !isUnpositioned(state.doc)) return;
    const cmd = layoutDocument(state.doc);
    if (cmd) {
      state.dispatch(cmd);
      requestAnimationFrame(() => fitView({ padding: 0.15, duration: 300 }));
    }
  }, [docMetaId, fitView]);

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

  // Connect: one common protocol → create immediately; several → inline
  // picker at the midpoint; none → reject (realism rule: flows must use a
  // protocol both endpoints support).
  const onConnect = useCallback(
    (connection: Connection) => {
      const state = useDocumentStore.getState();
      if (!state.doc || !connection.source || !connection.target) return;
      const source = state.doc.devices[connection.source];
      const target = state.doc.devices[connection.target];
      if (!source || !target) return;

      const common = source.protocols.filter((p) => target.protocols.includes(p));
      if (common.length === 0) {
        message.warning(
          `${source.name} and ${target.name} share no protocol — flow not created.`,
          4,
        );
        return;
      }
      if (common.length === 1) {
        createFlow(source.id, target.id, common[0]);
        return;
      }

      const mid = flowToScreenPosition({
        x: (source.position.x + target.position.x) / 2,
        y: (source.position.y + target.position.y) / 2,
      });
      const rect = wrapperRef.current?.getBoundingClientRect();
      setPending({
        sourceId: source.id,
        targetId: target.id,
        options: common,
        x: mid.x - (rect?.left ?? 0),
        y: mid.y - (rect?.top ?? 0),
      });
    },
    [flowToScreenPosition],
  );

  // Palette drop / click-to-place
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'copy';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      const payload = event.dataTransfer.getData('application/json');
      if (!payload) return;
      event.preventDefault();
      try {
        const template = JSON.parse(payload) as PaletteDeviceResponse;
        const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
        void placeDevice(template, position);
      } catch (e) {
        console.error('Failed to parse palette payload', e);
      }
    },
    [screenToFlowPosition],
  );

  const onPaneClick = useCallback(
    (event: React.MouseEvent) => {
      setPending(null);
      if (!armedTemplate) return;
      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
      void placeDevice(armedTemplate, position);
      // Shift-click keeps the template armed for rapid placement
      if (!event.shiftKey) setArmedTemplate(null);
    },
    [armedTemplate, screenToFlowPosition, setArmedTemplate],
  );

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
    <div ref={wrapperRef} style={{ width: '100%', height: '100%', position: 'relative' }}>
      <style>{`
        .s2-node:hover .s2-handle, .s2-node .s2-handle.connectingto, .react-flow__node:hover .s2-handle { opacity: 1 !important; }
        .react-flow__pane { cursor: ${armedTemplate ? 'crosshair' : 'default'}; }
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
        onPaneClick={onPaneClick}
        onDrop={onDrop}
        onDragOver={onDragOver}
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

      {/* Inline protocol picker — shown when the connected endpoints share
          more than one protocol */}
      {pending && (
        <div
          role="menu"
          aria-label="Choose flow protocol"
          style={{
            position: 'absolute',
            left: pending.x,
            top: pending.y,
            transform: 'translate(-50%, -50%)',
            zIndex: 20,
            background: SURFACE.raised,
            border: `1px solid ${SURFACE.border}`,
            borderRadius: 8,
            padding: 6,
            boxShadow: '0 6px 24px rgba(0,0,0,0.5)',
            fontFamily: FONT.ui,
            minWidth: 150,
          }}
        >
          <div
            style={{
              fontFamily: FONT.mono,
              fontSize: 9.5,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: TEXT.muted,
              padding: '2px 8px 6px',
            }}
          >
            Protocol
          </div>
          {pending.options.map((p) => (
            <button
              key={p}
              role="menuitem"
              onClick={() => {
                createFlow(pending.sourceId, pending.targetId, p);
                setPending(null);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                width: '100%',
                background: 'transparent',
                border: 'none',
                borderRadius: 5,
                color: TEXT.primary,
                fontFamily: FONT.ui,
                fontSize: 12.5,
                padding: '5px 8px',
                cursor: 'pointer',
                textAlign: 'left',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = SURFACE.hover)}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <span
                style={{
                  width: 14,
                  height: 3,
                  borderRadius: 2,
                  background: protocolEdgeColor(p),
                  flex: '0 0 auto',
                }}
              />
              {PROTOCOL_EDGE_LABELS[p as keyof typeof PROTOCOL_EDGE_LABELS] ?? p}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default Studio2Canvas;
