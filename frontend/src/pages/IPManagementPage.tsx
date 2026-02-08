/**
 * IP Management Page - View all scenario IP range allocations
 */

import React, { useEffect, useState } from 'react';
import {
  Table,
  Tag,
  Button,
  Space,
  Typography,
  Card,
  Progress,
  Statistic,
  Row,
  Col,
  message,
} from 'antd';
import {
  GlobalOutlined,
  LinkOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ClusterOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import { ipManagementApi, type IPRangeAllocation } from '../api/ipManagement';
import { TEXT_PARAGRAPH, TEXT_MUTED, BG_PANEL, BORDER_DEFAULT } from '../constants/theme';

const { Title, Text } = Typography;

const MAX_RANGES = 254; // 10.1.0.0/16 to 10.254.0.0/16

const IPManagementPage: React.FC = () => {
  const navigate = useNavigate();
  const [allocations, setAllocations] = useState<IPRangeAllocation[]>([]);
  const [availableRanges, setAvailableRanges] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchAllocations = async () => {
    setIsLoading(true);
    try {
      const response = await ipManagementApi.listAllocations();
      setAllocations(response.items);
      setAvailableRanges(response.available_ranges);
    } catch (error) {
      message.error('Failed to fetch IP allocations');
      console.error('Failed to fetch IP allocations:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAllocations();
  }, []);

  const usagePercent = Math.round((allocations.length / MAX_RANGES) * 100);

  const columns: ColumnsType<IPRangeAllocation> = [
    {
      title: 'Index',
      dataIndex: 'range_index',
      key: 'range_index',
      width: 80,
      sorter: (a, b) => a.range_index - b.range_index,
      render: (index: number) => (
        <Tag color="blue">{index}</Tag>
      ),
    },
    {
      title: 'IP Range',
      dataIndex: 'cidr_range',
      key: 'cidr_range',
      width: 160,
      render: (cidr: string) => (
        <Text code style={{ color: '#52c41a' }}>{cidr}</Text>
      ),
    },
    {
      title: 'Scenario',
      dataIndex: 'scenario_name',
      key: 'scenario_name',
      render: (name: string, record: IPRangeAllocation) => (
        <Button
          type="link"
          size="small"
          icon={<LinkOutlined />}
          onClick={() => navigate(`/studio?scenario=${record.scenario_id}`)}
          style={{ padding: 0 }}
        >
          {name || 'Unknown'}
        </Button>
      ),
    },
    {
      title: 'Next Host Offset',
      dataIndex: 'next_host_offset',
      key: 'next_host_offset',
      width: 140,
      render: (offset: number, record: IPRangeAllocation) => {
        // Calculate next IP from offset
        const subnet = Math.floor(offset / 256);
        let host = offset % 256;
        if (host === 0) host = 1;
        const nextIP = `10.${record.range_index}.${subnet}.${host}`;
        return (
          <Space direction="vertical" size={0}>
            <Text style={{ color: TEXT_PARAGRAPH, fontSize: 12 }}>
              Offset: {offset}
            </Text>
            <Text style={{ color: TEXT_MUTED, fontSize: 11 }}>
              Next: {nextIP}
            </Text>
          </Space>
        );
      },
    },
    {
      title: 'Allocated',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (ts: string) => (
        <Text style={{ color: TEXT_MUTED, fontSize: 12 }}>
          {new Date(ts).toLocaleString()}
        </Text>
      ),
      sorter: (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      defaultSortOrder: 'descend',
    },
  ];

  return (
    <div style={{ padding: '0 0 24px 0' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ color: '#fff', marginBottom: 8 }}>
          <GlobalOutlined style={{ marginRight: 12 }} />
          IP Management
        </Title>
        <Text style={{ color: TEXT_PARAGRAPH }}>
          View scenario IP range allocations and prevent address conflicts
        </Text>
      </div>

      {/* Summary Cards */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card
            style={{ background: BG_PANEL, border: `1px solid ${BORDER_DEFAULT}` }}
            styles={{ body: { padding: 16 } }}
          >
            <Statistic
              title={<Text style={{ color: TEXT_MUTED }}>Allocated Ranges</Text>}
              value={allocations.length}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              valueStyle={{ color: '#fff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card
            style={{ background: BG_PANEL, border: `1px solid ${BORDER_DEFAULT}` }}
            styles={{ body: { padding: 16 } }}
          >
            <Statistic
              title={<Text style={{ color: TEXT_MUTED }}>Available Ranges</Text>}
              value={availableRanges.length}
              prefix={<ClusterOutlined style={{ color: '#1890ff' }} />}
              valueStyle={{ color: '#fff' }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card
            style={{ background: BG_PANEL, border: `1px solid ${BORDER_DEFAULT}` }}
            styles={{ body: { padding: 16 } }}
          >
            <div style={{ marginBottom: 8 }}>
              <Text style={{ color: TEXT_MUTED }}>
                IP Range Usage ({allocations.length} / {MAX_RANGES})
              </Text>
            </div>
            <Progress
              percent={usagePercent}
              strokeColor={{
                '0%': '#1890ff',
                '100%': '#52c41a',
              }}
              trailColor={BORDER_DEFAULT}
              format={(percent) => (
                <span style={{ color: '#fff' }}>{percent}%</span>
              )}
            />
            <Text style={{ color: TEXT_MUTED, fontSize: 12 }}>
              Each scenario receives a unique 10.{'{n}'}.0.0/16 range (n = 1-254)
            </Text>
          </Card>
        </Col>
      </Row>

      {/* Allocations Table */}
      <Card
        style={{ background: BG_PANEL, border: `1px solid ${BORDER_DEFAULT}` }}
        styles={{ body: { padding: '16px 24px' } }}
      >
        <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchAllocations}
            loading={isLoading}
          >
            Refresh
          </Button>
          <div style={{ flex: 1 }} />
          <Text style={{ color: TEXT_MUTED, fontSize: 12 }}>
            {allocations.length} allocation{allocations.length !== 1 ? 's' : ''}
          </Text>
        </div>

        <Table
          columns={columns}
          dataSource={allocations}
          rowKey="id"
          loading={isLoading}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `${total} allocations`,
          }}
          size="middle"
          style={{
            background: 'transparent',
          }}
          locale={{
            emptyText: (
              <div style={{ padding: 48, textAlign: 'center' }}>
                <GlobalOutlined style={{ fontSize: 48, color: TEXT_MUTED, marginBottom: 16 }} />
                <div>
                  <Text style={{ color: TEXT_PARAGRAPH }}>
                    No IP ranges allocated yet
                  </Text>
                </div>
                <div>
                  <Text style={{ color: TEXT_MUTED, fontSize: 12 }}>
                    IP ranges are automatically allocated when you create a new scenario
                  </Text>
                </div>
              </div>
            ),
          }}
        />
      </Card>

      {/* Info Section */}
      <Card
        style={{ background: BG_PANEL, border: `1px solid ${BORDER_DEFAULT}`, marginTop: 16 }}
        styles={{ body: { padding: 16 } }}
      >
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          How IP Range Allocation Works
        </Title>
        <Row gutter={24}>
          <Col span={8}>
            <Text strong style={{ color: '#52c41a' }}>Automatic Allocation</Text>
            <div>
              <Text style={{ color: TEXT_PARAGRAPH, fontSize: 12 }}>
                When you create a scenario, a unique /16 IP range is automatically assigned from the 10.x.0.0/8 private address space.
              </Text>
            </div>
          </Col>
          <Col span={8}>
            <Text strong style={{ color: '#1890ff' }}>Device IP Assignment</Text>
            <div>
              <Text style={{ color: TEXT_PARAGRAPH, fontSize: 12 }}>
                When you drop a device on the canvas (for a saved scenario), an IP address from that scenario's range is automatically assigned.
              </Text>
            </div>
          </Col>
          <Col span={8}>
            <Text strong style={{ color: '#fa8c16' }}>No Conflicts</Text>
            <div>
              <Text style={{ color: TEXT_PARAGRAPH, fontSize: 12 }}>
                Each scenario has its own /16 range, ensuring devices in different scenarios never have IP address conflicts.
              </Text>
            </div>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default IPManagementPage;
