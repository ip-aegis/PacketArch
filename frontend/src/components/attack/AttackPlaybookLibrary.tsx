/**
 * AttackPlaybookLibrary - Card grid for browsing and selecting attack playbooks.
 */

import React, { useEffect } from 'react';
import { Card, Tag, Space, Spin, Typography, Empty, Tooltip } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import { useAttackStore } from '../../stores/attackStore';
import type { AttackPlaybookSummary } from '../../types/attackPlaybook';

const { Text } = Typography;

interface AttackPlaybookLibraryProps {
  scenarioId: string | null;
  onSelect: (playbookId: string) => void;
}

const severityColors: Record<string, string> = {
  critical: '#ff4d4f',
  high: '#fa8c16',
  medium: '#faad14',
  low: '#52c41a',
};

const categoryLabels: Record<string, string> = {
  apt: 'APT',
  insider: 'Insider',
  reconnaissance: 'Recon',
};

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

const PlaybookCard: React.FC<{
  playbook: AttackPlaybookSummary;
  onSelect: () => void;
}> = ({ playbook, onSelect }) => (
  <Card
    hoverable
    size="small"
    onClick={onSelect}
    style={{
      background: '#0d1117',
      border: '1px solid #2a3f54',
      cursor: 'pointer',
    }}
    styles={{
      body: { padding: '10px 12px' },
    }}
  >
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
      <Text strong style={{ color: '#e6f1ff', fontSize: 12, lineHeight: '18px', flex: 1 }}>
        {playbook.name}
      </Text>
      <Tag
        color={severityColors[playbook.severity] || '#ff4d4f'}
        style={{ fontSize: 9, margin: 0, lineHeight: '14px', padding: '0 4px', marginLeft: 6 }}
      >
        {playbook.severity.toUpperCase()}
      </Tag>
    </div>

    <Text style={{ color: '#6a8caf', fontSize: 10, display: 'block', marginBottom: 6 }} ellipsis>
      {playbook.description.slice(0, 120)}{playbook.description.length > 120 ? '...' : ''}
    </Text>

    {/* Kill-chain stage dots */}
    <div style={{ display: 'flex', gap: 3, marginBottom: 6 }}>
      {Array.from({ length: playbook.stage_count }).map((_, i) => (
        <Tooltip key={i} title={`Stage ${i + 1}`}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: `hsl(${(i / playbook.stage_count) * 30}, 80%, 55%)`,
              border: '1px solid #2a3f54',
            }}
          />
        </Tooltip>
      ))}
      <Text style={{ color: '#4a6a8a', fontSize: 9, marginLeft: 4 }}>
        {playbook.stage_count} stages
      </Text>
    </div>

    {/* Tags row */}
    <Space size={2} wrap>
      {playbook.mitre_software_id && (
        <Tag style={{ fontSize: 9, margin: 0, lineHeight: '14px', padding: '0 4px', background: '#1d1d3a', borderColor: '#3d3d7a', color: '#b3b3ff' }}>
          {playbook.mitre_software_id}
        </Tag>
      )}
      <Tag style={{ fontSize: 9, margin: 0, lineHeight: '14px', padding: '0 4px', background: '#1a0d0d', borderColor: '#5c2223', color: '#ff7875' }}>
        {categoryLabels[playbook.category] || playbook.category}
      </Tag>
      <Tag style={{ fontSize: 9, margin: 0, lineHeight: '14px', padding: '0 4px', background: '#0d1b2a', borderColor: '#2a3f54', color: '#6a8caf' }}>
        {formatDuration(playbook.total_duration_seconds)}
      </Tag>
      {playbook.required_protocols.slice(0, 2).map((p) => (
        <Tag key={p} style={{ fontSize: 9, margin: 0, lineHeight: '14px', padding: '0 4px', background: '#0d1b2a', borderColor: '#2a3f54', color: '#5a9fd4' }}>
          {p}
        </Tag>
      ))}
    </Space>
  </Card>
);

const AttackPlaybookLibrary: React.FC<AttackPlaybookLibraryProps> = ({ scenarioId, onSelect }) => {
  const { playbooks, isLoadingPlaybooks, fetchPlaybooks, fetchCompatible } = useAttackStore();

  useEffect(() => {
    if (scenarioId) {
      fetchCompatible(scenarioId);
    } else {
      fetchPlaybooks();
    }
  }, [scenarioId, fetchPlaybooks, fetchCompatible]);

  if (isLoadingPlaybooks) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <Spin size="small" />
        <Text style={{ color: '#6a8caf', display: 'block', marginTop: 8, fontSize: 11 }}>
          Loading playbooks...
        </Text>
      </div>
    );
  }

  if (playbooks.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <Text style={{ color: '#6a8caf', fontSize: 11 }}>
            No compatible playbooks found
          </Text>
        }
        style={{ marginTop: 40 }}
      />
    );
  }

  return (
    <div style={{ padding: '8px 0' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, padding: '0 4px' }}>
        <ThunderboltOutlined style={{ color: '#ff4d4f', fontSize: 12 }} />
        <Text style={{ color: '#c9d1d9', fontSize: 12, fontWeight: 500 }}>
          Attack Playbooks
        </Text>
        <Text style={{ color: '#4a6a8a', fontSize: 10 }}>
          ({playbooks.length})
        </Text>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {playbooks.map((p) => (
          <PlaybookCard key={p.playbook_id} playbook={p} onSelect={() => onSelect(p.playbook_id)} />
        ))}
      </div>
    </div>
  );
};

export default AttackPlaybookLibrary;
