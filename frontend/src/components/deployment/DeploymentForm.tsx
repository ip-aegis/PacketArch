/**
 * DeploymentForm - Form for configuring and launching a deployment to a traffic agent.
 */

import React, { useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Collapse,
  Form,
  InputNumber,
  Select,
  Space,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import type { FormInstance } from 'antd';
import {
  FieldTimeOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons';
import type { RunMode } from '../../types/docker';
import type { AgentInterface, TrafficAgent } from '../../types/agent';
import type { Phase } from '../../types';
import { PHASE_NAME_MAP, DEFAULT_LIVE_DURATIONS } from '../../constants/phases';

const { Text } = Typography;

export interface PhaseScheduleConfig {
  enabled: boolean;
  cycle: boolean;
  phases: {
    phase_id: string;
    name: string;
    duration_seconds: number;
    rate_multiplier: number;
    color: string;
  }[];
}

export interface DeploymentFormProps {
  form: FormInstance;

  // Agents
  onlineAgents: TrafficAgent[];
  agentsLoading: boolean;
  agentInterfaces: AgentInterface[];
  onAgentChange: (agentId: string) => void;

  // Scenario phases
  phases?: Phase[];

  // Shared
  loadingInterfaces: boolean;
  validating: boolean;
  deploymentsLoading: boolean;
  deployDisabled?: boolean;
  onFinish: (values: {
    agent_id?: string;
    network_interface: string;
    run_mode: RunMode;
    duration_minutes?: number;
    phase_schedule?: PhaseScheduleConfig;
  }) => void;
}

const DeploymentForm: React.FC<DeploymentFormProps> = React.memo(({
  form,
  onlineAgents,
  agentsLoading,
  agentInterfaces,
  onAgentChange,
  phases,
  loadingInterfaces,
  validating,
  deploymentsLoading,
  deployDisabled,
  onFinish,
}) => {
  const hasTargets = onlineAgents.length > 0;
  const [phaseScheduleEnabled, setPhaseScheduleEnabled] = useState(false);
  const [cycleContinuously, setCycleContinuously] = useState(true);
  const [phaseDurations, setPhaseDurations] = useState<Record<string, number>>(() => {
    const durations: Record<string, number> = {};
    if (phases) {
      for (const p of phases) {
        durations[p.id] = DEFAULT_LIVE_DURATIONS[p.name] ?? 600;
      }
    }
    return durations;
  });

  const handleFinish = (values: {
    agent_id?: string;
    network_interface: string;
    run_mode: RunMode;
    duration_minutes?: number;
  }) => {
    let phase_schedule: PhaseScheduleConfig | undefined;
    if (phaseScheduleEnabled && phases && phases.length > 0) {
      phase_schedule = {
        enabled: true,
        cycle: cycleContinuously,
        phases: phases.map((p) => ({
          phase_id: PHASE_NAME_MAP[p.name] ?? p.name,
          name: p.displayName,
          duration_seconds: phaseDurations[p.id] ?? DEFAULT_LIVE_DURATIONS[p.name] ?? 600,
          rate_multiplier: p.intensity,
          color: p.color,
        })),
      };
    }
    onFinish({ ...values, phase_schedule });
  };

  return (
    <Card
      size="small"
      title={
        <Space>
          <PlayCircleOutlined />
          <span>New Deployment</span>
        </Space>
      }
      style={{ background: '#1a2734' }}
      styles={{ body: { padding: '12px' } }}
    >
      {!hasTargets ? (
        <Alert
          message="No deployment targets available"
          description="Configure traffic agents in Settings > Traffic Agents"
          type="warning"
          showIcon
        />
      ) : (
        <Form
          form={form}
          layout="vertical"
          onFinish={handleFinish}
          initialValues={{ run_mode: 'perpetual' }}
          size="small"
        >
          {/* Agent Selection */}
          <Form.Item
            name="agent_id"
            label="Traffic Agent"
            rules={[{ required: true, message: 'Select an agent' }]}
          >
            <Select
              placeholder="Select agent"
              loading={agentsLoading}
              onChange={onAgentChange}
              options={onlineAgents.map((a) => ({
                value: a.id,
                label: (
                  <Space>
                    <span>{a.name}</span>
                    <Tag
                      color="green"
                      style={{ fontSize: 10 }}
                    >
                      Online
                    </Tag>
                    {a.hostname && (
                      <Text
                        type="secondary"
                        style={{ fontSize: 11 }}
                      >
                        ({a.hostname})
                      </Text>
                    )}
                  </Space>
                ),
              }))}
            />
          </Form.Item>

          {/* Network Interface */}
          <Form.Item
            name="network_interface"
            label="Network Interface"
            rules={[
              { required: true, message: 'Select an interface' },
            ]}
          >
            <Select
              placeholder={
                loadingInterfaces
                  ? 'Loading interfaces...'
                  : 'Select interface'
              }
              loading={loadingInterfaces}
              disabled={agentInterfaces.length === 0}
              options={agentInterfaces.map((i) => ({
                value: i.name,
                label: (
                  <Space>
                    <span>{i.name}</span>
                    {i.mac && (
                      <Text
                        type="secondary"
                        style={{ fontSize: 10 }}
                      >
                        {i.mac}
                      </Text>
                    )}
                  </Space>
                ),
              }))}
            />
          </Form.Item>

          {/* Phase Schedule */}
          {phases && phases.length > 0 && (
            <Collapse
              ghost
              size="small"
              style={{ marginBottom: 12, background: 'transparent' }}
              items={[{
                key: 'phase-schedule',
                label: (
                  <Space size={4}>
                    <FieldTimeOutlined />
                    <span style={{ fontSize: 12 }}>Phase Schedule</span>
                    {phaseScheduleEnabled && (
                      <Tag color="blue" style={{ fontSize: 10, margin: 0 }}>
                        {phases.length} phases
                      </Tag>
                    )}
                  </Space>
                ),
                children: (
                  <div style={{ paddingTop: 4 }}>
                    <Checkbox
                      checked={phaseScheduleEnabled}
                      onChange={(e) => setPhaseScheduleEnabled(e.target.checked)}
                      style={{ marginBottom: 8, fontSize: 12, color: '#8aa4bc' }}
                    >
                      Enable phase cycling
                    </Checkbox>

                    {phaseScheduleEnabled && (
                      <>
                        <div style={{ marginBottom: 8 }}>
                          {phases.map((phase) => (
                            <div
                              key={phase.id}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 8,
                                marginBottom: 6,
                              }}
                            >
                              <div
                                style={{
                                  width: 8,
                                  height: 8,
                                  borderRadius: '50%',
                                  background: phase.color,
                                  flexShrink: 0,
                                }}
                              />
                              <Text
                                style={{
                                  color: '#8aa4bc',
                                  fontSize: 11,
                                  width: 80,
                                  flexShrink: 0,
                                }}
                                ellipsis
                              >
                                {phase.displayName}
                              </Text>
                              <InputNumber
                                size="small"
                                min={10}
                                max={86400}
                                value={phaseDurations[phase.id] ?? DEFAULT_LIVE_DURATIONS[phase.name] ?? 600}
                                onChange={(val) => {
                                  if (val !== null) {
                                    setPhaseDurations((prev) => ({
                                      ...prev,
                                      [phase.id]: val,
                                    }));
                                  }
                                }}
                                style={{ width: 80 }}
                                addonAfter="s"
                              />
                              <Text
                                type="secondary"
                                style={{ fontSize: 10 }}
                              >
                                {Math.round(phase.intensity * 100)}% rate
                              </Text>
                            </div>
                          ))}
                        </div>

                        <Checkbox
                          checked={cycleContinuously}
                          onChange={(e) => setCycleContinuously(e.target.checked)}
                          style={{ fontSize: 12, color: '#8aa4bc' }}
                        >
                          Cycle continuously
                        </Checkbox>
                      </>
                    )}
                  </div>
                ),
              }]}
            />
          )}

          <Form.Item style={{ marginBottom: 0 }}>
            <Tooltip
              title={deployDisabled ? 'Fix readiness errors before deploying' : undefined}
            >
              <Button
                type="primary"
                htmlType="submit"
                loading={deploymentsLoading || validating}
                disabled={deployDisabled}
                icon={<PlayCircleOutlined />}
                block
              >
                {validating ? 'Validating...' : 'Deploy'}
              </Button>
            </Tooltip>
          </Form.Item>
        </Form>
      )}
    </Card>
  );
});

DeploymentForm.displayName = 'DeploymentForm';

export default DeploymentForm;
