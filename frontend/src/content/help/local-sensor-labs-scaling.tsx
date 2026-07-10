/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Local Sensor Labs — Memory Sizing Help Article
 */

import React from 'react';
import { Typography, Space, Card, Alert, Table, Tag } from 'antd';
import { DatabaseOutlined, WarningOutlined, CalculatorOutlined } from '@ant-design/icons';
import { TEXT_PARAGRAPH, ACCENT_BLUE, CARD_STYLE, CODE_BLOCK_STYLE } from '../../constants/theme';
import type { HelpArticle } from './index';

const { Title, Paragraph, Text } = Typography;

const LocalSensorLabsScalingContent: React.FC = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
          <DatabaseOutlined style={{ marginRight: 8, color: ACCENT_BLUE }} />
          Local Sensor Labs: Memory Sizing
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH, fontSize: 15 }}>
          Each Local Sensor Lab runs a Cisco Cyber Vision docker sensor and a traffic agent
          on this host. Both are real containers with a real memory cost — this page covers
          how much, why, and how to size a host for a target number of concurrent labs.
        </Paragraph>
      </div>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Why a sensor costs ~1.2&nbsp;GB
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          Cyber Vision's sensor process (<Text code>flowsf</Text>) opens a capture socket on
          its monitored interface and allocates a <Text strong style={{ color: '#fff' }}>fixed
          1&nbsp;GiB ring buffer</Text> for zero-copy packet capture. That buffer is private to
          each sensor instance — it is not shared or deduplicated across labs, and it does{' '}
          <Text strong style={{ color: '#fff' }}>not</Text> scale with scenario size: a
          4-device scenario and a 40-device scenario cost the same.
        </Paragraph>
        <Table
          size="small"
          pagination={false}
          dataSource={[
            { component: 'CV sensor (flowsf + container)', cost: '~1.18 GB', note: 'dominated by the fixed 1 GiB capture ring buffer' },
            { component: 'Traffic agent container', cost: '~0.08 GB', note: 'scales lightly with active traffic' },
            { component: 'Per active lab, total', cost: '~1.26 GB', note: 'flat cost, independent of scenario size' },
          ]}
          columns={[
            { title: 'Component', dataIndex: 'component', render: (t) => <Text style={{ color: '#fff' }}>{t}</Text> },
            { title: 'Memory', dataIndex: 'cost', render: (t) => <Tag color="blue">{t}</Tag> },
            { title: 'Notes', dataIndex: 'note', render: (t) => <Text style={{ color: TEXT_PARAGRAPH }}>{t}</Text> },
          ]}
          rowKey="component"
          style={{ background: 'transparent' }}
        />
      </Card>

      <Alert
        type="warning"
        showIcon
        icon={<WarningOutlined />}
        message="docker stats undercounts this — don't trust it alone"
        description={
          <>
            <Text style={{ color: TEXT_PARAGRAPH }}>
              <Text code>docker stats</Text> reports a sensor container using only ~100-160&nbsp;MB,
              against a real ~1.18&nbsp;GB — the AF_PACKET ring buffer isn't attributed the way
              cgroup memory accounting expects. When judging headroom before starting another
              lab, check <Text code>free -h</Text> or <Text code>vmstat 1</Text> (system-level,
              real), not <Text code>docker stats</Text>.
            </Text>
          </>
        }
        style={CARD_STYLE}
      />

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          <CalculatorOutlined style={{ marginRight: 8 }} />
          Sizing formula
        </Title>
        <Paragraph style={{ color: TEXT_PARAGRAPH }}>
          The platform itself (backend, Celery, Postgres, Redis, frontend, and the Docker
          daemon) has a roughly fixed baseline of <Text strong style={{ color: '#fff' }}>~1.5&nbsp;GB</Text>,
          independent of how many labs are running. Beyond that, each lab adds ~1.26&nbsp;GB.
          To find how many labs a host can safely run at once, with a 20% margin to avoid swap:
        </Paragraph>
        <pre style={CODE_BLOCK_STYLE}>
          {'max_concurrent_labs = floor(\n  (Total_RAM_GB - 1.5 - 0.2 * Total_RAM_GB) / 1.26\n)'}
        </pre>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginBottom: 0 }}>
          For new host sizing, the same numbers as a simple rule of thumb: budget{' '}
          <Text strong style={{ color: '#fff' }}>~1.5&nbsp;GB + ~1.5&nbsp;GB per planned
          concurrent lab</Text>. A host with 12&nbsp;GB of RAM, for example, comfortably
          supports around 6 concurrent active labs before swap becomes a risk.
        </Paragraph>
      </Card>

      <Card style={CARD_STYLE}>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Signs you're over capacity
        </Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="red">Swap active</Tag> <Text code>vmstat 1</Text> shows non-zero{' '}
            <Text code>si</Text>/<Text code>so</Text> columns — the system is actively
            paging, not just holding old swapped pages
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="orange">Low available memory</Tag> the <Text code>available</Text>{' '}
            column in <Text code>free -h</Text> (not <Text code>free</Text>) is only a few
            hundred MB
          </Text>
          <Text style={{ color: TEXT_PARAGRAPH }}>
            <Tag color="volcano">General sluggishness</Tag> deploys, AI calls, or large
            queries feel slow with no other obvious cause
          </Text>
        </Space>
        <Paragraph style={{ color: TEXT_PARAGRAPH, marginTop: 12, marginBottom: 0 }}>
          If you see these, the fix is to stop labs you're not actively using (a full,
          reversible teardown — redeploy later to bring one back), or add RAM to the host.
          The sensor's ring-buffer size isn't something PacketArch configures — it comes from
          Cyber Vision's own sensor provisioning — so capping concurrent labs is the lever
          available today.
        </Paragraph>
      </Card>
    </Space>
  );
};

export const localSensorLabsScalingArticle: HelpArticle = {
  id: 'local-sensor-labs-scaling',
  title: 'Local Sensor Labs: Memory Sizing',
  category: 'traffic-generation',
  keywords: [
    'local lab', 'local sensor lab', 'memory', 'ram', 'sizing', 'scaling', 'capacity',
    'out of memory', 'oom', 'swap', 'docker stats', 'flowsf', 'ring buffer', 'cyber vision sensor',
    'how many labs', 'host sizing',
  ],
  summary: 'How much memory each Local Sensor Lab costs, why, and a formula for how many a host can run.',
  content: LocalSensorLabsScalingContent,
  relatedArticles: ['agents-hub', 'cyber-vision', 'deployments'],
  relatedPages: [],
  order: 4,
};
