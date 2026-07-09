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
import ClusterNode2 from './ClusterNode2';
import type { ClusterNode2Data } from './ClusterNode2';
import FlowEdge2 from './FlowEdge2';
import ConduitEdge2 from './ConduitEdge2';
import AggregateEdge2 from './AggregateEdge2';
import { useClusterView2 } from './useClusterView2';
import { useDocumentStore, commands } from '../document/documentStore';
import { placeDevice } from '../document/createDevice';
import { useStudio2UI, GROUP_BY_MODES } from '../uiState';
import { useHealth } from '../health/healthStore';
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

const nodeTypes = { device2: DeviceNode2, zone2: ZoneNode2, cluster2: ClusterNode2 };
const edgeTypes = { flow2: FlowEdge2, conduit2: ConduitEdge2, aggregate2: AggregateEdge2 };

function newId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

/** Smallest zone whose rect contains the point (tightest wins on overlap). */
function findZoneAt(
  zones: Record<string, import('../../types').ScenarioZone>,
  point: { x: number; y: number },
): import('../../types').ScenarioZone | undefined {
  let best: import('../../types').ScenarioZone | undefined;
  let bestArea = Infinity;
  for (const zone of Object.values(zones)) {
    const x = zone.position?.x ?? 0;
    const y = zone.position?.y ?? 0;
    const w = zone.dimensions?.width ?? 350;
    const h = zone.dimensions?.height ?? 300;
    if (point.x >= x && point.x <= x + w && point.y >= y && point.y <= y + h) {
      const area = w * h;
      if (area < bestArea) {
        best = zone;
        bestArea = area;
      }
    }
  }
  return best;
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
  const zoneArmed = useStudio2UI((s) => s.zoneArmed);
  const setZoneArmed = useStudio2UI((s) => s.setZoneArmed);
  const conduitArmed = useStudio2UI((s) => s.conduitArmed);
  const setConduitArmed = useStudio2UI((s) => s.setConduitArmed);
  const groupBy = useStudio2UI((s) => s.groupBy);
  const expandedClusterIds = useStudio2UI((s) => s.expandedClusterIds);
  const toggleCluster = useStudio2UI((s) => s.toggleCluster);
  const { byDevice: statusByDevice, byFlow: statusByFlow } = useHealth();
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [pending, setPending] = useState<PendingConnection | null>(null);

  // Escape cancels click-to-place arming and the protocol picker
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setArmedTemplate(null);
        setZoneArmed(false);
        setConduitArmed(false);
        setPending(null);
        return;
      }
      // G cycles the group-by cluster modes
      if (
        e.key === 'g' &&
        !e.ctrlKey &&
        !e.metaKey &&
        !e.altKey &&
        !(e.target instanceof HTMLInputElement) &&
        !(e.target instanceof HTMLTextAreaElement) &&
        !(e.target instanceof HTMLSelectElement)
      ) {
        const ui = useStudio2UI.getState();
        const idx = GROUP_BY_MODES.indexOf(ui.groupBy);
        ui.setGroupBy(GROUP_BY_MODES[(idx + 1) % GROUP_BY_MODES.length]);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [setArmedTemplate, setZoneArmed, setConduitArmed]);

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

  // Derive React Flow nodes/edges from the document. Zones are real parent
  // containers: member devices are children with positions RELATIVE to the
  // zone (the document always stores absolute positions, so v1 and the
  // backend see the same shape).
  const derivedNodes = useMemo<Node[]>(() => {
    if (!doc) return [];
    const zoneNodes: Node[] = Object.values(doc.zones).map((z) => ({
      id: z.id,
      type: 'zone2',
      position: z.position ?? { x: 0, y: 0 },
      style: {
        width: z.dimensions?.width ?? 350,
        height: z.dimensions?.height ?? 300,
      },
      data: {
        name: z.name,
        purdueLevel: z.level,
        subnet: z.network?.subnet,
      },
    }));
    const deviceNodes: Node[] = Object.values(doc.devices).map((d) => {
      const abs = d.position ?? { x: 0, y: 0 };
      const zone = d.zoneId ? doc.zones[d.zoneId] : undefined;
      const position = zone
        ? { x: abs.x - (zone.position?.x ?? 0), y: abs.y - (zone.position?.y ?? 0) }
        : abs;
      return {
        id: d.id,
        type: 'device2',
        position,
        ...(zone ? { parentId: zone.id } : {}),
        data: {
          name: d.name,
          deviceType: d.type as string,
          ipAddress: d.network?.ipAddress,
          status: statusByDevice[d.id],
        },
      };
    });
    return [...zoneNodes, ...deviceNodes];
  }, [doc, statusByDevice]);

  const derivedEdges = useMemo<Edge[]>(() => {
    if (!doc) return [];
    const flowEdges: Edge[] = Object.values(doc.flows).map((f) => ({
      id: f.id,
      type: 'flow2',
      source: f.sourceDeviceId,
      target: f.targetDeviceId,
      data: { protocol: f.protocol as string, status: statusByFlow[f.id] },
    }));
    const conduitEdges: Edge[] = Object.values(doc.conduits)
      .filter((c) => doc.zones[c.sourceZoneId] && doc.zones[c.targetZoneId])
      .map((c) => ({
        id: c.id,
        type: 'conduit2',
        source: c.sourceZoneId,
        target: c.targetZoneId,
        sourceHandle: 'conduit-s',
        targetHandle: 'conduit-t',
        data: {
          name: c.name,
          direction: c.direction,
          protocolCount: c.allowedProtocols?.length,
        },
      }));
    return [...flowEdges, ...conduitEdges];
  }, [doc, statusByFlow]);

  // Group-by cluster view sits between the derived graph and React Flow
  const { nodes: viewNodes, edges: viewEdges } = useClusterView2(
    doc,
    derivedNodes,
    derivedEdges,
    groupBy,
    expandedClusterIds,
  );
  const clusterViewActive = groupBy !== 'none';

  // Local mirror for smooth dragging; document remains the source of truth.
  // Selection flags live in the mirror — carry them across doc rebuilds so
  // finishing a drag (which dispatches a command) doesn't deselect.
  // nodesRef mirrors the state synchronously so gesture-end handlers can
  // read authoritative geometry without waiting for a render.
  const [nodes, setNodesState] = useState<Node[]>(viewNodes);
  const [edges, setEdges] = useState<Edge[]>(viewEdges);
  const nodesRef = useRef<Node[]>(viewNodes);
  const setNodes = useCallback((next: Node[]) => {
    nodesRef.current = next;
    setNodesState(next);
  }, []);
  useEffect(() => {
    const selected = new Set(nodesRef.current.filter((n) => n.selected).map((n) => n.id));
    setNodes(viewNodes.map((n) => (selected.has(n.id) ? { ...n, selected: true } : n)));
  }, [viewNodes, setNodes]);
  useEffect(() => {
    setEdges((prev) => {
      const selected = new Set(prev.filter((e) => e.selected).map((e) => e.id));
      return viewEdges.map((e) => (selected.has(e.id) ? { ...e, selected: true } : e));
    });
  }, [viewEdges]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      const next = applyNodeChanges(changes, nodesRef.current);
      setNodes(next);

      // Cluster view is view-only: computed positions must never persist
      if (useStudio2UI.getState().groupBy !== 'none') return;

      const state = useDocumentStore.getState();
      if (!state.doc) return;
      const doc = state.doc;

      const deviceMoves: { id: string; position: { x: number; y: number } }[] = [];
      for (const change of changes) {
        if (change.type !== 'position' || !change.position || change.dragging !== false) continue;

        const device = doc.devices[change.id];
        if (device) {
          // Child positions are relative to their zone — convert to absolute
          const node = next.find((n) => n.id === change.id);
          const parentZone = node?.parentId ? doc.zones[node.parentId] : undefined;
          const abs = parentZone
            ? {
                x: (parentZone.position?.x ?? 0) + change.position.x,
                y: (parentZone.position?.y ?? 0) + change.position.y,
              }
            : change.position;

          // Zone membership follows the node's center point
          const w = node?.measured?.width ?? 180;
          const h = node?.measured?.height ?? 56;
          const zoneAtDrop = findZoneAt(doc.zones, { x: abs.x + w / 2, y: abs.y + h / 2 });
          if ((zoneAtDrop?.id ?? undefined) !== device.zoneId) {
            const fresh = useDocumentStore.getState();
            if (!fresh.doc) continue;
            const cmd = commands.setDeviceZone(fresh.doc, change.id, zoneAtDrop?.id, abs);
            if (cmd) fresh.dispatch(cmd);
          } else {
            deviceMoves.push({ id: change.id, position: abs });
          }
          continue;
        }

        if (doc.zones[change.id]) {
          const fresh = useDocumentStore.getState();
          if (!fresh.doc) continue;
          const cmd = commands.moveZone(fresh.doc, change.id, change.position);
          if (cmd) fresh.dispatch(cmd);
        }
      }
      if (deviceMoves.length > 0) {
        const fresh = useDocumentStore.getState();
        if (fresh.doc) fresh.dispatch(commands.moveDevices(fresh.doc, deviceMoves));
      }
    },
    [setNodes],
  );

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    setEdges((eds) => applyEdgeChanges(changes, eds));
    const state = useDocumentStore.getState();
    if (!state.doc) return;
    const removedIds = changes
      .filter((c): c is Extract<EdgeChange, { type: 'remove' }> => c.type === 'remove')
      .map((c) => c.id);
    const removedFlows = removedIds.filter((id) => state.doc!.flows[id]);
    const removedConduits = removedIds.filter((id) => state.doc!.conduits[id]);
    if (removedFlows.length > 0) {
      state.dispatch(commands.deleteFlows(state.doc, removedFlows));
    }
    if (removedConduits.length > 0) {
      const fresh = useDocumentStore.getState();
      if (fresh.doc) fresh.dispatch(commands.deleteConduits(fresh.doc, removedConduits));
    }
  }, []);

  const onNodesDelete = useCallback((deleted: Node[]) => {
    const state = useDocumentStore.getState();
    if (!state.doc) return;
    const zoneIds = deleted.filter((n) => n.type === 'zone2').map((n) => n.id);
    const zoneIdSet = new Set(zoneIds);
    // React Flow deletes a parent's children with it — but deleting a zone
    // must NOT delete its member devices; they just leave the zone.
    const deviceIds = deleted
      .filter((n) => n.type === 'device2')
      .filter((n) => !(n.parentId && zoneIdSet.has(n.parentId)))
      .map((n) => n.id);
    if (deviceIds.length > 0) {
      state.dispatch(commands.deleteDevices(state.doc, deviceIds));
    }
    if (zoneIds.length > 0) {
      const fresh = useDocumentStore.getState();
      if (fresh.doc) fresh.dispatch(commands.deleteZones(fresh.doc, zoneIds));
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

  // Conduit tool: click zone A, then zone B. Selection stays untouched;
  // the tool disarms after a successful connect (Esc cancels midway).
  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (!conduitArmed || node.type !== 'zone2') return;
      const ui = useStudio2UI.getState();
      const sourceZoneId = ui.conduitSourceZoneId;
      if (!sourceZoneId) {
        ui.setConduitSourceZoneId(node.id);
        return;
      }
      if (sourceZoneId === node.id) {
        message.info('Pick a different zone for the other end');
        return;
      }
      const state = useDocumentStore.getState();
      if (!state.doc) return;
      const zoneA = state.doc.zones[sourceZoneId];
      const zoneB = state.doc.zones[node.id];
      if (!zoneA || !zoneB) {
        ui.setConduitSourceZoneId(null);
        return;
      }
      const existing = Object.values(state.doc.conduits).find(
        (c) =>
          (c.sourceZoneId === zoneA.id && c.targetZoneId === zoneB.id) ||
          (c.sourceZoneId === zoneB.id && c.targetZoneId === zoneA.id),
      );
      if (existing) {
        message.info(`Conduit already exists: ${existing.name}`);
      } else {
        state.dispatch(
          commands.addConduit({
            id: newId('conduit'),
            name: `${zoneA.name} ↔ ${zoneB.name}`,
            sourceZoneId: zoneA.id,
            targetZoneId: zoneB.id,
            direction: 'bidirectional',
            allowedProtocols: [],
          }),
        );
      }
      ui.setConduitArmed(false);
    },
    [conduitArmed],
  );

  // Double-click a cluster to expand/collapse it in place
  const onNodeDoubleClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      if (node.type !== 'cluster2' || !node.data) return;
      toggleCluster((node.data as ClusterNode2Data).clusterId);
      setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 50);
    },
    [toggleCluster, fitView],
  );

  // Consume focus requests from the Health panel: select + zoom to the
  // finding's elements.
  const focusRequest = useStudio2UI((s) => s.focusRequest);
  useEffect(() => {
    if (!focusRequest) return;
    useStudio2UI.getState().setFocusRequest(null);
    const nodeIdSet = new Set(focusRequest.nodeIds);
    const edgeIdSet = new Set(focusRequest.edgeIds);
    setNodes(nodesRef.current.map((n) => ({ ...n, selected: nodeIdSet.has(n.id) })));
    setEdges((eds) => eds.map((e) => ({ ...e, selected: edgeIdSet.has(e.id) })));
    useDocumentStore.getState().setSelection(focusRequest.nodeIds, focusRequest.edgeIds);
    if (focusRequest.nodeIds.length > 0) {
      fitView({
        nodes: focusRequest.nodeIds.map((id) => ({ id })),
        padding: 0.5,
        duration: 300,
        maxZoom: 1.2,
      });
    }
  }, [focusRequest, fitView, setNodes]);

  // Re-center when the grouping mode changes
  const prevGroupByRef = useRef(groupBy);
  useEffect(() => {
    if (prevGroupByRef.current !== groupBy) {
      prevGroupByRef.current = groupBy;
      setTimeout(() => fitView({ padding: 0.2, duration: 300 }), 60);
    }
  }, [groupBy, fitView]);

  const onPaneClick = useCallback(
    (event: React.MouseEvent) => {
      setPending(null);

      if (zoneArmed) {
        const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
        const state = useDocumentStore.getState();
        if (!state.doc) return;
        const names = new Set(Object.values(state.doc.zones).map((z) => z.name));
        let n = 1;
        while (names.has(`Zone ${n}`)) n++;
        state.dispatch(
          commands.addZone({
            id: newId('zone'),
            name: `Zone ${n}`,
            type: 'logical',
            position,
            dimensions: { width: 480, height: 320 },
            deviceIds: [],
          }),
        );
        if (!event.shiftKey) setZoneArmed(false);
        return;
      }

      if (!armedTemplate) return;
      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
      void placeDevice(armedTemplate, position);
      // Shift-click keeps the template armed for rapid placement
      if (!event.shiftKey) setArmedTemplate(null);
    },
    [armedTemplate, zoneArmed, screenToFlowPosition, setArmedTemplate, setZoneArmed],
  );

  const onSelectionChange = useCallback(
    ({ nodes: selNodes, edges: selEdges }: OnSelectionChangeParams) => {
      setSelection(
        selNodes.map((n) => n.id),
        selEdges.map((e) => e.id),
      );
    },
    [setSelection],
  );

  return (
    <div ref={wrapperRef} style={{ width: '100%', height: '100%', position: 'relative' }}>
      <style>{`
        .s2-node:hover .s2-handle, .s2-node .s2-handle.connectingto, .react-flow__node:hover .s2-handle { opacity: 1 !important; }
        .react-flow__pane { cursor: ${armedTemplate || zoneArmed || conduitArmed ? 'crosshair' : 'default'}; }
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
        onNodeClick={onNodeClick}
        onNodeDoubleClick={onNodeDoubleClick}
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
