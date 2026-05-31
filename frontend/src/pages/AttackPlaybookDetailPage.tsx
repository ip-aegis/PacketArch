/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * AttackPlaybookDetailPage — full documentation view for one attack
 * playbook. Companion to AttackLibraryPage's grid view.
 *
 * Sections:
 *   1. Header card — name, severity, MITRE software ID, category,
 *      target verticals, required protocols, total duration.
 *   2. Narrative description.
 *   3. Kill-chain flowchart (SVG).
 *   4. MITRE ATT&CK coverage (planned mode).
 *   5. Per-stage detail cards anchored by stage_id so the flowchart's
 *      stage nodes can scroll-jump.
 *   6. References + "Run this playbook" CTA.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Empty,
  Space,
  Spin,
  Statistic,
  Tag,
  Typography,
} from 'antd';
import {
  ArrowLeftOutlined,
  ClockCircleOutlined,
  ExperimentOutlined,
  ExportOutlined,
  EyeOutlined,
  LinkOutlined,
  PlayCircleOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { attacksApi } from '../api/attacks';
import KillChainFlowChart from '../components/attack/KillChainFlowChart';
import MitreTechniquePanel from '../components/attack/MitreTechniquePanel';
import type {
  AttackAction,
  AttackPlaybook,
  KillChainStage,
} from '../types/attackPlaybook';

const { Title, Text, Paragraph } = Typography;

const severityColors: Record<string, string> = {
  critical: '#ff4d4f',
  high: '#fa8c16',
  medium: '#faad14',
  low: '#52c41a',
};

const categoryLabels: Record<string, string> = {
  apt: 'APT campaign',
  insider: 'Insider threat',
  reconnaissance: 'Reconnaissance',
  ids_testing: 'IDS validation',
};

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function StageActionCard({ action }: { action: AttackAction }): React.ReactElement {
  const paramEntries = Object.entries(action.parameters || {}).filter(
    ([, v]) => v !== null && v !== undefined && v !== '',
  );
  return (
    <Card
      size="small"
      style={{
        background: '#141428',
        border: '1px solid #2d2d52',
        marginBottom: 8,
      }}
      bodyStyle={{ padding: 12 }}
    >
      <Space style={{ width: '100%', justifyContent: 'space-between' }} wrap>
        <Space size={6} wrap>
          <Text strong style={{ color: '#dde2ec', fontSize: 13 }}>
            {action.name}
          </Text>
          {action.mitre_technique && (
            <Tag color="blue" style={{ fontSize: 10 }}>
              MITRE {action.mitre_technique}
            </Tag>
          )}
          <Tag style={{ fontSize: 10 }}>type: {action.action_type}</Tag>
          {action.target_selector && action.target_selector !== 'any' && (
            <Tag color="purple" style={{ fontSize: 10 }}>
              targets: {action.target_selector}
            </Tag>
          )}
          {action.repeat_count > 1 && (
            <Tag color="orange" style={{ fontSize: 10 }}>
              repeats ×{action.repeat_count}
            </Tag>
          )}
        </Space>
      </Space>

      {action.description && (
        <Paragraph
          style={{ color: '#a8a8c0', fontSize: 12, margin: '8px 0 4px' }}
        >
          {action.description}
        </Paragraph>
      )}

      {action.expected_cv_detection && (
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 6,
            padding: '6px 10px',
            background: '#0d1117',
            borderRadius: 4,
            border: '1px solid #1a3a2a',
            marginTop: 6,
          }}
        >
          <SafetyCertificateOutlined
            style={{ color: '#52c41a', fontSize: 13, marginTop: 2 }}
          />
          <Text style={{ color: '#8cc8a0', fontSize: 11 }}>
            <strong>CV detection:</strong> {action.expected_cv_detection}
          </Text>
        </div>
      )}

      {paramEntries.length > 0 && (
        <details style={{ marginTop: 6 }}>
          <summary
            style={{ cursor: 'pointer', color: '#8aa4bc', fontSize: 11 }}
          >
            Action parameters ({paramEntries.length})
          </summary>
          <pre
            style={{
              fontSize: 11,
              background: '#0e0e1f',
              padding: 8,
              margin: '4px 0 0',
              borderRadius: 3,
              color: '#a8a8c0',
              maxHeight: 200,
              overflow: 'auto',
            }}
          >
            {JSON.stringify(action.parameters, null, 2)}
          </pre>
        </details>
      )}
    </Card>
  );
}

function StageDetailCard({ stage, index }: { stage: KillChainStage; index: number }): React.ReactElement {
  return (
    <Card
      id={`stage-${stage.stage_id}`}
      size="small"
      style={{
        background: '#0e0e1f',
        border: `1px solid ${stage.color}55`,
        marginBottom: 12,
        scrollMarginTop: 80,
      }}
      title={
        <Space size={8}>
          <div
            style={{
              width: 22,
              height: 22,
              borderRadius: '50%',
              background: `${stage.color}66`,
              border: `1px solid ${stage.color}`,
              color: '#fff',
              fontSize: 11,
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {index + 1}
          </div>
          <span style={{ color: '#dde2ec', fontSize: 14 }}>{stage.name}</span>
          <Tag style={{ fontSize: 10 }}>
            <ClockCircleOutlined /> {formatDuration(stage.duration_seconds)}
          </Tag>
          <Tag style={{ fontSize: 10 }}>
            {stage.actions.length} action{stage.actions.length === 1 ? '' : 's'}
          </Tag>
          {stage.mitre_tactics.map((t) => (
            <Tag key={t} color="purple" style={{ fontSize: 10 }}>
              {t}
            </Tag>
          ))}
        </Space>
      }
    >
      {stage.description && (
        <Paragraph
          style={{ color: '#cfd6e4', fontSize: 13, marginBottom: 12 }}
        >
          {stage.description}
        </Paragraph>
      )}

      {stage.expected_cv_alerts.length > 0 && (
        <Alert
          type="info"
          showIcon
          icon={<EyeOutlined />}
          style={{ marginBottom: 12, padding: '6px 12px' }}
          message={
            <Text style={{ color: '#cfd6e4', fontSize: 12 }}>
              <strong>What Cyber Vision should catch in this stage:</strong>{' '}
              {stage.expected_cv_alerts.join('; ')}
            </Text>
          }
        />
      )}

      <Text strong style={{ color: '#8aa4bc', fontSize: 11 }}>
        Actions in this stage
      </Text>
      <div style={{ marginTop: 6 }}>
        {stage.actions.map((a) => (
          <StageActionCard key={a.action_id} action={a} />
        ))}
      </div>
    </Card>
  );
}

const AttackPlaybookDetailPage: React.FC = () => {
  const { playbookId } = useParams<{ playbookId: string }>();
  const navigate = useNavigate();
  const [playbook, setPlaybook] = useState<AttackPlaybook | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!playbookId) return;
    setLoading(true);
    attacksApi
      .getPlaybook(playbookId)
      .then((pb) => setPlaybook(pb))
      .catch((e) => setError(e?.message || 'Failed to load playbook'))
      .finally(() => setLoading(false));
  }, [playbookId]);

  const scrollToStage = useCallback((stageId: string) => {
    const el = document.getElementById(`stage-${stageId}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 60, textAlign: 'center' }}>
        <Spin />
      </div>
    );
  }

  if (error || !playbook) {
    return (
      <div style={{ padding: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/libraries?tab=attacks')}
          style={{ marginBottom: 12 }}
        >
          Back to library
        </Button>
        <Empty description={error || 'Playbook not found'} />
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      <Button
        type="text"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/libraries?tab=attacks')}
        style={{ color: '#8aa4bc', marginBottom: 12 }}
      >
        Attack Library
      </Button>

      {/* Header card */}
      <Card
        style={{
          background: '#141428',
          border: `1px solid ${severityColors[playbook.severity] || '#2d2d52'}66`,
          marginBottom: 16,
        }}
      >
        <Space size={12} align="start" style={{ width: '100%' }}>
          <ThunderboltOutlined
            style={{
              fontSize: 32,
              color: severityColors[playbook.severity] || '#ff7875',
            }}
          />
          <div style={{ flex: 1 }}>
            <Space size={6} wrap>
              <Title level={3} style={{ margin: 0, color: '#dde2ec' }}>
                {playbook.name}
              </Title>
              <Tag
                color={severityColors[playbook.severity] || 'default'}
                style={{ fontWeight: 600, marginLeft: 8 }}
              >
                {playbook.severity}
              </Tag>
            </Space>
            <Space size={6} wrap style={{ marginTop: 8 }}>
              {playbook.mitre_software_id && (
                <Tag color="blue">MITRE {playbook.mitre_software_id}</Tag>
              )}
              <Tag>{categoryLabels[playbook.category] || playbook.category}</Tag>
              {playbook.industry_verticals.map((v) => (
                <Tag key={v} color="gold">
                  {v}
                </Tag>
              ))}
            </Space>
          </div>
        </Space>

        <Paragraph
          style={{ color: '#cfd6e4', fontSize: 14, marginTop: 16, marginBottom: 8 }}
        >
          {playbook.description}
        </Paragraph>

        <div
          style={{
            marginTop: 16,
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
            gap: 16,
          }}
        >
          <Statistic
            title="Total duration"
            value={formatDuration(playbook.total_duration_seconds)}
            prefix={<ClockCircleOutlined />}
            valueStyle={{ color: '#dde2ec', fontSize: 18 }}
          />
          <Statistic
            title="Kill-chain stages"
            value={playbook.stages.length}
            prefix={<ExperimentOutlined />}
            valueStyle={{ color: '#dde2ec', fontSize: 18 }}
          />
          <Statistic
            title="Total actions"
            value={playbook.stages.reduce((s, st) => s + st.actions.length, 0)}
            valueStyle={{ color: '#dde2ec', fontSize: 18 }}
          />
          <Statistic
            title="Required protocols"
            value={
              playbook.required_protocols.length === 0
                ? 'any'
                : playbook.required_protocols.join(', ')
            }
            valueStyle={{ color: '#dde2ec', fontSize: 14 }}
          />
        </div>

        <Space style={{ marginTop: 16 }}>
          {playbook.reference_url && (
            <Button
              type="link"
              icon={<LinkOutlined />}
              href={playbook.reference_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              External reference
              <ExportOutlined style={{ marginLeft: 4 }} />
            </Button>
          )}
          <Button
            type="primary"
            danger
            icon={<PlayCircleOutlined />}
            onClick={() => navigate('/scenarios')}
          >
            Run this playbook
          </Button>
        </Space>
      </Card>

      {/* Kill-chain flowchart */}
      <Card
        size="small"
        title={
          <Space>
            <ExperimentOutlined />
            <span>Kill chain</span>
            <Text type="secondary" style={{ fontSize: 11 }}>
              ({playbook.stages.length} stages over{' '}
              {formatDuration(playbook.total_duration_seconds)})
            </Text>
          </Space>
        }
        style={{
          background: '#141428',
          border: '1px solid #2d2d52',
          marginBottom: 16,
        }}
      >
        <KillChainFlowChart
          stages={playbook.stages}
          onStageClick={scrollToStage}
        />
      </Card>

      {/* MITRE ATT&CK coverage */}
      <div style={{ marginBottom: 16 }}>
        <MitreTechniquePanel
          playbook={playbook}
          title="MITRE ATT&CK technique coverage (planned)"
        />
      </div>

      {/* Stage-by-stage details */}
      <Card
        size="small"
        title={
          <Space>
            <span>Stage-by-stage breakdown</span>
            <Text type="secondary" style={{ fontSize: 11 }}>
              click a stage in the kill-chain to jump here
            </Text>
          </Space>
        }
        style={{ background: '#141428', border: '1px solid #2d2d52' }}
      >
        {playbook.stages.map((stage, i) => (
          <StageDetailCard key={stage.stage_id} stage={stage} index={i} />
        ))}
      </Card>
    </div>
  );
};

export default AttackPlaybookDetailPage;
