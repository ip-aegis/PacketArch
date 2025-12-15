/**
 * Learned Sequences Panel - View learned operation sequences
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
  Progress,
  Timeline,
} from 'antd';
import {
  FilterOutlined,
  ReloadOutlined,
  OrderedListOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  PlayCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import {
  listSequences,
  getSequence,
  type LearnedSequence,
} from '../../api/learning';

const { Text } = Typography;

interface LearnedSequencesPanelProps {
  onSelectSequence?: (sequence: LearnedSequence) => void;
}

const sequenceTypeConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  startup: { color: 'green', icon: <PlayCircleOutlined />, label: 'Startup' },
  shutdown: { color: 'red', icon: <StopOutlined />, label: 'Shutdown' },
  poll_cycle: { color: 'blue', icon: <SyncOutlined />, label: 'Poll Cycle' },
  write_sequence: { color: 'orange', icon: <OrderedListOutlined />, label: 'Write Sequence' },
  error_recovery: { color: 'volcano', icon: <ClockCircleOutlined />, label: 'Error Recovery' },
  state_transition: { color: 'purple', icon: <OrderedListOutlined />, label: 'State Transition' },
  heartbeat: { color: 'cyan', icon: <SyncOutlined />, label: 'Heartbeat' },
  alarm: { color: 'magenta', icon: <ClockCircleOutlined />, label: 'Alarm' },
};

const LearnedSequencesPanel: React.FC<LearnedSequencesPanelProps> = ({
  onSelectSequence,
}) => {
  const [selectedType, setSelectedType] = useState<string | undefined>();
  const [selectedProtocol, setSelectedProtocol] = useState<string | undefined>();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['sequences', selectedType, selectedProtocol],
    queryFn: () =>
      listSequences({
        page_size: 100,
        sequence_type: selectedType,
        protocol: selectedProtocol,
      }),
  });

  const { data: sequenceDetail, isLoading: loadingDetail } = useQuery({
    queryKey: ['sequence', expandedId],
    queryFn: () => (expandedId ? getSequence(expandedId) : null),
    enabled: !!expandedId,
  });

  const sequences = data?.sequences || [];

  const renderSequenceSteps = (steps: Record<string, unknown> | null) => {
    if (!steps) return null;

    const stepArray = (steps as Record<string, unknown>).steps || steps;
    if (!Array.isArray(stepArray)) return null;

    return (
      <Timeline
        style={{ marginTop: 8, marginLeft: 8 }}
        items={stepArray.slice(0, 10).map((step, i) => {
          const s = step as Record<string, unknown>;
          return {
            color: i === 0 ? 'green' : i === stepArray.length - 1 ? 'red' : 'blue',
            children: (
              <div style={{ fontSize: 10 }}>
                <Text style={{ color: '#c9d1d9' }}>
                  {s.action || s.type || s.function_code ? `FC ${s.function_code}` : `Step ${i + 1}`}
                </Text>
                {s.delay_ms && (
                  <Text style={{ color: '#4a6a8a', marginLeft: 8 }}>
                    +{Number(s.delay_ms).toFixed(0)}ms
                  </Text>
                )}
              </div>
            ),
          };
        })}
      />
    );
  };

  const getSequenceTypeInfo = (type: string) => {
    const cleanType = type.replace('SequenceType.', '').toLowerCase();
    return sequenceTypeConfig[cleanType] || { color: 'default', icon: <OrderedListOutlined />, label: type };
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
            placeholder="Sequence Type"
            style={{ width: 150 }}
            size="small"
            allowClear
            value={selectedType}
            onChange={setSelectedType}
            options={[
              { value: 'startup', label: 'Startup' },
              { value: 'shutdown', label: 'Shutdown' },
              { value: 'poll_cycle', label: 'Poll Cycle' },
              { value: 'write_sequence', label: 'Write Sequence' },
              { value: 'error_recovery', label: 'Error Recovery' },
              { value: 'heartbeat', label: 'Heartbeat' },
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

      {/* Sequences List */}
      <Card
        size="small"
        title={
          <Space>
            <OrderedListOutlined />
            <span>Learned Sequences</span>
            <Tag>{sequences.length}</Tag>
          </Space>
        }
        style={{ background: '#1a2734' }}
        styles={{ body: { padding: '8px' } }}
      >
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
          </div>
        ) : sequences.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Text style={{ color: '#6a8caf', fontSize: 11 }}>
                No sequences found. Upload PCAPs to extract operation sequences.
              </Text>
            }
          />
        ) : (
          <List
            dataSource={sequences}
            size="small"
            renderItem={(seq) => {
              const typeInfo = getSequenceTypeInfo(seq.sequence_type);
              return (
                <div
                  key={seq.id}
                  style={{
                    background: '#0d1117',
                    borderRadius: 4,
                    marginBottom: 4,
                    border: expandedId === seq.id ? '1px solid #5a9fd4' : '1px solid transparent',
                    cursor: 'pointer',
                  }}
                  onClick={() => setExpandedId(expandedId === seq.id ? null : seq.id)}
                >
                  <div style={{ padding: '8px 12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Space direction="vertical" size={2}>
                        <Space size={8}>
                          <Tag color={typeInfo.color} icon={typeInfo.icon} style={{ fontSize: 10 }}>
                            {typeInfo.label}
                          </Tag>
                          <Tag style={{ fontSize: 10 }}>{seq.protocol}</Tag>
                          <Text style={{ fontSize: 11, color: '#c9d1d9' }}>
                            {seq.name}
                          </Text>
                        </Space>
                        <Space size={12}>
                          <Text style={{ fontSize: 10, color: '#6a8caf' }}>
                            {seq.step_count} steps
                          </Text>
                          {seq.average_duration_ms && (
                            <Text style={{ fontSize: 10, color: '#6a8caf' }}>
                              ~{seq.average_duration_ms.toFixed(0)}ms duration
                            </Text>
                          )}
                          <Text style={{ fontSize: 10, color: '#4a6a8a' }}>
                            {seq.occurrence_count}x observed
                          </Text>
                        </Space>
                      </Space>
                      <Space direction="vertical" size={2} style={{ alignItems: 'flex-end' }}>
                        <Tooltip title={`Confidence: ${(seq.confidence * 100).toFixed(0)}%`}>
                          <Progress
                            type="circle"
                            percent={Math.round(seq.confidence * 100)}
                            size={24}
                            strokeWidth={10}
                            strokeColor={seq.confidence > 0.8 ? '#52c41a' : seq.confidence > 0.5 ? '#faad14' : '#ff4d4f'}
                            format={() => null}
                          />
                        </Tooltip>
                      </Space>
                    </div>

                    {/* Repetition info for poll cycles */}
                    {seq.repetition_interval_ms && (
                      <div style={{ marginTop: 4 }}>
                        <Text style={{ fontSize: 10, color: '#5a9fd4' }}>
                          <SyncOutlined style={{ marginRight: 4 }} />
                          Repeats every {seq.repetition_interval_ms.toFixed(0)}ms
                          {seq.repetition_jitter_ms && ` (±${seq.repetition_jitter_ms.toFixed(0)}ms)`}
                        </Text>
                      </div>
                    )}
                  </div>

                  {/* Expanded Detail */}
                  {expandedId === seq.id && (
                    <div
                      style={{
                        borderTop: '1px solid #2a3f54',
                        padding: '12px',
                        background: '#0a0f14',
                      }}
                    >
                      {loadingDetail ? (
                        <Spin size="small" />
                      ) : sequenceDetail ? (
                        <Space direction="vertical" style={{ width: '100%' }} size="small">
                          {/* Flow endpoints */}
                          {(sequenceDetail.initiator_ip || sequenceDetail.responder_ip) && (
                            <div>
                              <Text style={{ fontSize: 10, color: '#8aa4bc' }}>
                                Flow: {sequenceDetail.initiator_ip || '?'} → {sequenceDetail.responder_ip || '?'}
                              </Text>
                            </div>
                          )}

                          {/* Timing details */}
                          {sequenceDetail.timing_variance && (
                            <div>
                              <Text style={{ fontSize: 10, color: '#6a8caf' }}>
                                Timing variance: ±{sequenceDetail.timing_variance.toFixed(2)}ms
                              </Text>
                            </div>
                          )}

                          {/* Sequence Steps */}
                          {sequenceDetail.steps && (
                            <div>
                              <Text style={{ fontSize: 10, color: '#8aa4bc', display: 'block', marginBottom: 4 }}>
                                Sequence Steps
                              </Text>
                              {renderSequenceSteps(sequenceDetail.steps)}
                            </div>
                          )}

                          {onSelectSequence && (
                            <Button
                              type="primary"
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation();
                                onSelectSequence(seq);
                              }}
                              style={{ marginTop: 8 }}
                            >
                              Apply Sequence
                            </Button>
                          )}
                        </Space>
                      ) : null}
                    </div>
                  )}
                </div>
              );
            }}
          />
        )}
      </Card>
    </div>
  );
};

export default LearnedSequencesPanel;
