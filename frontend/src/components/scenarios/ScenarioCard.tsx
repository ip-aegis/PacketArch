/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
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
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  MoreOutlined,
  FolderOutlined,
} from '@ant-design/icons';
import type { ScenarioSummary } from '../../api/scenarios';
import type { DashboardDeployment } from '../../api/dashboard';
import { formatRelativeTime } from '../../utils/dateUtils';
import { verticalConfig, formatDuration } from './scenarioConstants';
import { ScenarioModeBadges, modesFromSummary } from '../common';

const { Text, Paragraph } = Typography;

export interface ScenarioCardProps {
  scenario: ScenarioSummary;
  isSelected: boolean;
  menuItems: MenuProps['items'];
  onOpen: (id: string) => void;
  onToggleSelect: (id: string, e: React.MouseEvent) => void;
  onMenuClick: (scenario: ScenarioSummary, info: { key: string; domEvent: React.MouseEvent }) => void;
  deployment?: DashboardDeployment;
}

const ScenarioCard: React.FC<ScenarioCardProps> = React.memo(({
  scenario,
  isSelected,
  menuItems,
  onOpen,
  onToggleSelect,
  onMenuClick,
  deployment,
}) => {
  const verticalInfo = scenario.vertical
    ? verticalConfig[scenario.vertical]
    : null;

  return (
    <>
    <style>{`
      @keyframes scenarioCardPulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
      }
      .scenario-card-pulse {
        animation: scenarioCardPulse 2s ease-in-out infinite;
      }
    `}</style>
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

      {/* Mode badges (clean demo, broadcast, cell isolation) — render only
          when at least one non-default mode is active. */}
      <div style={{ marginBottom: 12 }} onClick={(e) => e.stopPropagation()}>
        <ScenarioModeBadges modes={modesFromSummary(scenario)} />
      </div>

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

      {/* Deployment Status */}
      {deployment && (
        <div
          style={{
            background: '#0a2e1a',
            border: '1px solid rgba(82,196,26,0.25)',
            borderRadius: 6,
            padding: '6px 12px',
            marginBottom: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div
              className="scenario-card-pulse"
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: '#52c41a',
                boxShadow: '0 0 8px rgba(82,196,26,0.6)',
                flexShrink: 0,
              }}
            />
            <Text style={{ color: '#52c41a', fontSize: 11 }}>
              Running on {deployment.agent_name}
            </Text>
          </div>
          <Text style={{ color: '#6b6b8a', fontSize: 10, whiteSpace: 'nowrap' }}>
            {deployment.packets_per_second.toFixed(0)} pps
          </Text>
        </div>
      )}

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
          {scenario.readiness && (
            <Tooltip
              title={
                <div style={{ fontSize: 12 }}>
                  <div style={{ marginBottom: 4, fontWeight: 600 }}>
                    Readiness: {scenario.readiness.score}%
                  </div>
                  {scenario.readiness.checks.map((check, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '1px 0' }}>
                      {check.passed ? (
                        <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 11 }} />
                      ) : check.severity === 'error' ? (
                        <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 11 }} />
                      ) : (
                        <ExclamationCircleOutlined style={{ color: '#faad14', fontSize: 11 }} />
                      )}
                      <span>{check.name}</span>
                    </div>
                  ))}
                </div>
              }
            >
              {scenario.readiness.status === 'ready' ? (
                <Tag
                  style={{
                    background: '#52c41a20',
                    border: '1px solid #52c41a40',
                    color: '#52c41a',
                    fontSize: 10,
                  }}
                >
                  <CheckCircleOutlined /> Ready
                </Tag>
              ) : scenario.readiness.status === 'warnings' ? (
                <Tag
                  style={{
                    background: '#faad1420',
                    border: '1px solid #faad1440',
                    color: '#faad14',
                    fontSize: 10,
                  }}
                >
                  <ExclamationCircleOutlined /> {scenario.readiness.warning_count} warning{scenario.readiness.warning_count !== 1 ? 's' : ''}
                </Tag>
              ) : (
                <Tag
                  style={{
                    background: '#ff4d4f20',
                    border: '1px solid #ff4d4f40',
                    color: '#ff4d4f',
                    fontSize: 10,
                  }}
                >
                  <CloseCircleOutlined /> Not Ready
                </Tag>
              )}
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
    </>
  );
});

ScenarioCard.displayName = 'ScenarioCard';

export default ScenarioCard;
