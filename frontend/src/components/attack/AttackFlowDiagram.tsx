/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * AttackFlowDiagram — pure-SVG attacker→targets visualization.
 *
 * A single attacker node on the left, target nodes fanned out to the
 * right (one per unique target IP that received attack traffic). Edge
 * thickness is proportional to estimated packet volume; edge color
 * comes from the action's stage colour so the visual ties back to the
 * kill-chain timeline.
 *
 * Lives in the report modal alongside `AttackIpMatrix` — the table
 * answers "what flows occurred," the diagram answers "what's the shape
 * of the attack."
 *
 * No external graph libraries — the data is small (~5–30 targets) and
 * hand-rolling SVG keeps the bundle lean. If we ever need force-direct
 * layout, swap to react-flow at that point.
 */

import React, { useMemo } from 'react';
import { Card, Empty, Space, Tag, Typography } from 'antd';
import { NodeIndexOutlined } from '@ant-design/icons';
import type { AttackReport } from '../../types/attackPlaybook';

const { Text } = Typography;

interface TargetNode {
  ip: string;
  totalPackets: number;
  protocols: string[];
  stageColor: string; // colour of most-recent stage that hit this target
}

interface EdgeData {
  targetIp: string;
  packets: number;
  color: string;
  actionTypes: string[];
}

function buildGraph(report: AttackReport): {
  attackerIp: string;
  targets: TargetNode[];
  edges: EdgeData[];
} {
  const targetMap = new Map<string, TargetNode>();
  const edgeMap = new Map<string, EdgeData>();
  const fallbackAttacker = report.attacker_ip || '203.0.113.1';
  let attackerIp = fallbackAttacker;

  for (const stage of report.stages) {
    for (const action of stage.actions) {
      if (action.fire_count === 0) continue;
      const aIp = (action.iocs?.attacker_ip as string | undefined) || fallbackAttacker;
      attackerIp = aIp;
      const targets = (action.iocs?.target_ips as string[] | undefined) || [];
      if (targets.length === 0) continue;

      const per = action.packets_emitted / targets.length;
      for (const t of targets) {
        const node = targetMap.get(t);
        if (node) {
          node.totalPackets += per;
          node.stageColor = stage.color;
          if (action.action_type && !node.protocols.includes(action.action_type)) {
            node.protocols.push(action.action_type);
          }
        } else {
          targetMap.set(t, {
            ip: t,
            totalPackets: per,
            protocols: action.action_type ? [action.action_type] : [],
            stageColor: stage.color,
          });
        }
        const edgeKey = `${t}|${stage.color}`;
        const edge = edgeMap.get(edgeKey);
        if (edge) {
          edge.packets += per;
          if (action.action_type && !edge.actionTypes.includes(action.action_type)) {
            edge.actionTypes.push(action.action_type);
          }
        } else {
          edgeMap.set(edgeKey, {
            targetIp: t,
            packets: per,
            color: stage.color,
            actionTypes: action.action_type ? [action.action_type] : [],
          });
        }
      }
    }
  }
  return {
    attackerIp,
    targets: Array.from(targetMap.values()).sort(
      (a, b) => b.totalPackets - a.totalPackets,
    ),
    edges: Array.from(edgeMap.values()),
  };
}

function strokeWidthForPackets(packets: number, max: number): number {
  if (max === 0) return 1;
  const ratio = packets / max;
  return 1 + ratio * 5; // 1..6 px
}

export interface AttackFlowDiagramProps {
  report: AttackReport;
  title?: string;
}

const AttackFlowDiagram: React.FC<AttackFlowDiagramProps> = ({ report, title }) => {
  const graph = useMemo(() => buildGraph(report), [report]);

  if (graph.targets.length === 0) {
    return (
      <Card
        size="small"
        title={title || 'Attack flow diagram'}
        style={{ background: '#141428', border: '1px solid #2d2d52' }}
      >
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Text type="secondary" style={{ fontSize: 12 }}>
              No targeted traffic yet.
            </Text>
          }
        />
      </Card>
    );
  }

  // Lay out: attacker at left (x=80), targets in a vertical column on
  // the right (x=620). Stack count adjusts height.
  const maxPackets = Math.max(...graph.targets.map((t) => t.totalPackets));
  const rowHeight = 38;
  const minHeight = 180;
  const height = Math.max(minHeight, graph.targets.length * rowHeight + 40);
  const attackerX = 80;
  const targetX = 620;
  const attackerY = height / 2;

  return (
    <Card
      size="small"
      title={
        <Space>
          <NodeIndexOutlined />
          <span>{title || 'Attack flow diagram'}</span>
          <Tag color="red" style={{ fontSize: 10 }}>
            {graph.targets.length} target{graph.targets.length === 1 ? '' : 's'}
          </Tag>
        </Space>
      }
      style={{ background: '#141428', border: '1px solid #2d2d52' }}
      bodyStyle={{ padding: 12, overflowX: 'auto' }}
    >
      <svg
        width={760}
        height={height}
        viewBox={`0 0 760 ${height}`}
        style={{ display: 'block' }}
      >
        <defs>
          {/* Arrowhead for edges. Stroked + filled with the edge colour
              via currentColor so each edge picks up its own hue. */}
          <marker
            id="attack-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" />
          </marker>
          {/* Glow filter for the attacker node so it stands out. */}
          <filter id="attack-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Edges first so nodes overlay them */}
        {graph.targets.map((target, i) => {
          const targetY = 20 + i * rowHeight + rowHeight / 2;
          // Edges per target — group by stage colour
          const edgesForTarget = graph.edges.filter((e) => e.targetIp === target.ip);
          return edgesForTarget.map((e, j) => {
            const width = strokeWidthForPackets(e.packets, maxPackets);
            // Slight curve so multiple edges to the same target don't overlap
            const ctrlX = (attackerX + targetX) / 2;
            const ctrlY = attackerY + (targetY - attackerY) * 0.5 + (j - edgesForTarget.length / 2) * 6;
            return (
              <g key={`${target.ip}-${j}`} style={{ color: e.color }}>
                <title>
                  {`${graph.attackerIp} → ${target.ip}  ·  ~${Math.round(e.packets)} packets  ·  ${e.actionTypes.join(', ')}`}
                </title>
                <path
                  d={`M ${attackerX + 14} ${attackerY} Q ${ctrlX} ${ctrlY} ${targetX - 14} ${targetY}`}
                  stroke={e.color}
                  strokeWidth={width}
                  strokeOpacity={0.75}
                  fill="none"
                  markerEnd="url(#attack-arrow)"
                />
              </g>
            );
          });
        })}

        {/* Attacker node */}
        <g filter="url(#attack-glow)">
          <circle cx={attackerX} cy={attackerY} r={22} fill="#5c2223" stroke="#ff4d4f" strokeWidth={2} />
          <text
            x={attackerX}
            y={attackerY - 28}
            textAnchor="middle"
            fill="#ffa39e"
            fontSize={11}
            fontWeight={600}
          >
            ATTACKER
          </text>
          <text
            x={attackerX}
            y={attackerY + 4}
            textAnchor="middle"
            fill="#fff"
            fontSize={11}
            fontFamily="ui-monospace, monospace"
          >
            ⚡
          </text>
          <text
            x={attackerX}
            y={attackerY + 40}
            textAnchor="middle"
            fill="#ff7875"
            fontSize={11}
            fontFamily="ui-monospace, monospace"
          >
            {graph.attackerIp}
          </text>
        </g>

        {/* Target nodes */}
        {graph.targets.map((target, i) => {
          const targetY = 20 + i * rowHeight + rowHeight / 2;
          const radius = 10 + Math.min(8, (target.totalPackets / maxPackets) * 8);
          return (
            <g key={target.ip}>
              <title>
                {`${target.ip}  ·  ~${Math.round(target.totalPackets)} packets received  ·  actions: ${target.protocols.join(', ')}`}
              </title>
              <circle
                cx={targetX}
                cy={targetY}
                r={radius}
                fill={`${target.stageColor}33`}
                stroke={target.stageColor}
                strokeWidth={2}
              />
              <text
                x={targetX + 16}
                y={targetY - 2}
                fill="#dde2ec"
                fontSize={11}
                fontFamily="ui-monospace, monospace"
              >
                {target.ip}
              </text>
              <text
                x={targetX + 16}
                y={targetY + 12}
                fill="#8aa4bc"
                fontSize={10}
              >
                ~{Math.round(target.totalPackets)} pkts · {target.protocols.length}{' '}
                action{target.protocols.length === 1 ? '' : 's'}
              </text>
            </g>
          );
        })}
      </svg>
    </Card>
  );
};

export default AttackFlowDiagram;
