/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Library Hub — the single reference home for everything PacketArch ships as
 * read-only reference data. Consolidates three formerly-standalone pages by
 * EMBEDDING the existing prop-less components (passed `embedded` so they drop
 * their own page chrome), so nothing is duplicated or lost (additive).
 *
 *   Overview        — combined stat cards + quick links into each library
 *   CVEs            — vulnerability browser (was /cves)
 *   Attacks         — attack playbook library (was /attack-library)
 *   Device Library  — protocols / vendors / device templates (was /fingerprints)
 */

import React, { useEffect, useState } from 'react';
import { Tabs, Typography, Row, Col, Card, Statistic, Button, Space } from 'antd';
import type { TabsProps } from 'antd';
import {
  BugOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  AppstoreOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons';
import { useSearchParams } from 'react-router-dom';

import CVEBrowserPage from './CVEBrowserPage';
import AttackLibraryPage from './AttackLibraryPage';
import FingerprintingLibraryPage from './FingerprintingLibraryPage';
import { getCVEStats } from '../api/cve';
import { getStats as getFingerprintStats } from '../api/fingerprints';
import { attacksApi } from '../api/attacks';

const { Title, Text } = Typography;

const statCardStyle: React.CSSProperties = {
  background: '#1a1a2e',
  border: '1px solid #2d2d52',
};

/** Combined snapshot across the three libraries. Best-effort: any failed
 *  fetch leaves that figure at zero rather than breaking the hub. */
const LibraryOverview: React.FC<{ onJump: (tab: string) => void }> = ({ onJump }) => {
  const [stats, setStats] = useState({
    totalCves: 0,
    criticalCves: 0,
    cvCves: 0,
    playbooks: 0,
    protocols: 0,
    vendors: 0,
    templates: 0,
    firmwareVariants: 0,
  });

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const [cve, fp, playbooks] = await Promise.all([
        getCVEStats().catch(() => null),
        getFingerprintStats().catch(() => null),
        attacksApi.listPlaybooks().catch(() => []),
      ]);
      if (cancelled) return;
      setStats({
        totalCves: cve?.total_cves ?? 0,
        criticalCves: cve?.by_severity?.critical ?? 0,
        cvCves: cve?.cyber_vision_detectable ?? 0,
        playbooks: playbooks.length,
        protocols: fp?.total_protocols ?? 0,
        vendors: fp?.total_vendors ?? 0,
        templates: fp?.total_device_templates ?? 0,
        firmwareVariants: fp?.total_firmware_variants ?? 0,
      });
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const sections: Array<{
    key: string;
    title: string;
    icon: React.ReactNode;
    color: string;
    blurb: string;
    figures: Array<{ label: string; value: number; color?: string }>;
  }> = [
    {
      key: 'cves',
      title: 'CVEs',
      icon: <BugOutlined />,
      color: '#ff4d4f',
      blurb: 'ICS/OT vulnerabilities for security testing, cross-referenced with Cyber Vision.',
      figures: [
        { label: 'Total CVEs', value: stats.totalCves },
        { label: 'Critical', value: stats.criticalCves, color: '#ff4d4f' },
        { label: 'CV detectable', value: stats.cvCves, color: '#52c41a' },
      ],
    },
    {
      key: 'attacks',
      title: 'Attack Library',
      icon: <ThunderboltOutlined />,
      color: '#fa8c16',
      blurb: 'Multi-stage kill-chain playbooks modeled on real ICS campaigns.',
      figures: [{ label: 'Playbooks', value: stats.playbooks, color: '#fa8c16' }],
    },
    {
      key: 'devices',
      title: 'Device Library',
      icon: <DatabaseOutlined />,
      color: '#049FD9',
      blurb: 'Protocols, vendors, and device templates that drive traffic generation.',
      figures: [
        { label: 'Templates', value: stats.templates },
        { label: 'Vendors', value: stats.vendors },
        { label: 'Protocols', value: stats.protocols },
        { label: 'Firmware variants', value: stats.firmwareVariants },
      ],
    },
  ];

  return (
    <Row gutter={[16, 16]}>
      {sections.map((s) => (
        <Col xs={24} lg={8} key={s.key}>
          <Card
            style={statCardStyle}
            hoverable
            onClick={() => onJump(s.key)}
            styles={{ body: { padding: 20 } }}
          >
            <Space align="center" size={10} style={{ marginBottom: 4 }}>
              <span style={{ color: s.color, fontSize: 22 }}>{s.icon}</span>
              <Title level={4} style={{ color: '#fff', margin: 0 }}>
                {s.title}
              </Title>
            </Space>
            <Text style={{ color: '#8b8fa3', display: 'block', minHeight: 44 }}>{s.blurb}</Text>
            <Row gutter={[12, 12]} style={{ marginTop: 16 }}>
              {s.figures.map((f) => (
                <Col span={12} key={f.label}>
                  <Statistic
                    title={<Text style={{ color: '#8b8fa3', fontSize: 11 }}>{f.label}</Text>}
                    value={f.value}
                    valueStyle={{ color: f.color || '#fff', fontSize: 22 }}
                  />
                </Col>
              ))}
            </Row>
            <Button
              type="link"
              style={{ padding: 0, marginTop: 12 }}
              onClick={(e) => {
                e.stopPropagation();
                onJump(s.key);
              }}
            >
              Open {s.title} <ArrowRightOutlined />
            </Button>
          </Card>
        </Col>
      ))}
    </Row>
  );
};

const LibraryHubPage: React.FC = () => {
  // Deep-linkable tab via ?tab=, matching the SettingsPage / AgentsHub convention.
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') || 'overview';
  const [activeKey, setActiveKey] = useState(initialTab);

  const onChange = (key: string) => {
    setActiveKey(key);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('tab', key);
      return next;
    });
  };

  const items: TabsProps['items'] = [
    {
      key: 'overview',
      label: (
        <span>
          <AppstoreOutlined /> Overview
        </span>
      ),
      children: <LibraryOverview onJump={onChange} />,
    },
    {
      key: 'cves',
      label: (
        <span>
          <BugOutlined /> CVEs
        </span>
      ),
      children: <CVEBrowserPage embedded />,
    },
    {
      key: 'attacks',
      label: (
        <span>
          <ThunderboltOutlined /> Attacks
        </span>
      ),
      children: <AttackLibraryPage embedded />,
    },
    {
      key: 'devices',
      label: (
        <span>
          <DatabaseOutlined /> Device Library
        </span>
      ),
      children: <FingerprintingLibraryPage embedded />,
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginTop: 0 }}>
        Libraries
      </Title>
      <Tabs activeKey={activeKey} onChange={onChange} items={items} destroyInactiveTabPane />
    </div>
  );
};

export default LibraryHubPage;
