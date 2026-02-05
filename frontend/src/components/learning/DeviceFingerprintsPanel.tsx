/**
 * Device Fingerprints Panel - View learned device signature templates
 *
 * Fingerprints are GENERIC TEMPLATES capturing vendor characteristics,
 * TCP signatures, and behavioral patterns - NOT specific device instances.
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
  Progress,
} from 'antd';
import {
  FilterOutlined,
  ReloadOutlined,
  DesktopOutlined,
  WifiOutlined,
  ClockCircleOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  CheckCircleOutlined,
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
  const [selectedDeviceType, setSelectedDeviceType] = useState<string | undefined>();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['device-fingerprints', selectedRole, selectedProtocol, selectedDeviceType],
    queryFn: () =>
      listDeviceFingerprints({
        page_size: 100,
        role: selectedRole,
        protocol: selectedProtocol,
        device_type: selectedDeviceType,
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
        {tcpSig.sack_permitted !== undefined && (
          <Descriptions.Item label="SACK">
            {tcpSig.sack_permitted ? 'Yes' : 'No'}
          </Descriptions.Item>
        )}
        {tcpSig.timestamps_enabled !== undefined && (
          <Descriptions.Item label="Timestamps">
            {tcpSig.timestamps_enabled ? 'Yes' : 'No'}
          </Descriptions.Item>
        )}
        {tcpSig.option_order && Array.isArray(tcpSig.option_order) && (
          <Descriptions.Item label="Options" span={2}>
            <Space size={4} wrap>
              {(tcpSig.option_order as string[]).map((opt, i) => (
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

  const renderProtocolIdentities = (identities: Record<string, unknown> | null) => {
    if (!identities || Object.keys(identities).length === 0) return null;

    return (
      <div style={{ marginTop: 8 }}>
        <Text style={{ fontSize: 10, color: '#8aa4bc', display: 'block', marginBottom: 4 }}>
          Protocol Identities (Vendor/Model/Firmware)
        </Text>
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          {Object.entries(identities).map(([protocol, identity]) => {
            const id = identity as Record<string, unknown>;
            return (
              <div
                key={protocol}
                style={{
                  background: '#0d1117',
                  padding: '4px 8px',
                  borderRadius: 4,
                }}
              >
                <Tag color="blue" style={{ fontSize: 9, marginBottom: 4 }}>{protocol}</Tag>
                <div style={{ paddingLeft: 8 }}>
                  {id.vendor && (
                    <Text style={{ fontSize: 9, color: '#c9d1d9', display: 'block' }}>
                      Vendor: {String(id.vendor)}
                    </Text>
                  )}
                  {id.product_code && (
                    <Text style={{ fontSize: 9, color: '#6a8caf', display: 'block' }}>
                      Product: {String(id.product_code)}
                    </Text>
                  )}
                  {id.firmware && (
                    <Text style={{ fontSize: 9, color: '#6a8caf', display: 'block' }}>
                      Firmware: {String(id.firmware)}
                    </Text>
                  )}
                  {id.model && (
                    <Text style={{ fontSize: 9, color: '#6a8caf', display: 'block' }}>
                      Model: {String(id.model)}
                    </Text>
                  )}
                </div>
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
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <Select
            placeholder="Device Type"
            style={{ width: 150 }}
            size="small"
            allowClear
            value={selectedDeviceType}
            onChange={setSelectedDeviceType}
            options={[
              { value: 'PLC', label: 'PLC' },
              { value: 'HMI', label: 'HMI' },
              { value: 'RTU', label: 'RTU' },
              { value: 'Drive', label: 'Drive' },
              { value: 'Controller', label: 'Controller' },
            ]}
          />
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
              { value: 'modbus_tcp', label: 'Modbus TCP' },
              { value: 's7comm', label: 'S7comm' },
              { value: 'ethernet_ip', label: 'EtherNet/IP' },
              { value: 'profinet', label: 'PROFINET' },
              { value: 'bacnet_ip', label: 'BACnet/IP' },
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
            <span>Fingerprint Templates</span>
            <Tag>{fingerprints.length}</Tag>
          </Space>
        }
        extra={
          <Text style={{ fontSize: 10, color: '#6a8caf' }}>
            Generic templates for applying to devices
          </Text>
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
                No fingerprint templates found. Upload PCAPs to extract device signatures.
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
                        <Text style={{ fontSize: 12, color: '#c9d1d9', fontWeight: 500 }}>
                          {fp.name || `${fp.inferred_vendor || 'Unknown'} ${fp.device_type || 'Device'}`}
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
                        {fp.device_type && (
                          <Tag style={{ fontSize: 9 }}>{fp.device_type}</Tag>
                        )}
                        {fp.oui_patterns && fp.oui_patterns.length > 0 && (
                          <Tooltip title={`OUI Patterns: ${fp.oui_patterns.join(', ')}`}>
                            <Text style={{ fontSize: 9, color: '#4a6a8a' }}>
                              {fp.oui_patterns.length} OUI{fp.oui_patterns.length > 1 ? 's' : ''}
                            </Text>
                          </Tooltip>
                        )}
                      </Space>
                    </Space>
                    <Space direction="vertical" size={2} style={{ alignItems: 'flex-end' }}>
                      <Space size={4}>
                        <Tooltip title={`${fp.observation_count} device(s) aggregated`}>
                          <Badge
                            count={fp.observation_count}
                            style={{ backgroundColor: '#52c41a' }}
                            size="small"
                          />
                        </Tooltip>
                        <Tooltip title={`Confidence: ${(fp.confidence * 100).toFixed(0)}%`}>
                          <Progress
                            type="circle"
                            percent={Math.round(fp.confidence * 100)}
                            width={24}
                            strokeWidth={10}
                            format={() => ''}
                          />
                        </Tooltip>
                      </Space>
                      <Space size={4}>
                        {fp.tcp_signature && (
                          <Tooltip title="Has TCP fingerprint">
                            <Badge status="success" text={<Text style={{ fontSize: 9, color: '#6a8caf' }}>TCP</Text>} />
                          </Tooltip>
                        )}
                        {fp.response_timings && (
                          <Tooltip title="Has response timing data">
                            <Badge status="processing" text={<Text style={{ fontSize: 9, color: '#6a8caf' }}>Timing</Text>} />
                          </Tooltip>
                        )}
                        {fp.protocol_identities && (
                          <Tooltip title="Has protocol identity info">
                            <Badge status="warning" text={<Text style={{ fontSize: 9, color: '#6a8caf' }}>Identity</Text>} />
                          </Tooltip>
                        )}
                      </Space>
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
                        {/* Aggregation Info */}
                        <div style={{ background: '#1a2734', padding: 8, borderRadius: 4 }}>
                          <Space size={16}>
                            <Tooltip title="Devices aggregated into this template">
                              <Space>
                                <TeamOutlined style={{ color: '#52c41a' }} />
                                <Text style={{ fontSize: 10, color: '#c9d1d9' }}>
                                  {fingerprintDetail.observation_count} device(s)
                                </Text>
                              </Space>
                            </Tooltip>
                            <Tooltip title="Total packets analyzed">
                              <Text style={{ fontSize: 10, color: '#6a8caf' }}>
                                {fingerprintDetail.total_packets_analyzed.toLocaleString()} packets
                              </Text>
                            </Tooltip>
                            <Tooltip title="Consistency score">
                              <Space>
                                <CheckCircleOutlined style={{ color: '#1890ff' }} />
                                <Text style={{ fontSize: 10, color: '#c9d1d9' }}>
                                  {(fingerprintDetail.consistency_score * 100).toFixed(0)}% consistent
                                </Text>
                              </Space>
                            </Tooltip>
                          </Space>
                        </div>

                        {/* TCP Signature */}
                        {fingerprintDetail.tcp_signature && (
                          <div>
                            <Text style={{ fontSize: 10, color: '#8aa4bc', display: 'block', marginBottom: 4 }}>
                              <SafetyCertificateOutlined /> TCP Stack Signature
                            </Text>
                            {renderTcpSignature(fingerprintDetail.tcp_signature)}
                          </div>
                        )}

                        {/* Protocol Identities */}
                        {fingerprintDetail.protocol_identities && (
                          renderProtocolIdentities(fingerprintDetail.protocol_identities)
                        )}

                        {/* Response Timings */}
                        {fingerprintDetail.response_timings && (
                          <div>
                            <ClockCircleOutlined style={{ color: '#8aa4bc', marginRight: 4 }} />
                            {renderResponseTimings(fingerprintDetail.response_timings)}
                          </div>
                        )}

                        {/* Typical Ports */}
                        {fingerprintDetail.typical_ports && (
                          <div style={{ marginTop: 8 }}>
                            <Text style={{ fontSize: 10, color: '#8aa4bc', display: 'block', marginBottom: 4 }}>
                              Typical Ports
                            </Text>
                            <Space wrap size={4}>
                              {fingerprintDetail.typical_ports.tcp?.map((port) => (
                                <Tag key={`tcp-${port}`} color="blue" style={{ fontSize: 9 }}>
                                  TCP:{port}
                                </Tag>
                              ))}
                              {fingerprintDetail.typical_ports.udp?.map((port) => (
                                <Tag key={`udp-${port}`} color="green" style={{ fontSize: 9 }}>
                                  UDP:{port}
                                </Tag>
                              ))}
                            </Space>
                          </div>
                        )}

                        {/* Tags */}
                        {fingerprintDetail.tags && fingerprintDetail.tags.length > 0 && (
                          <div style={{ marginTop: 8 }}>
                            <Text style={{ fontSize: 10, color: '#8aa4bc', display: 'block', marginBottom: 4 }}>
                              Tags
                            </Text>
                            <Space wrap size={4}>
                              {fingerprintDetail.tags.map((tag) => (
                                <Tag key={tag} style={{ fontSize: 9 }}>
                                  {tag}
                                </Tag>
                              ))}
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
                            Apply Fingerprint Template
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
