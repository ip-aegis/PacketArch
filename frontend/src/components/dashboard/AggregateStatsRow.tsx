import React from 'react';
import { Row, Col, Card, Statistic } from 'antd';
import {
  ThunderboltOutlined,
  DashboardOutlined,
  CloudServerOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import type { DashboardAggregate } from '../../api/dashboard';
import { formatPacketRate, formatBandwidth } from '../../utils/formatUtils';

interface AggregateStatsRowProps {
  aggregate: DashboardAggregate;
}

const cardStyle: React.CSSProperties = {
  background: '#1a1a2e',
  border: '1px solid #2d2d52',
};

const AggregateStatsRow: React.FC<AggregateStatsRowProps> = ({ aggregate }) => (
  <Row gutter={[16, 16]}>
    <Col xs={24} sm={12} lg={6}>
      <Card style={cardStyle}>
        <Statistic
          title="Packets/sec"
          value={formatPacketRate(aggregate.total_packets_per_second)}
          suffix="pkt/s"
          prefix={<ThunderboltOutlined />}
          valueStyle={{ color: '#1890ff' }}
        />
      </Card>
    </Col>
    <Col xs={24} sm={12} lg={6}>
      <Card style={cardStyle}>
        <Statistic
          title="Bandwidth"
          value={formatBandwidth(aggregate.total_bytes_per_second)}
          prefix={<DashboardOutlined />}
          valueStyle={{ color: '#52c41a' }}
        />
      </Card>
    </Col>
    <Col xs={24} sm={12} lg={6}>
      <Card style={cardStyle}>
        <Statistic
          title="Active Deployments"
          value={aggregate.active_deployments}
          prefix={<CloudServerOutlined />}
          valueStyle={{ color: '#722ed1' }}
        />
      </Card>
    </Col>
    <Col xs={24} sm={12} lg={6}>
      <Card style={cardStyle}>
        <Statistic
          title="Connected Agents"
          value={aggregate.connected_agents}
          prefix={<ApiOutlined />}
          valueStyle={{ color: '#fa8c16' }}
        />
      </Card>
    </Col>
  </Row>
);

export default AggregateStatsRow;
