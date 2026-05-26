/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * AttackLibraryPage — top-level documentation index for every attack
 * playbook shipped with PacketArch. Companion to the right-panel
 * AttackPlaybookLibrary (which is sized for the narrow sidebar);
 * this page is a full-screen browse + drill-down experience.
 *
 * The page fetches `/api/v1/attacks/playbooks` and lets the user
 * filter by category, severity, and protocol. Clicking a card
 * navigates to /attack-library/:playbookId for the deep dive.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Empty,
  Input,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
} from 'antd';
import {
  AppstoreOutlined,
  BookOutlined,
  ClockCircleOutlined,
  ExperimentOutlined,
  SearchOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { attacksApi } from '../api/attacks';
import type { AttackPlaybookSummary } from '../types/attackPlaybook';

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
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

const AttackLibraryPage: React.FC = () => {
  const navigate = useNavigate();
  const [playbooks, setPlaybooks] = useState<AttackPlaybookSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<string | null>(null);
  const [severity, setSeverity] = useState<string | null>(null);
  const [protocol, setProtocol] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    attacksApi
      .listPlaybooks()
      .then((res) => {
        if (alive) setPlaybooks(res);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return playbooks.filter((p) => {
      if (category && p.category !== category) return false;
      if (severity && p.severity !== severity) return false;
      if (protocol && !p.required_protocols.includes(protocol)) return false;
      if (term) {
        const hay = `${p.name} ${p.description} ${p.mitre_software_id}`.toLowerCase();
        if (!hay.includes(term)) return false;
      }
      return true;
    });
  }, [playbooks, search, category, severity, protocol]);

  const allCategories = useMemo(
    () => Array.from(new Set(playbooks.map((p) => p.category))).sort(),
    [playbooks],
  );
  const allSeverities = useMemo(
    () => Array.from(new Set(playbooks.map((p) => p.severity))).sort(),
    [playbooks],
  );
  const allProtocols = useMemo(
    () =>
      Array.from(
        new Set(playbooks.flatMap((p) => p.required_protocols).filter(Boolean)),
      ).sort(),
    [playbooks],
  );

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 20 }}>
        <Space align="center" size={10}>
          <BookOutlined style={{ fontSize: 24, color: '#ff7875' }} />
          <Title level={3} style={{ margin: 0, color: '#dde2ec' }}>
            Attack Library
          </Title>
          <Tag color="red">{playbooks.length} playbooks</Tag>
        </Space>
        <Paragraph type="secondary" style={{ marginTop: 8, maxWidth: 920 }}>
          Detailed documentation for every attack playbook PacketArch ships
          with. Each entry is a multi-stage kill chain modeled on a real
          ICS campaign (TRITON, INDUSTROYER, PIPEDREAM, HAVEX), an insider
          threat pattern, a reconnaissance flow, or an IDS-rule validation
          suite. Click a playbook to see its stages, MITRE ATT&CK technique
          coverage, the per-action behaviour, and what Cyber Vision should
          alert on.
        </Paragraph>
      </div>

      {/* Filter bar */}
      <Card
        size="small"
        style={{
          marginBottom: 16,
          background: '#141428',
          border: '1px solid #2d2d52',
        }}
        bodyStyle={{ padding: '12px 16px' }}
      >
        <Space wrap size={12}>
          <Input
            placeholder="Search by name, MITRE ID, description"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            prefix={<SearchOutlined />}
            allowClear
            style={{ width: 320 }}
          />
          <Select
            placeholder="Category"
            allowClear
            value={category}
            onChange={(v) => setCategory(v ?? null)}
            style={{ width: 180 }}
            options={allCategories.map((c) => ({
              value: c,
              label: categoryLabels[c] || c,
            }))}
          />
          <Select
            placeholder="Severity"
            allowClear
            value={severity}
            onChange={(v) => setSeverity(v ?? null)}
            style={{ width: 140 }}
            options={allSeverities.map((s) => ({ value: s, label: s }))}
          />
          <Select
            placeholder="Required protocol"
            allowClear
            value={protocol}
            onChange={(v) => setProtocol(v ?? null)}
            style={{ width: 200 }}
            options={allProtocols.map((p) => ({ value: p, label: p }))}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            Showing <strong>{filtered.length}</strong> of {playbooks.length}
          </Text>
        </Space>
      </Card>

      {loading ? (
        <div style={{ padding: 60, textAlign: 'center' }}>
          <Spin />
        </div>
      ) : filtered.length === 0 ? (
        <Empty description="No playbooks match the current filters" />
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
            gap: 16,
          }}
        >
          {filtered.map((pb) => (
            <Card
              key={pb.playbook_id}
              hoverable
              onClick={() => navigate(`/attack-library/${pb.playbook_id}`)}
              style={{
                background: '#141428',
                border: `1px solid ${
                  severityColors[pb.severity] || '#2d2d52'
                }33`,
              }}
              bodyStyle={{ padding: 16 }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  gap: 8,
                  marginBottom: 8,
                }}
              >
                <Space size={6}>
                  <ThunderboltOutlined
                    style={{ color: severityColors[pb.severity] || '#ff7875' }}
                  />
                  <Text strong style={{ color: '#dde2ec', fontSize: 15 }}>
                    {pb.name}
                  </Text>
                </Space>
                <Tag
                  color={severityColors[pb.severity] || 'default'}
                  style={{ margin: 0, fontWeight: 600 }}
                >
                  {pb.severity}
                </Tag>
              </div>

              <Space size={4} wrap style={{ marginBottom: 10 }}>
                {pb.mitre_software_id && (
                  <Tag color="blue" style={{ fontSize: 10 }}>
                    MITRE {pb.mitre_software_id}
                  </Tag>
                )}
                <Tag style={{ fontSize: 10 }}>
                  {categoryLabels[pb.category] || pb.category}
                </Tag>
                {pb.industry_verticals.slice(0, 2).map((v) => (
                  <Tag key={v} style={{ fontSize: 10 }}>
                    {v}
                  </Tag>
                ))}
              </Space>

              <Paragraph
                style={{
                  color: '#a8a8c0',
                  fontSize: 12,
                  marginBottom: 12,
                }}
                ellipsis={{ rows: 3 }}
              >
                {pb.description}
              </Paragraph>

              <div
                style={{
                  display: 'flex',
                  gap: 16,
                  paddingTop: 8,
                  borderTop: '1px solid #2d2d52',
                  fontSize: 11,
                  color: '#8aa4bc',
                }}
              >
                <span>
                  <ExperimentOutlined /> {pb.stage_count} stages
                </span>
                <span>
                  <ClockCircleOutlined /> {formatDuration(pb.total_duration_seconds)}
                </span>
                {pb.required_protocols.length > 0 && (
                  <span style={{ flex: 1, textAlign: 'right' }}>
                    <AppstoreOutlined />{' '}
                    {pb.required_protocols.slice(0, 3).join(', ')}
                    {pb.required_protocols.length > 3 && '…'}
                  </span>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default AttackLibraryPage;
