/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React from 'react';
import { Card, Tag, Space, Typography, Row, Col, Statistic } from 'antd';
import {
  PlayCircleOutlined,
  ClockCircleOutlined,
  SwapOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import type { DashboardDeployment } from '../../api/dashboard';
import { formatPacketRate, formatBandwidth, formatBytes, formatUptime, formatNumber } from '../../utils/formatUtils';
import ProtocolBreakdownChart from './ProtocolBreakdownChart';
import PacketRateSparkline from './PacketRateSparkline';
import KillChainTimeline from '../attack/KillChainTimeline';

const { Text } = Typography;

interface DeploymentCardProps {
  deployment: DashboardDeployment;
}

const stateColors: Record<string, string> = {
  running: 'green',
  starting: 'blue',
  stopping: 'orange',
  stopped: 'default',
  error: 'red',
};

const DeploymentCard: React.FC<DeploymentCardProps> = ({ deployment }) => (
  <Card
    style={{
      background: '#1a1a2e',
      border: '1px solid #2d2d52',
    }}
    title={
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <PlayCircleOutlined style={{ color: '#52c41a' }} />
        <Text strong style={{ color: '#fff', fontSize: 16 }}>
          {deployment.scenario_name || 'Unnamed Scenario'}
        </Text>
        <Tag color="purple">{deployment.agent_name}</Tag>
        <Tag color={stateColors[deployment.state] || 'default'}>
          {deployment.state.toUpperCase()}
        </Tag>
        <Space style={{ marginLeft: 'auto' }}>
          <ClockCircleOutlined style={{ color: '#6b6b8a' }} />
          <Text type="secondary">{formatUptime(deployment.uptime_seconds)}</Text>
        </Space>
      </div>
    }
    headStyle={{ borderBottom: '1px solid #2d2d52' }}
  >
    <Row gutter={[24, 16]}>
      {/* Protocol Breakdown Chart */}
      <Col xs={24} md={10}>
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
          Protocol Breakdown
        </Text>
        <ProtocolBreakdownChart breakdown={deployment.protocol_breakdown} />
      </Col>

      {/* Packet Rate Sparkline */}
      <Col xs={24} md={14}>
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
          Packet Rate (last 5 min)
        </Text>
        <PacketRateSparkline timeSeries={deployment.time_series} />
      </Col>
    </Row>

    {/* Attack Timeline */}
    {deployment.attack && (deployment.attack.is_active || deployment.attack.is_completed) && (
      <div style={{ marginTop: 12, padding: '8px 12px', background: '#1a0d0d', borderRadius: 6, border: '1px solid #3d1f1f' }}>
        <KillChainTimeline
          scenarioId={deployment.scenario_id}
          isRunning={deployment.state === 'running'}
          attackState={deployment.attack}
        />
      </div>
    )}

    {/* Footer Stats */}
    <Row gutter={[16, 8]} style={{ marginTop: 16, borderTop: '1px solid #2d2d52', paddingTop: 16 }}>
      <Col xs={12} sm={8} md={4}>
        <Statistic
          title="Packets/sec"
          value={formatPacketRate(deployment.packets_per_second)}
          suffix="pkt/s"
          prefix={<SwapOutlined />}
          valueStyle={{ color: '#1890ff', fontSize: 16 }}
          style={{ textAlign: 'center' }}
        />
      </Col>
      <Col xs={12} sm={8} md={4}>
        <Statistic
          title="Bandwidth"
          value={formatBandwidth(deployment.bytes_per_second)}
          valueStyle={{ color: '#52c41a', fontSize: 16 }}
          style={{ textAlign: 'center' }}
        />
      </Col>
      <Col xs={12} sm={8} md={4}>
        <Statistic
          title="Total Packets"
          value={formatNumber(deployment.packets_sent)}
          prefix={<FileTextOutlined />}
          valueStyle={{ color: '#722ed1', fontSize: 16 }}
          style={{ textAlign: 'center' }}
        />
      </Col>
      <Col xs={12} sm={8} md={4}>
        <Statistic
          title="Total Bytes"
          value={formatBytes(deployment.bytes_sent)}
          valueStyle={{ color: '#fa8c16', fontSize: 16 }}
          style={{ textAlign: 'center' }}
        />
      </Col>
      <Col xs={12} sm={8} md={4}>
        <Statistic
          title="Flows"
          value={deployment.flow_count}
          valueStyle={{ color: '#13c2c2', fontSize: 16 }}
          style={{ textAlign: 'center' }}
        />
      </Col>
    </Row>
  </Card>
);

export default DeploymentCard;
