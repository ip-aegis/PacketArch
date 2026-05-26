/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * AttackReportPanel — after-action report for a completed (or stopped)
 * playbook run. Renders three views:
 *
 *   1. Header card with totals + status + duration
 *   2. Stage-by-stage breakdown with planned vs actual timing and
 *      per-action telemetry (packets emitted, targets hit, IOCs)
 *   3. MITRE technique coverage panel (delegates to MitreTechniquePanel
 *      in "actual" mode so techniques that fired light up green)
 *
 * Includes a "Download JSON" button so the operator can hand the full
 * report off to a SIEM / training material / runbook.
 */

import React from 'react';
import {
  Alert,
  Button,
  Card,
  Collapse,
  Empty,
  Space,
  Statistic,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  CheckCircleTwoTone,
  ClockCircleOutlined,
  CloseCircleOutlined,
  DownloadOutlined,
  ExperimentOutlined,
  FireOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  WarningTwoTone,
} from '@ant-design/icons';
import type {
  AttackPlaybook,
  AttackReport,
  StageReport,
} from '../../types/attackPlaybook';
import AttackFlowDiagram from './AttackFlowDiagram';
import AttackIpMatrix from './AttackIpMatrix';
import MitreTechniquePanel from './MitreTechniquePanel';

const { Text } = Typography;

const severityColors: Record<string, string> = {
  critical: '#ff4d4f',
  high: '#fa8c16',
  medium: '#faad14',
  low: '#52c41a',
};

function formatDuration(seconds: number): string {
  if (!seconds || seconds < 0) return '—';
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  if (seconds < 3600) {
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return s > 0 ? `${m}m ${s}s` : `${m}m`;
  }
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function formatTimestamp(epoch: number | null): string {
  if (!epoch) return '—';
  try {
    return new Date(epoch * 1000).toLocaleString();
  } catch {
    return '—';
  }
}

function statusBadge(status: AttackReport['status']) {
  switch (status) {
    case 'completed':
      return (
        <Tag color="success" icon={<CheckCircleTwoTone twoToneColor="#52c41a" />}>
          Completed
        </Tag>
      );
    case 'stopped':
      return (
        <Tag color="warning" icon={<WarningTwoTone twoToneColor="#faad14" />}>
          Stopped early
        </Tag>
      );
    case 'failed':
      return (
        <Tag color="error" icon={<CloseCircleOutlined />}>
          Failed
        </Tag>
      );
    default:
      return (
        <Tag color="processing" icon={<ClockCircleOutlined />}>
          In progress
        </Tag>
      );
  }
}

function downloadReport(report: AttackReport): void {
  const blob = new Blob([JSON.stringify(report, null, 2)], {
    type: 'application/json',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  const start = new Date((report.started_at || 0) * 1000)
    .toISOString()
    .replace(/[:.]/g, '-');
  link.download = `attack-report-${report.playbook_id}-${start}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function StageBlock({ stage }: { stage: StageReport }): React.ReactElement {
  const firedActions = stage.actions.filter((a) => a.fire_count > 0);
  const skippedActions = stage.actions.filter((a) => a.fire_count === 0);
  const wallTimeOverrun =
    stage.actual_duration_s > stage.planned_duration_s + 1;
  const wallTimeShort =
    stage.status === 'completed' &&
    stage.actual_duration_s < stage.planned_duration_s - 1;

  return (
    <Card
      size="small"
      style={{
        background: '#141428',
        border: `1px solid ${
          stage.status === 'completed' ? '#2d4a2d' : '#2d2d52'
        }`,
        marginBottom: 8,
      }}
      title={
        <Space>
          <span
            style={{
              width: 8,
              height: 8,
              background: stage.color,
              borderRadius: 2,
              display: 'inline-block',
            }}
          />
          <Text strong style={{ color: '#dde2ec' }}>
            {stage.stage_name}
          </Text>
          {stage.status === 'completed' && (
            <Tag color="success">completed</Tag>
          )}
          {stage.status === 'in_progress' && (
            <Tag color="processing">in progress</Tag>
          )}
          {stage.status === 'skipped' && <Tag color="default">skipped</Tag>}
          {stage.status === 'pending' && <Tag color="default">never ran</Tag>}
        </Space>
      }
    >
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Space size={24} wrap>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Planned: <strong>{formatDuration(stage.planned_duration_s)}</strong>
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Actual: <strong>{formatDuration(stage.actual_duration_s)}</strong>{' '}
            {wallTimeOverrun && (
              <Tag color="orange" style={{ marginLeft: 4 }}>
                ran long
              </Tag>
            )}
            {wallTimeShort && (
              <Tag color="blue" style={{ marginLeft: 4 }}>
                ended early
              </Tag>
            )}
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Packets: <strong>{stage.packets_emitted}</strong>
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Actions fired: <strong>{firedActions.length}</strong> of{' '}
            {stage.actions.length}
          </Text>
        </Space>

        {stage.expected_cv_alerts.length > 0 && (
          <Alert
            type="info"
            showIcon
            style={{ padding: '4px 10px', fontSize: 12 }}
            message={
              <span>
                <SafetyCertificateOutlined style={{ marginRight: 6 }} />
                CV should have alerted on:&nbsp;
                {stage.expected_cv_alerts.join('; ')}
              </span>
            }
          />
        )}

        {firedActions.length > 0 ? (
          <div>
            <Text strong style={{ fontSize: 12, color: '#a8a8c0' }}>
              What ran ({firedActions.length}):
            </Text>
            <Space direction="vertical" size={4} style={{ width: '100%', marginTop: 4 }}>
              {firedActions.map((a) => (
                <div
                  key={a.action_id}
                  style={{
                    padding: '6px 10px',
                    background: '#1a1a2e',
                    border: '1px solid #2d2d52',
                    borderRadius: 4,
                  }}
                >
                  <Space wrap size={8}>
                    <Text strong style={{ color: '#dde2ec', fontSize: 12 }}>
                      {a.action_name}
                    </Text>
                    {a.mitre_technique && (
                      <Tag color="blue" style={{ fontSize: 10 }}>
                        {a.mitre_technique}
                      </Tag>
                    )}
                    <Tag color="green" style={{ fontSize: 10 }}>
                      ×{a.fire_count}
                    </Tag>
                    <Tag color="cyan" style={{ fontSize: 10 }}>
                      {a.packets_emitted} pkts
                    </Tag>
                    <Tag style={{ fontSize: 10 }}>
                      {a.targets_hit.length} target(s)
                    </Tag>
                  </Space>
                  {Object.keys(a.iocs || {}).length > 0 && (
                    <details style={{ marginTop: 6 }}>
                      <summary style={{ cursor: 'pointer', fontSize: 11, color: '#8aa4bc' }}>
                        IOCs ({Object.keys(a.iocs).length})
                      </summary>
                      <pre
                        style={{
                          fontSize: 11,
                          background: '#0e0e1f',
                          padding: 6,
                          margin: '4px 0 0',
                          borderRadius: 3,
                          color: '#a8a8c0',
                          maxHeight: 200,
                          overflow: 'auto',
                        }}
                      >
                        {JSON.stringify(a.iocs, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
            </Space>
          </div>
        ) : (
          stage.status !== 'pending' && (
            <Text type="secondary" style={{ fontSize: 12, fontStyle: 'italic' }}>
              No actions fired in this stage.
            </Text>
          )
        )}

        {skippedActions.length > 0 && stage.status === 'completed' && (
          <Collapse
            ghost
            size="small"
            items={[
              {
                key: 'skipped',
                label: (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {skippedActions.length} planned action
                    {skippedActions.length === 1 ? '' : 's'} did not fire
                  </Text>
                ),
                children: (
                  <Space direction="vertical" size={2}>
                    {skippedActions.map((a) => (
                      <Tooltip
                        key={a.action_id}
                        title={a.description || 'no description'}
                      >
                        <Text
                          type="secondary"
                          style={{ fontSize: 11, paddingLeft: 16 }}
                        >
                          • {a.action_name}{' '}
                          {a.mitre_technique && (
                            <Tag style={{ fontSize: 9, marginLeft: 4 }}>
                              {a.mitre_technique}
                            </Tag>
                          )}
                        </Text>
                      </Tooltip>
                    ))}
                  </Space>
                ),
              },
            ]}
          />
        )}
      </Space>
    </Card>
  );
}

export interface AttackReportPanelProps {
  report: AttackReport;
  playbook: AttackPlaybook;
  source?: 'live' | 'history' | 'none';
  onRunAgain?: () => void;
}

const AttackReportPanel: React.FC<AttackReportPanelProps> = ({
  report,
  playbook,
  source = 'live',
  onRunAgain,
}) => {
  if (!report) {
    return (
      <Card size="small">
        <Empty description="No attack report available yet" />
      </Card>
    );
  }

  const totalWallTime =
    report.completed_at && report.started_at
      ? report.completed_at - report.started_at
      : 0;

  return (
    <Space direction="vertical" size={12} style={{ width: '100%' }}>
      {/* Header summary card */}
      <Card
        size="small"
        style={{ background: '#141428', border: '1px solid #2d2d52' }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
          <div style={{ flex: 1 }}>
            <Space size={8} wrap>
              <Text strong style={{ fontSize: 16, color: '#dde2ec' }}>
                {report.playbook_name}
              </Text>
              {statusBadge(report.status)}
              <Tag color={severityColors[report.severity] || 'default'}>
                {report.severity}
              </Tag>
              {report.mitre_software_id && (
                <Tag color="blue">{report.mitre_software_id}</Tag>
              )}
              {source === 'history' && (
                <Tag color="default">historical run</Tag>
              )}
            </Space>
            <div style={{ marginTop: 6, fontSize: 12, color: '#8aa4bc' }}>
              Started {formatTimestamp(report.started_at)} · Ended{' '}
              {formatTimestamp(report.completed_at)} · Wall time{' '}
              {formatDuration(totalWallTime)} · Intensity{' '}
              {report.intensity.toFixed(2)}× · Attacker{' '}
              <code style={{ color: '#dde2ec' }}>{report.attacker_ip}</code>
            </div>
          </div>
          <Space>
            {onRunAgain && (
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={onRunAgain}
              >
                Run again
              </Button>
            )}
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => downloadReport(report)}
            >
              Download JSON
            </Button>
          </Space>
        </div>

        <div
          style={{
            marginTop: 14,
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
            gap: 12,
          }}
        >
          <Statistic
            title="Stages"
            value={`${report.stages_completed} / ${report.total_stages}`}
            prefix={<ExperimentOutlined />}
            valueStyle={{ color: '#dde2ec', fontSize: 18 }}
          />
          <Statistic
            title="Actions fired"
            value={report.total_actions}
            valueStyle={{ color: '#dde2ec', fontSize: 18 }}
          />
          <Statistic
            title="Packets emitted"
            value={report.total_packets}
            prefix={<FireOutlined style={{ color: '#fa8c16' }} />}
            valueStyle={{ color: '#dde2ec', fontSize: 18 }}
          />
          <Statistic
            title="Targets hit"
            value={`${report.targets_hit.length} / ${report.target_device_count}`}
            valueStyle={{ color: '#dde2ec', fontSize: 18 }}
          />
          <Statistic
            title="Techniques"
            value={report.techniques_used.length}
            valueStyle={{ color: '#dde2ec', fontSize: 18 }}
          />
          <Statistic
            title="Tactics"
            value={report.tactics_covered.length}
            valueStyle={{ color: '#dde2ec', fontSize: 18 }}
          />
        </div>
      </Card>

      {/* Attacker→target visualization. The diagram shows the SHAPE
          of the attack (who hit how many targets, how heavy each pipe);
          the matrix below shows the per-pair detail. */}
      <AttackFlowDiagram report={report} title="Attack flow — attacker → targets" />

      <AttackIpMatrix report={report} variant="full" title="Attack IP matrix" />

      {/* MITRE ATT&CK coverage in "actual" mode */}
      <MitreTechniquePanel
        playbook={playbook}
        report={report}
        title="MITRE ATT&CK — what actually fired"
      />

      {/* Stage-by-stage breakdown */}
      <Card
        size="small"
        title={<span>Kill-chain breakdown</span>}
        style={{ background: '#141428', border: '1px solid #2d2d52' }}
      >
        {report.stages.length === 0 ? (
          <Empty description="No stages recorded" />
        ) : (
          report.stages.map((s) => <StageBlock key={s.stage_id} stage={s} />)
        )}
      </Card>
    </Space>
  );
};

export default AttackReportPanel;
