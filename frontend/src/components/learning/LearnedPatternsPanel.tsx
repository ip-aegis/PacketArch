/**
 * Learned Patterns Panel - Browse and apply learned traffic patterns
 */

import React, { useEffect, useState, useCallback } from 'react';
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
  Switch,
  Tooltip,
  Progress,
  Collapse,
  Divider,
  message,
} from 'antd';
import {
  LineChartOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  FilterOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import {
  listPatterns,
  togglePattern,
  getPattern,
  type LearnedPattern,
  type PatternDetail,
} from '../../api/learning';

const { Text, Title } = Typography;
const { Panel } = Collapse;

interface LearnedPatternsPanelProps {
  onApplyPattern?: (pattern: LearnedPattern) => void;
  filterProtocol?: string;
}

const patternTypeColors: Record<string, string> = {
  timing: 'blue',
  payload: 'purple',
  sequence: 'cyan',
  error: 'orange',
};

const distributionTypeLabels: Record<string, string> = {
  gaussian: 'Gaussian (Normal)',
  exponential: 'Exponential',
  uniform: 'Uniform',
  lognormal: 'Log-Normal',
  poisson: 'Poisson',
};

const LearnedPatternsPanel: React.FC<LearnedPatternsPanelProps> = ({
  onApplyPattern,
  filterProtocol,
}) => {
  const [patterns, setPatterns] = useState<LearnedPattern[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedProtocol, setSelectedProtocol] = useState<string | undefined>(filterProtocol);
  const [selectedType, setSelectedType] = useState<string | undefined>();
  const [showActiveOnly, setShowActiveOnly] = useState(true);
  const [expandedPattern, setExpandedPattern] = useState<string | null>(null);
  const [patternDetail, setPatternDetail] = useState<PatternDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Fetch patterns
  const fetchPatterns = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listPatterns({
        page_size: 100,
        protocol: selectedProtocol,
        pattern_type: selectedType,
        active_only: showActiveOnly,
      });
      setPatterns(data.patterns);
    } catch (err) {
      console.error('Failed to fetch patterns:', err);
      message.error('Failed to load patterns');
    } finally {
      setLoading(false);
    }
  }, [selectedProtocol, selectedType, showActiveOnly]);

  useEffect(() => {
    fetchPatterns();
  }, [fetchPatterns]);

  // Fetch pattern detail when expanded
  const handleExpandPattern = async (patternId: string) => {
    if (expandedPattern === patternId) {
      setExpandedPattern(null);
      setPatternDetail(null);
      return;
    }

    setExpandedPattern(patternId);
    setLoadingDetail(true);
    try {
      const detail = await getPattern(patternId);
      setPatternDetail(detail);
    } catch (err) {
      console.error('Failed to fetch pattern detail:', err);
      message.error('Failed to load pattern details');
    } finally {
      setLoadingDetail(false);
    }
  };

  // Toggle pattern active state
  const handleTogglePattern = async (patternId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const result = await togglePattern(patternId);
      setPatterns((prev) =>
        prev.map((p) =>
          p.id === patternId ? { ...p, is_active: result.is_active } : p
        )
      );
      message.success(`Pattern ${result.is_active ? 'activated' : 'deactivated'}`);
    } catch (err) {
      console.error('Failed to toggle pattern:', err);
      message.error('Failed to toggle pattern');
    }
  };

  // Get unique protocols from patterns
  const uniqueProtocols = [...new Set(patterns.map((p) => p.protocol))];

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
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          <div style={{ display: 'flex', gap: 8 }}>
            <Select
              placeholder="Protocol"
              style={{ flex: 1 }}
              size="small"
              allowClear
              value={selectedProtocol}
              onChange={setSelectedProtocol}
              options={[
                { value: 'modbus_tcp', label: 'Modbus TCP' },
                { value: 'ethernet_ip', label: 'EtherNet/IP' },
                { value: 'profinet', label: 'PROFINET' },
                { value: 'opc_ua', label: 'OPC UA' },
                { value: 'dnp3', label: 'DNP3' },
              ]}
            />
            <Select
              placeholder="Type"
              style={{ flex: 1 }}
              size="small"
              allowClear
              value={selectedType}
              onChange={setSelectedType}
              options={[
                { value: 'timing', label: 'Timing' },
                { value: 'payload', label: 'Payload' },
                { value: 'sequence', label: 'Sequence' },
                { value: 'error', label: 'Error' },
              ]}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <Text style={{ fontSize: 11, color: '#6a8caf' }}>Active only</Text>
              <Switch
                size="small"
                checked={showActiveOnly}
                onChange={setShowActiveOnly}
              />
            </Space>
            <Button
              type="text"
              size="small"
              icon={<ReloadOutlined />}
              onClick={fetchPatterns}
            >
              Refresh
            </Button>
          </div>
        </Space>
      </Card>

      {/* Patterns List */}
      <Card
        size="small"
        title={
          <Space>
            <LineChartOutlined />
            <span>Learned Patterns</span>
            <Tag>{patterns.length}</Tag>
          </Space>
        }
        style={{ background: '#1a2734' }}
        styles={{ body: { padding: '8px' } }}
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
          </div>
        ) : patterns.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <div>
                <Text style={{ color: '#6a8caf', fontSize: 11 }}>
                  No patterns found
                </Text>
                <div style={{ marginTop: 4 }}>
                  <Text style={{ color: '#4a6a8a', fontSize: 10 }}>
                    Upload PCAP files to learn traffic patterns
                  </Text>
                </div>
              </div>
            }
          />
        ) : (
          <List
            dataSource={patterns}
            size="small"
            renderItem={(pattern) => (
              <PatternListItem
                key={pattern.id}
                pattern={pattern}
                expanded={expandedPattern === pattern.id}
                detail={expandedPattern === pattern.id ? patternDetail : null}
                loadingDetail={expandedPattern === pattern.id && loadingDetail}
                onExpand={() => handleExpandPattern(pattern.id)}
                onToggle={(e) => handleTogglePattern(pattern.id, e)}
                onApply={() => onApplyPattern?.(pattern)}
              />
            )}
          />
        )}
      </Card>
    </div>
  );
};

// Pattern List Item Component
interface PatternListItemProps {
  pattern: LearnedPattern;
  expanded: boolean;
  detail: PatternDetail | null;
  loadingDetail: boolean;
  onExpand: () => void;
  onToggle: (e: React.MouseEvent) => void;
  onApply?: () => void;
}

const PatternListItem: React.FC<PatternListItemProps> = ({
  pattern,
  expanded,
  detail,
  loadingDetail,
  onExpand,
  onToggle,
  onApply,
}) => {
  return (
    <div
      style={{
        background: '#0d1117',
        borderRadius: 4,
        marginBottom: 4,
        border: expanded ? '1px solid #5a9fd4' : '1px solid transparent',
      }}
    >
      <div
        style={{
          padding: '8px',
          cursor: 'pointer',
        }}
        onClick={onExpand}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Space direction="vertical" size={2}>
            <Space size={4}>
              <Text style={{ fontSize: 11, color: '#c9d1d9', fontWeight: 500 }}>
                {pattern.name}
              </Text>
              <Tag
                color={patternTypeColors[pattern.pattern_type] || 'default'}
                style={{ fontSize: 9 }}
              >
                {pattern.pattern_type}
              </Tag>
              <Tag style={{ fontSize: 9 }}>{pattern.protocol}</Tag>
            </Space>
            <Space size={4}>
              {pattern.distribution_type && (
                <Text style={{ fontSize: 10, color: '#6a8caf' }}>
                  {distributionTypeLabels[pattern.distribution_type] || pattern.distribution_type}
                </Text>
              )}
              <Text style={{ fontSize: 10, color: '#4a6a8a' }}>
                | {pattern.sample_count} samples
              </Text>
            </Space>
          </Space>
          <Space size={4}>
            <Tooltip title={`Confidence: ${(pattern.confidence * 100).toFixed(0)}%`}>
              <Progress
                type="circle"
                percent={Math.round(pattern.confidence * 100)}
                size={24}
                strokeWidth={10}
                strokeColor={pattern.confidence > 0.8 ? '#52c41a' : pattern.confidence > 0.5 ? '#faad14' : '#ff4d4f'}
                format={() => null}
              />
            </Tooltip>
            <Switch
              size="small"
              checked={pattern.is_active}
              onClick={onToggle}
            />
          </Space>
        </div>

        {/* Summary stats */}
        {(pattern.mean_value || pattern.min_value || pattern.max_value) && (
          <div style={{ marginTop: 4 }}>
            <Space size={8}>
              {pattern.mean_value && (
                <Text style={{ fontSize: 10, color: '#6a8caf' }}>
                  Mean: {pattern.mean_value.toFixed(2)}ms
                </Text>
              )}
              {pattern.min_value && pattern.max_value && (
                <Text style={{ fontSize: 10, color: '#6a8caf' }}>
                  Range: {pattern.min_value.toFixed(0)}-{pattern.max_value.toFixed(0)}ms
                </Text>
              )}
              {pattern.std_dev && (
                <Text style={{ fontSize: 10, color: '#6a8caf' }}>
                  StdDev: {pattern.std_dev.toFixed(2)}
                </Text>
              )}
            </Space>
          </div>
        )}
      </div>

      {/* Expanded Detail */}
      {expanded && (
        <div
          style={{
            borderTop: '1px solid #2a3f54',
            padding: '8px',
            background: '#0a0f14',
          }}
        >
          {loadingDetail ? (
            <div style={{ textAlign: 'center', padding: 16 }}>
              <Spin size="small" />
            </div>
          ) : detail ? (
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              {/* Timing Parameters */}
              {detail.timing_params && (
                <div>
                  <Text strong style={{ fontSize: 10, color: '#8aa4bc' }}>
                    Timing Parameters
                  </Text>
                  <pre
                    style={{
                      fontSize: 9,
                      color: '#6a8caf',
                      margin: '4px 0',
                      background: '#0d1117',
                      padding: 8,
                      borderRadius: 4,
                      overflow: 'auto',
                      maxHeight: 100,
                    }}
                  >
                    {JSON.stringify(detail.timing_params, null, 2)}
                  </pre>
                </div>
              )}

              {/* Flow Info */}
              <div>
                <Text strong style={{ fontSize: 10, color: '#8aa4bc' }}>
                  Flow Details
                </Text>
                <div style={{ marginTop: 4 }}>
                  <Space size={8} wrap>
                    {detail.source_ip && (
                      <Tag style={{ fontSize: 9 }}>Src: {detail.source_ip}</Tag>
                    )}
                    {detail.destination_ip && (
                      <Tag style={{ fontSize: 9 }}>Dst: {detail.destination_ip}</Tag>
                    )}
                    {detail.source_port && (
                      <Tag style={{ fontSize: 9 }}>SPort: {detail.source_port}</Tag>
                    )}
                    {detail.destination_port && (
                      <Tag style={{ fontSize: 9 }}>DPort: {detail.destination_port}</Tag>
                    )}
                  </Space>
                </div>
              </div>

              {/* Fit Score */}
              {detail.fit_score && (
                <div>
                  <Text strong style={{ fontSize: 10, color: '#8aa4bc' }}>
                    Distribution Fit Score: {(detail.fit_score * 100).toFixed(1)}%
                  </Text>
                </div>
              )}

              {/* Apply Button */}
              {onApply && (
                <Button
                  type="primary"
                  size="small"
                  icon={<ThunderboltOutlined />}
                  onClick={onApply}
                  style={{ marginTop: 8 }}
                >
                  Apply to Selected Device
                </Button>
              )}
            </Space>
          ) : (
            <Text style={{ fontSize: 10, color: '#6a8caf' }}>
              No additional details available
            </Text>
          )}
        </div>
      )}
    </div>
  );
};

export default LearnedPatternsPanel;
