/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Scenario Version History Help Article
 */

import React from 'react';
import { Typography, Space, Card, Tag, Divider, Alert } from 'antd';
import { HistoryOutlined, DiffOutlined, RollbackOutlined } from '@ant-design/icons';
import type { HelpArticle } from './index';
import { TEXT_PARAGRAPH, ACCENT_BLUE, BORDER_DEFAULT, CARD_STYLE } from '../../constants/theme';

const { Title, Paragraph, Text } = Typography;

const ScenarioVersionsContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <HistoryOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Scenario Version History
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          Every scenario keeps a history of full-definition snapshots, so you can
          experiment freely in the Studio and roll back when an edit goes wrong.
        </Paragraph>
      </div>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          Creating Versions
        </Title>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Tag color="blue" style={{ marginBottom: 4 }}>Manual</Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Press <Text code>Ctrl+S</Text> in the Studio, or use the Save Version
              button in the canvas toolbar / Version History drawer. Give versions a
              label so you can find them later — labels are editable any time.
            </Paragraph>
          </div>
          <div>
            <Tag style={{ marginBottom: 4 }}>Automatic</Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              While you edit, PacketArch coalesces changes into an automatic snapshot
              every few minutes, so you always have a recent restore point even without
              saving explicitly.
            </Paragraph>
          </div>
          <div>
            <Tag color="orange" style={{ marginBottom: 4 }}>Rollback</Tag>
            <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
              Created automatically as a safety snapshot whenever you restore an older
              version.
            </Paragraph>
          </div>
        </Space>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <DiffOutlined style={{ marginRight: 8 }} />
          Comparing Versions
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Pick any two versions in the Version History drawer and click Compare. The
          diff groups changes by category — devices, flows, zones, conduits, phases,
          metadata — and shows field-level old → new values for modified items.
          Cosmetic canvas position changes are ignored, so the diff reflects real
          design changes only.
        </Paragraph>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
          With AI enabled, the <Text strong style={{ color: '#fff' }}>Summarize</Text>{' '}
          button produces a plain-language summary of what changed between the two
          versions.
        </Paragraph>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 16 }}>
          <RollbackOutlined style={{ marginRight: 8 }} />
          Restoring
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
          Restore replaces the current scenario definition with the selected snapshot.
          A backup of the current state is saved automatically first, so a restore is
          always reversible. IP range allocations are not touched by a restore.
        </Paragraph>
      </Card>

      <Divider style={{ borderColor: BORDER_DEFAULT }} />

      <Alert
        type="info"
        showIcon
        message="Retention"
        description="Each scenario keeps up to 50 versions; the oldest are pruned automatically. Deleting a scenario deletes its version history."
        style={CARD_STYLE}
      />
    </Space>
  );
};

export const scenarioVersionsArticle: HelpArticle = {
  id: 'scenario-versions',
  title: 'Scenario Version History',
  category: 'scenarios',
  keywords: [
    'version', 'versions', 'history', 'snapshot', 'save', 'ctrl+s',
    'diff', 'compare', 'restore', 'rollback', 'undo', 'backup', 'label'
  ],
  summary: 'Snapshot, compare, and restore scenario versions — manual Ctrl+S saves, automatic snapshots, field-level diffs, and safe rollback.',
  content: ScenarioVersionsContent,
  relatedArticles: ['scenario-studio', 'scenarios'],
  relatedPages: [],
  order: 6,
};
