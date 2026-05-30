/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Live agent topology — one lane per agent showing how traffic flows from the
 * scenario through the agent into the capture path, live-colored from
 * /dashboard/live + /local-sensor/labs. Renders ALL agent kinds:
 *
 *   Local lab:  [Scenario] -> [Agent] -> [SPAN veth] -> [CV Sensor]
 *   CML lab:    [Scenario] -> [Agent] -> [CML SPAN]   -> [CV Sensor]  (augments CML)
 *   Manual:     [Scenario] -> [Agent]
 *
 * Nodes turn green when online/up; the inject edge animates when packets flow.
 * Uses plain styled default nodes (no custom node components) to stay clear of
 * xyflow v12 generic-typing friction.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { ReactFlow, Background, Controls, type Node, type Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Empty, Spin } from 'antd';
import { dashboardApi, type DashboardAgent } from '../../api/dashboard';
import { localSensorApi, type LocalLabItem } from '../../api/localSensor';
import { agentsApi } from '../../api/agents';
import type { TrafficAgent } from '../../types/agent';

const LANE_H = 150;
const COL = { scenario: 0, agent: 230, span: 470, sensor: 710 };

const GREEN = '#52c41a';
const GREY = '#6b6b8a';
const BLUE = '#1890ff';
const CYAN = '#13c2c2';

function nodeStyle(color: string, on: boolean): React.CSSProperties {
  return {
    background: '#1a1a2e',
    color: '#e6e6f0',
    border: `2px solid ${on ? color : GREY}`,
    borderRadius: 8,
    fontSize: 12,
    width: 180,
    whiteSpace: 'pre-line',
    boxShadow: on ? `0 0 10px ${color}55` : 'none',
  };
}

const labelStyle = { fill: '#e6e6f0', fontSize: 10 };

interface Combined {
  agent: TrafficAgent;
  live?: DashboardAgent;
  lab?: LocalLabItem;
}

const AgentTopology: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState<Combined[]>([]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [agentsResp, live, labsResp] = await Promise.all([
          agentsApi.list(1, 100).catch(() => ({ agents: [] as TrafficAgent[] })),
          dashboardApi.getLive().catch(() => null),
          localSensorApi.getLabs().catch(() => ({ items: [] as LocalLabItem[] })),
        ]);
        if (cancelled) return;
        const liveById = new Map<string, DashboardAgent>(
          (live?.agents || []).map((a) => [a.agent_id, a]),
        );
        const labByAgent = new Map<string, LocalLabItem>(
          labsResp.items.filter((l) => l.agent_id).map((l) => [l.agent_id as string, l]),
        );
        const combined = (agentsResp as { agents: TrafficAgent[] }).agents.map((agent) => ({
          agent,
          live: liveById.get(agent.id),
          lab: labByAgent.get(agent.id),
        }));
        setRows(combined);
        setLoading(false);
      } catch {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    const t = setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  const { nodes, edges } = useMemo(() => {
    const ns: Node[] = [];
    const es: Edge[] = [];
    rows.forEach((row, i) => {
      const y = i * LANE_H;
      const online = row.live?.is_online ?? row.agent.status === 'online';
      const flowing = online && (row.live?.active_deployments ?? 0) > 0;
      const pps = row.live?.total_packets_per_second ?? 0;
      const kind = row.agent.local_lab_id ? 'Local' : row.agent.cml_lab_id ? 'CML' : 'Manual';
      const aId = row.agent.id;

      if (flowing) {
        ns.push({
          id: `scn-${aId}`, position: { x: COL.scenario, y },
          data: { label: '> Scenario running' },
          style: nodeStyle(BLUE, true), selectable: false,
        });
      }

      ns.push({
        id: `agt-${aId}`, position: { x: COL.agent, y },
        data: { label: `${row.agent.name}\n[${kind}] ${online ? 'online' : 'offline'}` },
        style: nodeStyle(online ? GREEN : GREY, online), selectable: false,
      });

      if (flowing) {
        es.push({
          id: `e-scn-${aId}`, source: `scn-${aId}`, target: `agt-${aId}`,
          animated: true, label: pps ? `${Math.round(pps)} pps` : undefined,
          style: { stroke: BLUE }, labelStyle,
        });
      }

      if (kind === 'Local' && row.lab) {
        const res = row.lab.resources || {};
        const vethUp = !!res.veth;
        const sensorUp = !!res.sensor_running;
        ns.push({
          id: `span-${aId}`, position: { x: COL.span, y },
          data: { label: `SPAN veth\n${row.lab.gen_if} <-> ${row.lab.mon_if}` },
          style: nodeStyle(CYAN, vethUp), selectable: false,
        });
        ns.push({
          id: `sns-${aId}`, position: { x: COL.sensor, y },
          data: { label: `CV Sensor\n${row.lab.sensor_serial || ''}` },
          style: nodeStyle(GREEN, sensorUp), selectable: false,
        });
        es.push({
          id: `e-agt-span-${aId}`, source: `agt-${aId}`, target: `span-${aId}`,
          animated: flowing, label: 'inject', style: { stroke: vethUp ? CYAN : GREY }, labelStyle,
        });
        es.push({
          id: `e-span-sns-${aId}`, source: `span-${aId}`, target: `sns-${aId}`,
          animated: flowing, label: 'capture', style: { stroke: sensorUp ? GREEN : GREY }, labelStyle,
        });
      } else if (kind === 'CML') {
        ns.push({
          id: `span-${aId}`, position: { x: COL.span, y },
          data: { label: 'CML SPAN switch' },
          style: nodeStyle(CYAN, online), selectable: false,
        });
        ns.push({
          id: `sns-${aId}`, position: { x: COL.sensor, y },
          data: { label: 'CV Sensor (in lab)' },
          style: nodeStyle(GREEN, online), selectable: false,
        });
        es.push({
          id: `e-agt-span-${aId}`, source: `agt-${aId}`, target: `span-${aId}`,
          animated: flowing, label: 'inject', style: { stroke: online ? CYAN : GREY }, labelStyle,
        });
        es.push({
          id: `e-span-sns-${aId}`, source: `span-${aId}`, target: `sns-${aId}`,
          animated: flowing, label: 'SPAN', style: { stroke: online ? GREEN : GREY }, labelStyle,
        });
      }
    });
    return { nodes: ns, edges: es };
  }, [rows]);

  if (loading) {
    return <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>;
  }
  if (rows.length === 0) {
    return <Empty description="No agents yet" style={{ padding: 48 }} />;
  }

  return (
    <div style={{ height: Math.max(360, rows.length * LANE_H + 80), background: '#141428', borderRadius: 8 }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#2d2d52" gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
};

export default AgentTopology;
