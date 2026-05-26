/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * AttackIpMatrix — live netflow-style view of attacker→target IP pairs
 * derived from the orchestrator's per-action IOC data.
 *
 * For each (attacker_ip, target_ip, action_type) tuple the matrix
 * tracks: cumulative packets, MITRE technique(s), action name(s),
 * stage colour, and most-recent fire time. Sorted by recency by
 * default so the active conversations bubble to the top.
 *
 * Two display sizes:
 *   - `compact` — for the sidebar; top N rows, condensed columns.
 *   - `full`    — for the report modal; full table, all rows, sortable.
 *
 * The component derives everything from the report — no extra backend
 * calls. It works equally for live-state reports (rolling) and for
 * persisted history reports (frozen).
 */

import React, { useMemo } from 'react';
import { Card, Empty, Space, Table, Tag, Tooltip, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { ApiOutlined, AppstoreOutlined, FireOutlined } from '@ant-design/icons';
import type { AttackReport } from '../../types/attackPlaybook';

const { Text } = Typography;

interface AttackIpFlow {
  key: string;
  attackerIp: string;
  targetIp: string;
  actionType: string;
  actionNames: string[];
  techniques: string[];
  stageName: string;
  stageColor: string;
  packetsEstimated: number;
  lastFiredAt: number;
}

/** Bucket the report's per-action IOC records into (attacker, target,
 *  action_type) flows. Packets per row are an estimate because the
 *  orchestrator records packets per action — when an action fans out
 *  to N targets we attribute packets_emitted/N to each row. Good
 *  enough for "which target took the brunt." */
function buildIpFlows(report: AttackReport): AttackIpFlow[] {
  const flows = new Map<string, AttackIpFlow>();
  const fallbackAttacker = report.attacker_ip || '';

  for (const stage of report.stages) {
    for (const action of stage.actions) {
      if (action.fire_count === 0) continue;
      const attackerIp =
        (action.iocs?.attacker_ip as string | undefined) || fallbackAttacker;
      const rawTargets = action.iocs?.target_ips;
      const targetIps: string[] = Array.isArray(rawTargets)
        ? (rawTargets as string[])
        : [];
      if (targetIps.length === 0) continue;

      const packetsPerTarget = action.packets_emitted / targetIps.length;

      for (const targetIp of targetIps) {
        const key = `${attackerIp}|${targetIp}|${action.action_type}`;
        const existing = flows.get(key);
        if (existing) {
          existing.packetsEstimated += packetsPerTarget;
          existing.lastFiredAt = Math.max(existing.lastFiredAt, action.fired_at);
          if (
            action.mitre_technique &&
            !existing.techniques.includes(action.mitre_technique)
          ) {
            existing.techniques.push(action.mitre_technique);
          }
          if (!existing.actionNames.includes(action.action_name)) {
            existing.actionNames.push(action.action_name);
          }
        } else {
          flows.set(key, {
            key,
            attackerIp,
            targetIp,
            actionType: action.action_type,
            actionNames: [action.action_name],
            techniques: action.mitre_technique ? [action.mitre_technique] : [],
            stageName: stage.stage_name,
            stageColor: stage.color,
            packetsEstimated: packetsPerTarget,
            lastFiredAt: action.fired_at,
          });
        }
      }
    }
  }
  return Array.from(flows.values()).sort((a, b) => b.lastFiredAt - a.lastFiredAt);
}

/** Pretty-print a protocol/action-type label. Strips the verb prefix
 *  (e.g. `modbus_coil_flood` → "Modbus · coil flood") so the matrix
 *  reads cleanly. */
function formatActionType(actionType: string): string {
  if (!actionType) return '—';
  const parts = actionType.split('_');
  if (parts.length === 1) return parts[0];
  const head = parts[0];
  const tail = parts.slice(1).join(' ');
  return `${head} · ${tail}`;
}

function packetIntensity(packets: number): {
  bar: number;
  color: string;
} {
  // Buckets: light orange / orange / red / dark red. Pure rate-of-fire
  // hint, not a quantitative scale.
  if (packets < 10) return { bar: 0.15, color: '#fa8c16' };
  if (packets < 100) return { bar: 0.35, color: '#ff7a45' };
  if (packets < 500) return { bar: 0.6, color: '#ff4d4f' };
  if (packets < 2000) return { bar: 0.85, color: '#cf1322' };
  return { bar: 1.0, color: '#820014' };
}

function secondsAgo(epochSeconds: number): string {
  if (!epochSeconds) return '—';
  const delta = Date.now() / 1000 - epochSeconds;
  if (delta < 1) return 'now';
  if (delta < 60) return `${Math.round(delta)}s ago`;
  if (delta < 3600) return `${Math.round(delta / 60)}m ago`;
  return `${Math.round(delta / 3600)}h ago`;
}

export interface AttackIpMatrixProps {
  report: AttackReport;
  variant?: 'compact' | 'full';
  /** Max rows in compact mode. Default 5. */
  maxRows?: number;
  title?: string;
}

const AttackIpMatrix: React.FC<AttackIpMatrixProps> = ({
  report,
  variant = 'full',
  maxRows = 5,
  title,
}) => {
  const flows = useMemo(() => buildIpFlows(report), [report]);

  if (flows.length === 0) {
    return variant === 'compact' ? null : (
      <Card
        size="small"
        title={title || 'Attack IP matrix'}
        style={{ background: '#141428', border: '1px solid #2d2d52' }}
      >
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Text type="secondary" style={{ fontSize: 12 }}>
              No IP flow data yet. Flows appear as attack actions fire and
              record targets.
            </Text>
          }
        />
      </Card>
    );
  }

  const rows = variant === 'compact' ? flows.slice(0, maxRows) : flows;
  const totalPackets = flows.reduce((sum, f) => sum + f.packetsEstimated, 0);
  const uniqueTargets = new Set(flows.map((f) => f.targetIp)).size;

  if (variant === 'compact') {
    return (
      <div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 3,
          }}
        >
          <Text
            style={{
              color: '#8aa4bc',
              fontSize: 9,
              textTransform: 'uppercase',
              letterSpacing: 0.4,
            }}
          >
            Live IP attack matrix
          </Text>
          <Text style={{ color: '#6a8caf', fontSize: 9 }}>
            {flows.length} pair{flows.length === 1 ? '' : 's'} · {uniqueTargets} target
            {uniqueTargets === 1 ? '' : 's'} · ~{Math.round(totalPackets)} pkts
          </Text>
        </div>
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
            maxHeight: 130,
            overflowY: 'auto',
          }}
        >
          {rows.map((f) => {
            const intensity = packetIntensity(f.packetsEstimated);
            return (
              <Tooltip
                key={f.key}
                title={
                  <div style={{ maxWidth: 280, fontSize: 11 }}>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>
                      {f.actionNames.join(', ')}
                    </div>
                    <div style={{ marginBottom: 2 }}>
                      <code>{f.attackerIp}</code> →{' '}
                      <code>{f.targetIp}</code>
                    </div>
                    <div style={{ color: '#a8a8c0' }}>
                      Stage: {f.stageName} · Last fired {secondsAgo(f.lastFiredAt)}
                    </div>
                    {f.techniques.length > 0 && (
                      <div style={{ marginTop: 4 }}>
                        Techniques: {f.techniques.join(', ')}
                      </div>
                    )}
                  </div>
                }
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '2px 6px',
                    background: '#0d1117',
                    borderRadius: 3,
                    borderLeft: `2px solid ${f.stageColor}`,
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                >
                  {/* Intensity bar — bleeds behind the row. */}
                  <div
                    style={{
                      position: 'absolute',
                      left: 0,
                      top: 0,
                      bottom: 0,
                      width: `${intensity.bar * 100}%`,
                      background: intensity.color,
                      opacity: 0.12,
                      transition: 'width 0.5s ease',
                    }}
                  />
                  <code
                    style={{
                      color: '#ff7875',
                      fontSize: 10,
                      flexShrink: 0,
                      fontFamily: 'ui-monospace, monospace',
                    }}
                  >
                    {f.attackerIp}
                  </code>
                  <span style={{ color: '#5a6b7e', fontSize: 10 }}>→</span>
                  <code
                    style={{
                      color: '#dde2ec',
                      fontSize: 10,
                      flex: 1,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      fontFamily: 'ui-monospace, monospace',
                    }}
                  >
                    {f.targetIp}
                  </code>
                  <Text
                    style={{
                      color: '#a8a8c0',
                      fontSize: 9,
                      flexShrink: 0,
                      maxWidth: 60,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {formatActionType(f.actionType)}
                  </Text>
                  <Text
                    style={{
                      color: intensity.color,
                      fontSize: 10,
                      fontWeight: 600,
                      minWidth: 36,
                      textAlign: 'right',
                      flexShrink: 0,
                      fontFamily: 'ui-monospace, monospace',
                    }}
                  >
                    {Math.round(f.packetsEstimated)}p
                  </Text>
                </div>
              </Tooltip>
            );
          })}
        </div>
        {flows.length > maxRows && (
          <Text style={{ color: '#5a6b7e', fontSize: 9, marginTop: 2, display: 'block' }}>
            + {flows.length - maxRows} more pair{flows.length - maxRows === 1 ? '' : 's'} —
            open the full report for the complete matrix
          </Text>
        )}
      </div>
    );
  }

  // Full-table variant (for the report modal)
  const columns: ColumnsType<AttackIpFlow> = [
    {
      title: 'Attacker',
      dataIndex: 'attackerIp',
      key: 'attackerIp',
      width: 130,
      render: (ip: string) => (
        <code style={{ color: '#ff7875', fontFamily: 'ui-monospace, monospace' }}>{ip}</code>
      ),
    },
    {
      title: '',
      key: 'arrow',
      width: 24,
      render: () => <span style={{ color: '#5a6b7e' }}>→</span>,
    },
    {
      title: 'Target',
      dataIndex: 'targetIp',
      key: 'targetIp',
      width: 130,
      render: (ip: string) => (
        <code style={{ color: '#dde2ec', fontFamily: 'ui-monospace, monospace' }}>{ip}</code>
      ),
    },
    {
      title: 'Action / protocol',
      dataIndex: 'actionType',
      key: 'actionType',
      render: (actionType: string, row) => (
        <Space size={4} wrap>
          <Text style={{ color: '#dde2ec', fontSize: 12 }}>
            {formatActionType(actionType)}
          </Text>
          {row.actionNames.slice(0, 2).map((n) => (
            <Tag key={n} style={{ fontSize: 10, margin: 0 }}>
              {n}
            </Tag>
          ))}
          {row.actionNames.length > 2 && (
            <Tag style={{ fontSize: 10 }}>+{row.actionNames.length - 2}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'MITRE',
      dataIndex: 'techniques',
      key: 'techniques',
      width: 120,
      render: (techniques: string[]) =>
        techniques.length === 0 ? (
          <Text type="secondary">—</Text>
        ) : (
          <Space size={2} wrap>
            {techniques.map((t) => (
              <Tag color="blue" key={t} style={{ fontSize: 10, margin: 0 }}>
                {t}
              </Tag>
            ))}
          </Space>
        ),
    },
    {
      title: 'Stage',
      dataIndex: 'stageName',
      key: 'stageName',
      width: 140,
      render: (stageName: string, row) => (
        <Space size={4}>
          <span
            style={{
              width: 8,
              height: 8,
              background: row.stageColor,
              borderRadius: 2,
              display: 'inline-block',
            }}
          />
          <Text style={{ color: '#a8a8c0', fontSize: 12 }}>{stageName}</Text>
        </Space>
      ),
    },
    {
      title: 'Packets',
      dataIndex: 'packetsEstimated',
      key: 'packetsEstimated',
      width: 90,
      sorter: (a, b) => a.packetsEstimated - b.packetsEstimated,
      defaultSortOrder: 'descend',
      render: (n: number) => {
        const intensity = packetIntensity(n);
        return (
          <Text
            style={{
              color: intensity.color,
              fontWeight: 600,
              fontFamily: 'ui-monospace, monospace',
            }}
          >
            ~{Math.round(n)}
          </Text>
        );
      },
    },
    {
      title: 'Last',
      dataIndex: 'lastFiredAt',
      key: 'lastFiredAt',
      width: 80,
      sorter: (a, b) => a.lastFiredAt - b.lastFiredAt,
      render: (t: number) => (
        <Text type="secondary" style={{ fontSize: 11 }}>
          {secondsAgo(t)}
        </Text>
      ),
    },
  ];

  return (
    <Card
      size="small"
      title={
        <Space>
          <ApiOutlined />
          <span>{title || 'Attack IP matrix'}</span>
          <Tag color="red" style={{ fontSize: 10 }}>
            <FireOutlined /> {Math.round(totalPackets)} pkts
          </Tag>
          <Tag style={{ fontSize: 10 }}>
            <AppstoreOutlined /> {flows.length} flow{flows.length === 1 ? '' : 's'}
          </Tag>
          <Tag style={{ fontSize: 10 }}>{uniqueTargets} target{uniqueTargets === 1 ? '' : 's'}</Tag>
        </Space>
      }
      style={{ background: '#141428', border: '1px solid #2d2d52' }}
    >
      <Table
        size="small"
        rowKey="key"
        columns={columns}
        dataSource={rows}
        pagination={false}
        scroll={{ y: 360 }}
      />
    </Card>
  );
};

export default AttackIpMatrix;
