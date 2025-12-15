/**
 * Protocol Patterns Panel - View deep protocol analysis patterns
 */

import React, { useCallback, useState } from 'react';
import {
  Card,
  Space,
  Typography,
  Tag,
  Button,
  Select,
  List,
  Empty,
  Spin,
  Tooltip,
  Progress,
  message,
  Descriptions,
} from 'antd';
import {
  CodeOutlined,
  FilterOutlined,
  ReloadOutlined,
  DatabaseOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import {
  listProtocolPatterns,
  getProtocolPattern,
  type ProtocolPattern,
} from '../../api/learning';

const { Text } = Typography;

interface ProtocolPatternsPanelProps {
  onSelectPattern?: (pattern: ProtocolPattern) => void;
}

const protocolColors: Record<string, string> = {
  modbus: '#1890ff',
  modbus_tcp: '#1890ff',
  s7: '#52c41a',
  s7comm: '#52c41a',
  ethernet_ip: '#722ed1',
  profinet: '#eb2f96',
  dnp3: '#fa8c16',
  opc_ua: '#13c2c2',
};

const ProtocolPatternsPanel: React.FC<ProtocolPatternsPanelProps> = ({
  onSelectPattern,
}) => {
  const [selectedProtocol, setSelectedProtocol] = useState<string | undefined>();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['protocol-patterns', selectedProtocol],
    queryFn: () => listProtocolPatterns({ page_size: 100, protocol: selectedProtocol }),
  });

  const { data: patternDetail, isLoading: loadingDetail } = useQuery({
    queryKey: ['protocol-pattern', expandedId],
    queryFn: () => (expandedId ? getProtocolPattern(expandedId) : null),
    enabled: !!expandedId,
  });

  const patterns = data?.patterns || [];

  const renderFunctionCodeChart = (functionCodes: Record<string, unknown> | null) => {
    if (!functionCodes) return null;

    const frequency = (functionCodes as Record<string, Record<string, number>>).frequency || functionCodes;
    if (typeof frequency !== 'object') return null;

    const entries = Object.entries(frequency as Record<string, number>)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 8);

    const total = entries.reduce((sum, [, count]) => sum + count, 0);

    return (
      <div style={{ marginTop: 8 }}>
        <Text style={{ fontSize: 10, color: '#8aa4bc', display: 'block', marginBottom: 4 }}>
          Function Code Distribution
        </Text>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {entries.map(([fc, count]) => (
            <div key={fc} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Text style={{ fontSize: 10, color: '#6a8caf', width: 40 }}>
                FC {fc}
              </Text>
              <Progress
                percent={Math.round((count / total) * 100)}
                size="small"
                strokeColor="#5a9fd4"
                style={{ flex: 1, margin: 0 }}
                format={(p) => `${p}%`}
              />
              <Text style={{ fontSize: 9, color: '#4a6a8a', width: 40 }}>
                {count}x
              </Text>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderAddressPatterns = (addressPatterns: Record<string, unknown> | null) => {
    if (!addressPatterns) return null;

    const ranges = (addressPatterns as Record<string, unknown>).register_ranges ||
      (addressPatterns as Record<string, unknown>).ranges || [];

    if (!Array.isArray(ranges) || ranges.length === 0) return null;

    return (
      <div style={{ marginTop: 8 }}>
        <Text style={{ fontSize: 10, color: '#8aa4bc', display: 'block', marginBottom: 4 }}>
          Register Ranges Accessed
        </Text>
        <Space wrap>
          {(ranges as Array<{ start?: number; end?: number; min?: number; max?: number }>)
            .slice(0, 6)
            .map((range, i) => (
              <Tag key={i} style={{ fontSize: 9 }}>
                {range.start ?? range.min}-{range.end ?? range.max}
              </Tag>
            ))}
        </Space>
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Filters */}
      <Card
        size="small"
        title={
          <Space>
            <FilterOutlined />
            <span>Filters</span>
          </Space>
        }
        style={{ background: '#1a2734' }}
        styles={{ body: { padding: '12px' } }}
      >
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Select
            placeholder="Filter by Protocol"
            style={{ width: 200 }}
            size="small"
            allowClear
            value={selectedProtocol}
            onChange={setSelectedProtocol}
            options={[
              { value: 'modbus', label: 'Modbus' },
              { value: 's7', label: 'S7comm' },
              { value: 'ethernet_ip', label: 'EtherNet/IP' },
              { value: 'profinet', label: 'PROFINET' },
              { value: 'dnp3', label: 'DNP3' },
              { value: 'opc_ua', label: 'OPC UA' },
            ]}
          />
          <Button
            type="text"
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => refetch()}
          >
            Refresh
          </Button>
        </div>
      </Card>

      {/* Patterns List */}
      <Card
        size="small"
        title={
          <Space>
            <CodeOutlined />
            <span>Protocol Patterns</span>
            <Tag>{patterns.length}</Tag>
          </Space>
        }
        style={{ background: '#1a2734' }}
        styles={{ body: { padding: '8px' } }}
      >
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
          </div>
        ) : patterns.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Text style={{ color: '#6a8caf', fontSize: 11 }}>
                No protocol patterns found. Upload PCAPs to extract protocol-specific patterns.
              </Text>
            }
          />
        ) : (
          <List
            dataSource={patterns}
            size="small"
            renderItem={(pattern) => (
              <div
                key={pattern.id}
                style={{
                  background: '#0d1117',
                  borderRadius: 4,
                  marginBottom: 4,
                  border: expandedId === pattern.id ? '1px solid #5a9fd4' : '1px solid transparent',
                  cursor: 'pointer',
                }}
                onClick={() => setExpandedId(expandedId === pattern.id ? null : pattern.id)}
              >
                <div style={{ padding: '8px 12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Space direction="vertical" size={2}>
                      <Space size={4}>
                        <Tag
                          color={protocolColors[pattern.protocol] || 'default'}
                          style={{ fontSize: 10 }}
                        >
                          {pattern.protocol.toUpperCase()}
                        </Tag>
                        <Text style={{ fontSize: 11, color: '#c9d1d9' }}>
                          {pattern.sample_count.toLocaleString()} packets analyzed
                        </Text>
                      </Space>
                      <Space size={8}>
                        {pattern.function_codes && (
                          <Tooltip title="Has function code distribution">
                            <Tag icon={<BarChartOutlined />} style={{ fontSize: 9 }}>
                              Function Codes
                            </Tag>
                          </Tooltip>
                        )}
                        {pattern.address_patterns && (
                          <Tooltip title="Has address/register patterns">
                            <Tag icon={<DatabaseOutlined />} style={{ fontSize: 9 }}>
                              Addresses
                            </Tag>
                          </Tooltip>
                        )}
                      </Space>
                    </Space>
                    <Text style={{ fontSize: 9, color: '#4a6a8a' }}>
                      {new Date(pattern.created_at).toLocaleDateString()}
                    </Text>
                  </div>

                  {/* Inline preview */}
                  {expandedId !== pattern.id && pattern.function_codes && (
                    <div style={{ marginTop: 8 }}>
                      <Space size={4}>
                        {Object.keys(
                          ((pattern.function_codes as Record<string, unknown>).frequency as Record<string, number>) ||
                          pattern.function_codes
                        )
                          .slice(0, 5)
                          .map((fc) => (
                            <Tag key={fc} style={{ fontSize: 9 }}>
                              FC {fc}
                            </Tag>
                          ))}
                        {Object.keys(
                          ((pattern.function_codes as Record<string, unknown>).frequency as Record<string, number>) ||
                          pattern.function_codes
                        ).length > 5 && (
                          <Text style={{ fontSize: 9, color: '#4a6a8a' }}>
                            +{Object.keys(
                              ((pattern.function_codes as Record<string, unknown>).frequency as Record<string, number>) ||
                              pattern.function_codes
                            ).length - 5} more
                          </Text>
                        )}
                      </Space>
                    </div>
                  )}
                </div>

                {/* Expanded Detail */}
                {expandedId === pattern.id && (
                  <div
                    style={{
                      borderTop: '1px solid #2a3f54',
                      padding: '12px',
                      background: '#0a0f14',
                    }}
                  >
                    {loadingDetail ? (
                      <Spin size="small" />
                    ) : patternDetail ? (
                      <Space direction="vertical" style={{ width: '100%' }} size="small">
                        {renderFunctionCodeChart(patternDetail.function_codes)}
                        {renderAddressPatterns(patternDetail.address_patterns)}

                        {patternDetail.unit_id_distribution && (
                          <div style={{ marginTop: 8 }}>
                            <Text style={{ fontSize: 10, color: '#8aa4bc' }}>
                              Unit IDs: {Object.keys(patternDetail.unit_id_distribution).join(', ')}
                            </Text>
                          </div>
                        )}

                        {patternDetail.exception_patterns && (
                          <div style={{ marginTop: 8 }}>
                            <Text style={{ fontSize: 10, color: '#fa8c16' }}>
                              Exception codes observed in traffic
                            </Text>
                          </div>
                        )}

                        {onSelectPattern && (
                          <Button
                            type="primary"
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectPattern(pattern);
                            }}
                            style={{ marginTop: 8 }}
                          >
                            Select Pattern
                          </Button>
                        )}
                      </Space>
                    ) : null}
                  </div>
                )}
              </div>
            )}
          />
        )}
      </Card>
    </div>
  );
};

export default ProtocolPatternsPanel;
