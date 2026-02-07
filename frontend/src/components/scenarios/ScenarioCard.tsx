/**
 * ScenarioCard - Renders a single scenario as a card in the grid view.
 */

import React from 'react';
import {
  Card,
  Tag,
  Space,
  Tooltip,
  Typography,
  Checkbox,
  Button,
  Dropdown,
} from 'antd';
import type { MenuProps } from 'antd';
import {
  ClockCircleOutlined,
  MoreOutlined,
  FolderOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import type { ScenarioSummary } from '../../api/scenarios';
import { formatRelativeTime } from '../../utils/dateUtils';
import { verticalConfig, formatDuration } from './scenarioConstants';

const { Text, Paragraph } = Typography;

export interface ScenarioCardProps {
  scenario: ScenarioSummary;
  isSelected: boolean;
  menuItems: MenuProps['items'];
  onOpen: (id: string) => void;
  onToggleSelect: (id: string, e: React.MouseEvent) => void;
  onMenuClick: (scenario: ScenarioSummary, info: { key: string; domEvent: React.MouseEvent }) => void;
}

const ScenarioCard: React.FC<ScenarioCardProps> = React.memo(({
  scenario,
  isSelected,
  menuItems,
  onOpen,
  onToggleSelect,
  onMenuClick,
}) => {
  const verticalInfo = scenario.vertical
    ? verticalConfig[scenario.vertical]
    : null;

  return (
    <Card
      hoverable
      style={{
        background: isSelected ? '#1a2433' : '#141428',
        border: isSelected
          ? '1px solid #1890ff'
          : '1px solid #2d2d52',
        borderRadius: 12,
      }}
      bodyStyle={{ padding: 20 }}
      onClick={() => onOpen(scenario.id)}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          marginBottom: 12,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            flex: 1,
            minWidth: 0,
          }}
        >
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 10,
              background: verticalInfo
                ? `linear-gradient(135deg, ${verticalInfo.color}20 0%, ${verticalInfo.color}10 100%)`
                : 'linear-gradient(135deg, #049FD920 0%, #049FD910 100%)',
              border: `1px solid ${verticalInfo?.color || '#049FD9'}40`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: verticalInfo?.color || '#049FD9',
              fontSize: 20,
              flexShrink: 0,
              position: 'relative',
            }}
            onClick={(e) => onToggleSelect(scenario.id, e)}
          >
            {isSelected ? (
              <Checkbox
                checked
                style={{ position: 'absolute' }}
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              verticalInfo?.icon || <FolderOutlined />
            )}
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <Text
              strong
              style={{ color: '#fff', fontSize: 15, display: 'block' }}
              ellipsis={{ tooltip: scenario.name }}
            >
              {scenario.name}
            </Text>
            {verticalInfo && (
              <Tag
                style={{
                  background: `${verticalInfo.color}20`,
                  border: `1px solid ${verticalInfo.color}40`,
                  color: verticalInfo.color,
                  marginTop: 4,
                  fontSize: 11,
                }}
              >
                {verticalInfo.label}
              </Tag>
            )}
          </div>
        </div>
        <Dropdown
          menu={{
            items: menuItems,
            onClick: (info) => onMenuClick(scenario, info),
          }}
          trigger={['click']}
        >
          <Button
            type="text"
            icon={<MoreOutlined />}
            style={{ color: '#6b6b8a' }}
            onClick={(e) => e.stopPropagation()}
          />
        </Dropdown>
      </div>

      {/* Description */}
      {scenario.description && (
        <Paragraph
          ellipsis={{ rows: 2 }}
          style={{
            color: '#a8a8c0',
            fontSize: 13,
            marginBottom: 16,
            minHeight: 40,
          }}
        >
          {scenario.description}
        </Paragraph>
      )}

      {/* Stats */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 12,
          marginBottom: 16,
          padding: 12,
          background: '#1a1a2e',
          borderRadius: 8,
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <Text
            style={{
              color: '#6b6b8a',
              fontSize: 10,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            Devices
          </Text>
          <div style={{ color: '#fff', fontSize: 18, fontWeight: 600 }}>
            {scenario.device_count}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <Text
            style={{
              color: '#6b6b8a',
              fontSize: 10,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            Flows
          </Text>
          <div style={{ color: '#fff', fontSize: 18, fontWeight: 600 }}>
            {scenario.flow_count}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <Text
            style={{
              color: '#6b6b8a',
              fontSize: 10,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            Duration
          </Text>
          <div style={{ color: '#fff', fontSize: 18, fontWeight: 600 }}>
            {formatDuration(scenario.total_duration_ms)}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderTop: '1px solid #2d2d52',
          paddingTop: 12,
        }}
      >
        <Space size={4}>
          <ClockCircleOutlined style={{ color: '#6b6b8a', fontSize: 12 }} />
          <Text style={{ color: '#6b6b8a', fontSize: 11 }}>
            Updated {formatRelativeTime(scenario.updated_at)}
          </Text>
        </Space>
        <Space size={4}>
          {scenario.has_learned_patterns && (
            <Tooltip
              title={`Enhanced with learned patterns for: ${scenario.protocols_enhanced?.join(', ') || 'multiple protocols'}`}
            >
              <Tag
                style={{
                  background: '#52c41a20',
                  border: '1px solid #52c41a40',
                  color: '#52c41a',
                  fontSize: 10,
                }}
              >
                <ExperimentOutlined /> Learned
              </Tag>
            </Tooltip>
          )}
          <Tag
            style={{
              background: '#2d2d52',
              border: 'none',
              color: '#6b6b8a',
              fontSize: 10,
            }}
          >
            v{scenario.version}
          </Tag>
        </Space>
      </div>
    </Card>
  );
});

ScenarioCard.displayName = 'ScenarioCard';

export default ScenarioCard;
