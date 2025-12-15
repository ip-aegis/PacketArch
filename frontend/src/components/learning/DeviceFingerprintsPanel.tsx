/**
 * Device Fingerprints Panel - View learned device signatures
 */

import React, { useState } from 'react';
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
  Descriptions,
  Badge,
} from 'antd';
import {
  FilterOutlined,
  ReloadOutlined,
  DesktopOutlined,
  WifiOutlined,
  ClockCircleOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import {
  listDeviceFingerprints,
  getDeviceFingerprint,
  type DeviceFingerprint,
} from '../../api/learning';

const { Text } = Typography;

interface DeviceFingerprintsPanelProps {
  onSelectFingerprint?: (fingerprint: DeviceFingerprint) => void;
}

const roleColors: Record<string, string> = {
  master: 'blue',
  slave: 'green',
  both: 'purple',
  unknown: 'default',
};

const DeviceFingerprintsPanel: React.FC<DeviceFingerprintsPanelProps> = ({
  onSelectFingerprint,
}) => {
  const [selectedRole, setSelectedRole] = useState<string | undefined>();
  const [selectedProtocol, setSelectedProtocol] = useState<string | undefined>();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['device-fingerprints', selectedRole, selectedProtocol],
    queryFn: () =>
      listDeviceFingerprints({
        page_size: 100,
        role: selectedRole,
        protocol: selectedProtocol,
      }),
  });

  const { data: fingerprintDetail, isLoading: loadingDetail } = useQuery({
    queryKey: ['device-fingerprint', expandedId],
    queryFn: () => (expandedId ? getDeviceFingerprint(expandedId) : null),
    enabled: !!expandedId,
  });

  const fingerprints = data?.fingerprints || [];

  const renderTcpSignature = (tcpSig: Record<string, unknown> | null) => {
    if (!tcpSig) return null;

    return (
      <Descriptions
        size="small"
        column={2}
        style={{ marginTop: 8 }}
        labelStyle={{ color: '#6a8caf', fontSize: 10 }}
        contentStyle={{ color: '#c9d1d9', fontSize: 10 }}
      >
        {tcpSig.ttl && (
          <Descriptions.Item label="TTL">{String(tcpSig.ttl)}</Descriptions.Item>
        )}
        {tcpSig.window_size && (
          <Descriptions.Item label="Window Size">
            {Number(tcpSig.window_size).toLocaleString()}
          </Descriptions.Item>
        )}
        {tcpSig.mss && (
          <Descriptions.Item label="MSS">{String(tcpSig.mss)}</Descriptions.Item>
        )}
        {tcpSig.df_flag !== undefined && (
          <Descriptions.Item label="DF Flag">
            {tcpSig.df_flag ? 'Yes' : 'No'}
          </Descriptions.Item>
        )}
        {tcpSig.options && Array.isArray(tcpSig.options) && (
          <Descriptions.Item label="Options" span={2}>
            <Space size={4} wrap>
              {(tcpSig.options as string[]).map((opt, i) => (
                <Tag key={i} style={{ fontSize: 9 }}>
                  {opt}
                </Tag>
              ))}
            </Space>
          </Descriptions.Item>
        )}
      </Descriptions>
    );
  };

  const renderResponseTimings = (timings: Record<string, unknown> | null) => {
    if (!timings) return null;

    return (
      <div style={{ marginTop: 8 }}>
        <Text style={{ fontSize: 10, color: '#8aa4bc', display: 'block', marginBottom: 4 }}>
          Response Timings by Protocol
        </Text>
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          {Object.entries(timings).map(([protocol, timing]) => {
            const t = timing as Record<string, number>;
            return (
              <div
                key={protocol}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  background: '#0d1117',
                  padding: '4px 8px',
                  borderRadius: 4,
                }}
              >
                <Tag style={{ fontSize: 9 }}>{protocol}</Tag>
                <Space size={8}>
                  <Text style={{ fontSize: 9, color: '#6a8caf' }}>
                    Mean: {t.mean_ms?.toFixed(2) || '-'}ms
                  </Text>
                  <Text style={{ fontSize: 9, color: '#4a6a8a' }}>
                    ({t.min_ms?.toFixed(1) || '-'} - {t.max_ms?.toFixed(1) || '-'}ms)
                  </Text>
                </Space>
              </div>
            );
          })}
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
            placeholder="Device Role"
            style={{ width: 150 }}
            size="small"
            allowClear
            value={selectedRole}
            onChange={setSelectedRole}
            options={[
              { value: 'master', label: 'Master' },
              { value: 'slave', label: 'Slave' },
              { value: 'both', label: 'Both' },
            ]}
          />
          <Select
            placeholder="Protocol"
            style={{ width: 150 }}
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

      {/* Fingerprints List */}
      <Card
        size="small"
        title={
          <Space>
            <SafetyCertificateOutlined />
            <span>Device Fingerprints</span>
            <Tag>{fingerprints.length}</Tag>
          </Space>
        }
        style={{ background: '#1a2734' }}
        styles={{ body: { padding: '8px' } }}
      >
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
          </div>
        ) : fingerprints.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Text style={{ color: '#6a8caf', fontSize: 11 }}>
                No device fingerprints found. Upload PCAPs to extract device signatures.
              </Text>
            }
          />
        ) : (
          <List
            dataSource={fingerprints}
            size="small"
            renderItem={(fp) => (
              <div
                key={fp.id}
                style={{
                  background: '#0d1117',
                  borderRadius: 4,
                  marginBottom: 4,
                  border: expandedId === fp.id ? '1px solid #5a9fd4' : '1px solid transparent',
                  cursor: 'pointer',
                }}
                onClick={() => setExpandedId(expandedId === fp.id ? null : fp.id)}
              >
                <div style={{ padding: '8px 12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Space direction="vertical" size={2}>
                      <Space size={8}>
                        <DesktopOutlined style={{ color: '#5a9fd4' }} />
                        <Text style={{ fontSize: 12, color: '#c9d1d9', fontFamily: 'monospace' }}>
                          {fp.ip_address}
                        </Text>
                        <Tag color={roleColors[fp.role]} style={{ fontSize: 9 }}>
                          {fp.role.toUpperCase()}
                        </Tag>
                      </Space>
                      <Space size={8}>
                        {fp.inferred_vendor && (
                          <Text style={{ fontSize: 10, color: '#8aa4bc' }}>
                            {fp.inferred_vendor}
                          </Text>
                        )}
                        {fp.mac_address && (
                          <Text style={{ fontSize: 10, color: '#4a6a8a', fontFamily: 'monospace' }}>
                            {fp.mac_address}
                          </Text>
                        )}
                      </Space>
                    </Space>
                    <Space direction="vertical" size={2} style={{ alignItems: 'flex-end' }}>
                      {fp.tcp_signature && (
                        <Tooltip title="Has TCP fingerprint">
                          <Badge status="success" text={<Text style={{ fontSize: 9, color: '#6a8caf' }}>TCP Sig</Text>} />
                        </Tooltip>
                      )}
                      {fp.response_timings && (
                        <Tooltip title="Has response timing data">
                          <Badge status="processing" text={<Text style={{ fontSize: 9, color: '#6a8caf' }}>Timing</Text>} />
                        </Tooltip>
                      )}
                    </Space>
                  </div>

                  {/* Protocol tags */}
                  {fp.active_protocols && fp.active_protocols.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      <Space size={4}>
                        <WifiOutlined style={{ color: '#6a8caf', fontSize: 10 }} />
                        {fp.active_protocols.map((proto) => (
                          <Tag key={proto} style={{ fontSize: 9 }}>
                            {proto}
                          </Tag>
                        ))}
                      </Space>
                    </div>
                  )}
                </div>

                {/* Expanded Detail */}
                {expandedId === fp.id && (
                  <div
                    style={{
                      borderTop: '1px solid #2a3f54',
                      padding: '12px',
                      background: '#0a0f14',
                    }}
                  >
                    {loadingDetail ? (
                      <Spin size="small" />
                    ) : fingerprintDetail ? (
                      <Space direction="vertical" style={{ width: '100%' }} size="small">
                        {/* TCP Signature */}
                        {fingerprintDetail.tcp_signature && (
                          <div>
                            <Text style={{ fontSize: 10, color: '#8aa4bc', display: 'block', marginBottom: 4 }}>
                              <SafetyCertificateOutlined /> TCP Stack Signature
                            </Text>
                            {renderTcpSignature(fingerprintDetail.tcp_signature)}
                          </div>
                        )}

                        {/* Response Timings */}
                        {fingerprintDetail.response_timings && (
                          <div>
                            <ClockCircleOutlined style={{ color: '#8aa4bc', marginRight: 4 }} />
                            {renderResponseTimings(fingerprintDetail.response_timings)}
                          </div>
                        )}

                        {/* Communication Partners */}
                        {fingerprintDetail.communication_partners &&
                          fingerprintDetail.communication_partners.length > 0 && (
                            <div style={{ marginTop: 8 }}>
                              <Text style={{ fontSize: 10, color: '#8aa4bc', display: 'block', marginBottom: 4 }}>
                                Communication Partners
                              </Text>
                              <Space wrap size={4}>
                                {fingerprintDetail.communication_partners.slice(0, 10).map((ip) => (
                                  <Tag key={ip} style={{ fontSize: 9, fontFamily: 'monospace' }}>
                                    {ip}
                                  </Tag>
                                ))}
                                {fingerprintDetail.communication_partners.length > 10 && (
                                  <Text style={{ fontSize: 9, color: '#4a6a8a' }}>
                                    +{fingerprintDetail.communication_partners.length - 10} more
                                  </Text>
                                )}
                              </Space>
                            </div>
                          )}

                        {onSelectFingerprint && (
                          <Button
                            type="primary"
                            size="small"
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectFingerprint(fp);
                            }}
                            style={{ marginTop: 8 }}
                          >
                            Apply Fingerprint
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

export default DeviceFingerprintsPanel;
