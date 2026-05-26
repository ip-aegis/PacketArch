/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * MitreTechniquePanel — render the playbook's MITRE ATT&CK technique
 * coverage as a stage-by-stage grid. Two display modes:
 *
 *   - planned  (no report given): shows which techniques the playbook
 *     will exercise. Used in the AttackConfigurator pre-flight view.
 *   - actual   (report given):    highlights techniques that actually
 *     fired during the run, dims those that didn't. Used in the
 *     post-run after-action report.
 *
 * Most ICS ATT&CK tactic IDs (TA01xx, TA0043, etc.) are mapped to short
 * display names below — falls back to the raw ID if unknown.
 */

import React from 'react';
import { Card, Empty, Space, Tag, Tooltip, Typography } from 'antd';
import {
  CheckCircleTwoTone,
  MinusCircleOutlined,
} from '@ant-design/icons';
import type {
  ActionReport,
  AttackAction,
  AttackPlaybook,
  AttackReport,
  KillChainStage,
  StageReport,
} from '../../types/attackPlaybook';

const { Text } = Typography;

// MITRE tactic ID → short human-readable name. Covers ATT&CK for ICS
// (TA01xx) and Enterprise tactics referenced by the playbooks. Unknown
// IDs render as the raw ID.
const TACTIC_NAMES: Record<string, string> = {
  // ATT&CK for ICS
  TA0100: 'Initial Access',
  TA0101: 'Execution',
  TA0102: 'Persistence',
  TA0103: 'Privilege Escalation',
  TA0104: 'Evasion',
  TA0105: 'Discovery',
  TA0106: 'Lateral Movement',
  TA0107: 'Collection',
  TA0108: 'Command and Control',
  TA0109: 'Inhibit Response Function',
  TA0110: 'Impair Process Control',
  TA0111: 'Impact',
  // Enterprise tactics referenced by playbooks
  TA0001: 'Initial Access',
  TA0002: 'Execution',
  TA0003: 'Persistence',
  TA0004: 'Privilege Escalation',
  TA0005: 'Defense Evasion',
  TA0006: 'Credential Access',
  TA0007: 'Discovery',
  TA0008: 'Lateral Movement',
  TA0009: 'Collection',
  TA0010: 'Exfiltration',
  TA0011: 'Command and Control',
  TA0040: 'Impact',
  TA0042: 'Resource Development',
  TA0043: 'Reconnaissance',
};

function tacticLabel(id: string): string {
  return TACTIC_NAMES[id] || id;
}

/** Cross-walk: build a list of (stage, actions[]) entries. When a
 *  report is given, use the report's action records (which include
 *  per-action fire counts); otherwise use the playbook's static
 *  action list. */
interface StageRow {
  stageId: string;
  stageName: string;
  color: string;
  tactics: string[];
  actions: ActionRowInfo[];
}

interface ActionRowInfo {
  actionId: string;
  name: string;
  technique: string;
  description: string;
  expectedCv: string;
  /** Number of times this action fired during the run. 0 in planned mode. */
  fireCount: number;
  packets: number;
  targets: string[];
}

function buildRows(playbook: AttackPlaybook, report?: AttackReport): StageRow[] {
  // If we have a report, prefer its stage data (it carries fire counts).
  // Fall back to playbook stages for any field the report omits.
  if (report?.stages?.length) {
    return report.stages.map((s) => stageRowFromReport(s));
  }
  return playbook.stages.map((s) => stageRowFromPlaybook(s));
}

function stageRowFromReport(s: StageReport): StageRow {
  return {
    stageId: s.stage_id,
    stageName: s.stage_name,
    color: s.color,
    tactics: s.mitre_tactics || [],
    actions: (s.actions || []).map((a: ActionReport) => ({
      actionId: a.action_id,
      name: a.action_name,
      technique: a.mitre_technique,
      description: a.description,
      expectedCv: a.expected_cv_detection,
      fireCount: a.fire_count,
      packets: a.packets_emitted,
      targets: a.targets_hit || [],
    })),
  };
}

function stageRowFromPlaybook(s: KillChainStage): StageRow {
  return {
    stageId: s.stage_id,
    stageName: s.name,
    color: s.color,
    tactics: s.mitre_tactics || [],
    actions: s.actions.map((a: AttackAction) => ({
      actionId: a.action_id,
      name: a.name,
      technique: a.mitre_technique,
      description: a.description,
      expectedCv: a.expected_cv_detection,
      fireCount: 0,
      packets: 0,
      targets: [],
    })),
  };
}

export interface MitreTechniquePanelProps {
  playbook: AttackPlaybook;
  /** When provided, the panel renders in "actual" mode and highlights
   *  techniques that fired. When omitted, "planned" mode. */
  report?: AttackReport;
  title?: string;
}

const MitreTechniquePanel: React.FC<MitreTechniquePanelProps> = ({
  playbook,
  report,
  title,
}) => {
  const rows = buildRows(playbook, report);
  const actualMode = !!report;

  const allTechniques = new Set<string>();
  let firedTechniques = new Set<string>();
  rows.forEach((r) =>
    r.actions.forEach((a) => {
      if (a.technique) allTechniques.add(a.technique);
      if (a.fireCount > 0 && a.technique) firedTechniques.add(a.technique);
    }),
  );

  if (rows.length === 0 || allTechniques.size === 0) {
    return (
      <Card size="small" title={title || 'MITRE ATT&CK Coverage'}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Text type="secondary" style={{ fontSize: 12 }}>
              This playbook has no MITRE technique annotations.
            </Text>
          }
        />
      </Card>
    );
  }

  return (
    <Card
      size="small"
      title={
        <Space>
          <span>{title || 'MITRE ATT&CK Coverage'}</span>
          {actualMode ? (
            <Tag color="gold">
              {firedTechniques.size} / {allTechniques.size} techniques fired
            </Tag>
          ) : (
            <Tag color="blue">{allTechniques.size} techniques planned</Tag>
          )}
        </Space>
      }
      style={{ background: '#141428', border: '1px solid #2d2d52' }}
    >
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {rows.map((row) => (
          <div key={row.stageId} style={{ width: '100%' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                marginBottom: 6,
              }}
            >
              <span
                style={{
                  width: 8,
                  height: 8,
                  background: row.color,
                  borderRadius: 2,
                  display: 'inline-block',
                }}
              />
              <Text strong style={{ color: '#dde2ec' }}>
                {row.stageName}
              </Text>
              {row.tactics.map((t) => (
                <Tag key={t} color="purple" style={{ fontSize: 10 }}>
                  {tacticLabel(t)}
                  {TACTIC_NAMES[t] ? ` · ${t}` : ''}
                </Tag>
              ))}
            </div>
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 6,
                paddingLeft: 16,
              }}
            >
              {row.actions.map((a) => {
                const fired = a.fireCount > 0;
                const dim = actualMode && !fired;
                const tip = (
                  <div style={{ maxWidth: 320 }}>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>
                      {a.name}
                    </div>
                    {a.description && (
                      <div style={{ marginBottom: 4 }}>{a.description}</div>
                    )}
                    {a.expectedCv && (
                      <div style={{ marginBottom: 4 }}>
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          Expected CV detection:
                        </Text>{' '}
                        {a.expectedCv}
                      </div>
                    )}
                    {actualMode && (
                      <div style={{ fontSize: 11, color: '#8aa4bc' }}>
                        Fired {a.fireCount}×, {a.packets} packets, {a.targets.length} target(s)
                      </div>
                    )}
                  </div>
                );
                return (
                  <Tooltip key={a.actionId} title={tip}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '4px 10px',
                        border: `1px solid ${
                          fired ? '#52c41a' : dim ? '#3a3a5a' : '#5a8dee'
                        }`,
                        borderRadius: 4,
                        background: fired
                          ? '#52c41a14'
                          : dim
                          ? '#1a1a2e'
                          : '#5a8dee14',
                        opacity: dim ? 0.55 : 1,
                        fontSize: 12,
                        cursor: 'default',
                      }}
                    >
                      {actualMode ? (
                        fired ? (
                          <CheckCircleTwoTone twoToneColor="#52c41a" />
                        ) : (
                          <MinusCircleOutlined style={{ color: '#5b5b7d' }} />
                        )
                      ) : null}
                      <span
                        style={{
                          fontFamily: 'ui-monospace, monospace',
                          color: dim ? '#7e83a8' : '#dde2ec',
                        }}
                      >
                        {a.technique || '—'}
                      </span>
                      <span style={{ color: dim ? '#7e83a8' : '#a8a8c0' }}>
                        {a.name}
                      </span>
                      {actualMode && fired && a.packets > 0 && (
                        <Tag color="green" style={{ marginLeft: 4, fontSize: 10 }}>
                          {a.packets} pkt
                        </Tag>
                      )}
                    </div>
                  </Tooltip>
                );
              })}
            </div>
          </div>
        ))}
      </Space>
    </Card>
  );
};

export default MitreTechniquePanel;
