/**
 * DeploymentForm - Form for configuring and launching a deployment
 * to either a traffic agent or Docker host.
 */

import React from 'react';
import {
  Alert,
  Button,
  Card,
  Form,
  InputNumber,
  Radio,
  Select,
  Space,
  Tag,
  Typography,
} from 'antd';
import type { FormInstance } from 'antd';
import {
  CloudServerOutlined,
  PlayCircleOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import type { DockerHost } from '../../types/docker';
import type { RunMode, NetworkInterface } from '../../types/docker';
import type { AgentInterface, TrafficAgent } from '../../types/agent';

const { Text } = Typography;

export type TargetType = 'docker' | 'agent';

export interface DeploymentFormProps {
  form: FormInstance;
  targetType: TargetType;
  onTargetTypeChange: (type: TargetType) => void;

  // Agents
  onlineAgents: TrafficAgent[];
  agentsLoading: boolean;
  agentInterfaces: AgentInterface[];
  onAgentChange: (agentId: string) => void;

  // Docker hosts
  activeHosts: DockerHost[];
  hostsLoading: boolean;
  interfaces: NetworkInterface[];
  onHostChange: (hostId: string) => void;

  // Shared
  loadingInterfaces: boolean;
  validating: boolean;
  deploymentsLoading: boolean;
  onFinish: (values: {
    docker_host_id?: string;
    agent_id?: string;
    network_interface: string;
    run_mode: RunMode;
    duration_minutes?: number;
  }) => void;
}

const DeploymentForm: React.FC<DeploymentFormProps> = React.memo(({
  form,
  targetType,
  onTargetTypeChange,
  onlineAgents,
  agentsLoading,
  agentInterfaces,
  onAgentChange,
  activeHosts,
  hostsLoading,
  interfaces,
  onHostChange,
  loadingInterfaces,
  validating,
  deploymentsLoading,
  onFinish,
}) => {
  const hasTargets = onlineAgents.length > 0 || activeHosts.length > 0;

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
          description="Configure traffic agents in Settings > Traffic Agents, or Docker hosts in Settings > Docker Hosts"
          type="warning"
          showIcon
        />
      ) : (
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{ duration_minutes: 5, run_mode: 'timed' }}
          size="small"
        >
          {/* Target Type Selector */}
          <Form.Item label="Deploy To" style={{ marginBottom: 12 }}>
            <Radio.Group
              value={targetType}
              onChange={(e) => onTargetTypeChange(e.target.value)}
              size="small"
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
              }}
            >
              <Radio
                value="agent"
                disabled={onlineAgents.length === 0}
              >
                <Space size={4}>
                  <RocketOutlined />
                  <span>Traffic Agent</span>
                  {onlineAgents.length > 0 ? (
                    <Tag
                      color="green"
                      style={{ fontSize: 10, marginLeft: 4 }}
                    >
                      {onlineAgents.length} online
                    </Tag>
                  ) : (
                    <Tag
                      color="default"
                      style={{ fontSize: 10, marginLeft: 4 }}
                    >
                      none online
                    </Tag>
                  )}
                </Space>
              </Radio>
              <Radio
                value="docker"
                disabled={activeHosts.length === 0}
              >
                <Space size={4}>
                  <CloudServerOutlined />
                  <span>Docker Host (Legacy)</span>
                  {activeHosts.length === 0 && (
                    <Tag
                      color="default"
                      style={{ fontSize: 10, marginLeft: 4 }}
                    >
                      none configured
                    </Tag>
                  )}
                </Space>
              </Radio>
            </Radio.Group>
          </Form.Item>

          {/* Agent Selection */}
          {targetType === 'agent' && (
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
          )}

          {/* Docker Host Selection */}
          {targetType === 'docker' && (
            <Form.Item
              name="docker_host_id"
              label="Docker Host"
              rules={[{ required: true, message: 'Select a host' }]}
            >
              <Select
                placeholder="Select host"
                loading={hostsLoading}
                onChange={onHostChange}
                options={activeHosts.map((h) => ({
                  value: h.id,
                  label: h.name,
                }))}
              />
            </Form.Item>
          )}

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
              disabled={
                targetType === 'agent'
                  ? agentInterfaces.length === 0
                  : interfaces.length === 0
              }
              options={
                targetType === 'agent'
                  ? agentInterfaces.map((i) => ({
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
                    }))
                  : interfaces.map((i) => ({
                      value: i.name,
                      label: (
                        <Space>
                          <span>{i.name}</span>
                          {i.is_up ? (
                            <Tag
                              color="green"
                              style={{ fontSize: 10 }}
                            >
                              UP
                            </Tag>
                          ) : (
                            <Tag
                              color="default"
                              style={{ fontSize: 10 }}
                            >
                              DOWN
                            </Tag>
                          )}
                        </Space>
                      ),
                    }))
              }
            />
          </Form.Item>

          {/* Run Mode - only for Docker hosts */}
          {targetType === 'docker' && (
            <>
              <Form.Item name="run_mode" label="Run Mode">
                <Select
                  options={[
                    {
                      value: 'timed',
                      label: 'Timed (stops after duration)',
                    },
                    {
                      value: 'perpetual',
                      label: 'Perpetual (runs until stopped)',
                    },
                  ]}
                />
              </Form.Item>

              <Form.Item
                noStyle
                shouldUpdate={(prev, curr) =>
                  prev.run_mode !== curr.run_mode
                }
              >
                {({ getFieldValue }) =>
                  getFieldValue('run_mode') !== 'perpetual' && (
                    <Form.Item
                      name="duration_minutes"
                      label="Duration (minutes)"
                      rules={[{ required: true }]}
                    >
                      <InputNumber
                        min={1}
                        max={1440}
                        style={{ width: '100%' }}
                      />
                    </Form.Item>
                  )
                }
              </Form.Item>
            </>
          )}

          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={deploymentsLoading || validating}
              icon={<PlayCircleOutlined />}
              block
            >
              {validating ? 'Validating...' : 'Deploy'}
            </Button>
          </Form.Item>
        </Form>
      )}
    </Card>
  );
});

DeploymentForm.displayName = 'DeploymentForm';

export default DeploymentForm;
