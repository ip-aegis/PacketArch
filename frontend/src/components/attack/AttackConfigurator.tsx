/**
 * AttackConfigurator - Configure playbook settings before deployment.
 */

import React from 'react';
import { Button, Collapse, InputNumber, Slider, Space, Switch, Tag, Typography, Radio } from 'antd';
import { ArrowLeftOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useAttackStore } from '../../stores/attackStore';

const { Text, Title } = Typography;

type InjectionStatus = 'idle' | 'injecting' | 'polling' | 'confirmed' | 'failed';

interface AttackConfiguratorProps {
  onBack: () => void;
  onApply: () => void;
  isDeployed?: boolean;
  onInject?: () => void;
  injectionStatus?: InjectionStatus;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

const severityColors: Record<string, string> = {
  critical: '#ff4d4f',
  high: '#fa8c16',
  medium: '#faad14',
  low: '#52c41a',
};

const AttackConfigurator: React.FC<AttackConfiguratorProps> = ({ onBack, onApply, isDeployed, onInject, injectionStatus = 'idle' }) => {
  const { selectedPlaybook, playbookConfig, setConfig } = useAttackStore();

  if (!selectedPlaybook || !playbookConfig) return null;

  const updateConfig = (updates: Partial<typeof playbookConfig>) => {
    setConfig({ ...playbookConfig, ...updates });
  };

  return (
    <div style={{ padding: '8px 0' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
        <Button
          type="text"
          size="small"
          icon={<ArrowLeftOutlined />}
          onClick={onBack}
          style={{ color: '#8aa4bc', width: 22, height: 22 }}
        />
        <Text style={{ color: '#e6f1ff', fontSize: 12, fontWeight: 500, flex: 1 }}>
          {selectedPlaybook.name}
        </Text>
        <Tag
          color={severityColors[selectedPlaybook.severity] || '#ff4d4f'}
          style={{ fontSize: 9, margin: 0, lineHeight: '14px', padding: '0 4px' }}
        >
          {selectedPlaybook.severity.toUpperCase()}
        </Tag>
      </div>

      {/* Description */}
      <Text style={{ color: '#6a8caf', fontSize: 10, display: 'block', marginBottom: 12 }}>
        {selectedPlaybook.description}
      </Text>

      {/* Stage overview */}
      <div style={{ marginBottom: 12 }}>
        <Text style={{ color: '#8aa4bc', fontSize: 10, display: 'block', marginBottom: 4 }}>
          Kill Chain ({selectedPlaybook.stages.length} stages, {formatDuration(selectedPlaybook.total_duration_seconds)})
        </Text>
        <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', background: '#0d1117' }}>
          {selectedPlaybook.stages.map((s) => {
            const widthPct = (s.duration_seconds / selectedPlaybook.total_duration_seconds) * 100;
            return (
              <div
                key={s.stage_id}
                style={{
                  width: `${widthPct}%`,
                  minWidth: 3,
                  background: s.color,
                  borderRight: '1px solid #0d1117',
                }}
                title={`${s.name} — ${formatDuration(s.duration_seconds)}`}
              />
            );
          })}
        </div>
        <div style={{ display: 'flex', marginTop: 2 }}>
          {selectedPlaybook.stages.map((s) => {
            const widthPct = (s.duration_seconds / selectedPlaybook.total_duration_seconds) * 100;
            return (
              <div
                key={s.stage_id}
                style={{
                  width: `${widthPct}%`, fontSize: 8, color: '#4a6a8a',
                  textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}
              >
                {widthPct > 12 ? s.name : ''}
              </div>
            );
          })}
        </div>
      </div>

      {/* Configuration */}
      <Collapse
        ghost
        size="small"
        defaultActiveKey={['settings']}
        items={[
          {
            key: 'settings',
            label: <Text style={{ color: '#8aa4bc', fontSize: 11 }}>Settings</Text>,
            children: (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {/* Intensity */}
                <div>
                  <Text style={{ color: '#6a8caf', fontSize: 10, display: 'block', marginBottom: 2 }}>
                    Intensity ({Math.round((playbookConfig.intensity ?? 1) * 100)}%)
                  </Text>
                  <Slider
                    min={10}
                    max={300}
                    value={(playbookConfig.intensity ?? 1) * 100}
                    onChange={(v) => updateConfig({ intensity: v / 100 })}
                    marks={{ 10: '10%', 100: '100%', 300: '300%' }}
                    style={{ margin: '4px 0 16px' }}
                  />
                </div>

                {/* Auto-advance */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text style={{ color: '#6a8caf', fontSize: 10 }}>
                    Auto-advance stages
                  </Text>
                  <Switch
                    size="small"
                    checked={playbookConfig.auto_advance ?? true}
                    onChange={(v) => updateConfig({ auto_advance: v })}
                  />
                </div>

                {/* Start mode */}
                <div>
                  <Text style={{ color: '#6a8caf', fontSize: 10, display: 'block', marginBottom: 4 }}>
                    Start mode
                  </Text>
                  <Radio.Group
                    size="small"
                    value={playbookConfig.start_mode ?? 'with_deployment'}
                    onChange={(e) => updateConfig({ start_mode: e.target.value })}
                    style={{ fontSize: 10 }}
                  >
                    <Radio value="with_deployment" style={{ color: '#8aa4bc', fontSize: 10 }}>
                      Auto (on deploy)
                    </Radio>
                    <Radio value="manual" style={{ color: '#8aa4bc', fontSize: 10 }}>
                      Manual
                    </Radio>
                  </Radio.Group>
                </div>
              </div>
            ),
          },
          {
            key: 'stages',
            label: <Text style={{ color: '#8aa4bc', fontSize: 11 }}>Stage Details</Text>,
            children: (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {selectedPlaybook.stages.map((stage) => (
                  <div
                    key={stage.stage_id}
                    style={{
                      padding: '6px 8px',
                      background: '#0d1117',
                      borderRadius: 4,
                      borderLeft: `3px solid ${stage.color}`,
                    }}
                  >
                    <Text style={{ color: '#e6f1ff', fontSize: 10, fontWeight: 500, display: 'block' }}>
                      {stage.name}
                    </Text>
                    <Text style={{ color: '#4a6a8a', fontSize: 9 }}>
                      {formatDuration(stage.duration_seconds)} · {stage.actions.length} actions
                    </Text>
                    {stage.mitre_tactics.length > 0 && (
                      <div style={{ marginTop: 2 }}>
                        {stage.mitre_tactics.map((t) => (
                          <Tag key={t} style={{ fontSize: 8, margin: '0 2px 0 0', lineHeight: '12px', padding: '0 3px', background: '#1d1d3a', borderColor: '#3d3d7a', color: '#b3b3ff' }}>
                            {t}
                          </Tag>
                        ))}
                      </div>
                    )}
                    {stage.expected_cv_alerts.length > 0 && (
                      <div style={{ marginTop: 2 }}>
                        <Text style={{ color: '#52c41a', fontSize: 8 }}>
                          CV: {stage.expected_cv_alerts.join(', ')}
                        </Text>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ),
          },
        ]}
      />

      {/* Action buttons */}
      {isDeployed ? (
        <Button
          type="primary"
          danger
          block
          icon={<ThunderboltOutlined />}
          loading={injectionStatus === 'injecting' || injectionStatus === 'polling'}
          disabled={injectionStatus === 'polling'}
          onClick={onInject}
          style={{ marginTop: 12 }}
        >
          {injectionStatus === 'polling'
            ? 'Confirming with agent...'
            : 'Inject Into Running Deployment'}
        </Button>
      ) : (
        <Button
          type="primary"
          danger
          block
          icon={<ThunderboltOutlined />}
          onClick={onApply}
          style={{ marginTop: 12 }}
        >
          Apply to Scenario
        </Button>
      )}
    </div>
  );
};

export default AttackConfigurator;
