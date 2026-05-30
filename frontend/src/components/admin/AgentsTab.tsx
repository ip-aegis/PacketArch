/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * AgentsTab - Traffic Agent Management UI
 *
 * Provides comprehensive management of WebSocket-based remote traffic agents:
 * - List agents with status indicators
 * - Create/edit/delete agents
 * - View connection info and system stats
 * - Deploy scenarios to agents
 * - Installation instructions
 */

import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  ArrowUpOutlined,
  BuildOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CopyOutlined,
  DeleteOutlined,
  DesktopOutlined,
  EditOutlined,
  EyeOutlined,
  InfoCircleOutlined,
  KeyOutlined,
  LoadingOutlined,
  PlusOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
  RocketOutlined,
} from '@ant-design/icons';

import { ErrorAlert } from '../common';
import { useAgentsStore } from '../../stores/agentsStore';
import { agentsApi } from '../../api/agents';
import { healthMonitorApi, type HealthStatusResponse } from '../../api/healthMonitor';
import type { TrafficAgent, TrafficAgentWithToken, AgentCreate, AgentUpdateStatus } from '../../types/agent';
import AgentDetailsDrawer from './AgentDetailsDrawer';
import AgentInstallDrawer from './AgentInstallDrawer';
import { formatRelativeTime } from '../../utils/dateUtils';
import { extractErrorMessage } from '../../utils/errorUtils';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

const AgentsTab: React.FC = () => {
  const {
    agents,
    isLoading,
    error,
    total,
    standardVersion,
    fetchAgents,
    createAgent,
    updateAgent,
    deleteAgent,
    regenerateToken,
    clearError,
  } = useAgentsStore();

  // Local state
  const [modalVisible, setModalVisible] = useState(false);
  const [editingAgent, setEditingAgent] = useState<TrafficAgent | null>(null);
  const [tokenModalVisible, setTokenModalVisible] = useState(false);
  const [newAgentToken, setNewAgentToken] = useState<TrafficAgentWithToken | null>(null);
  const [detailsDrawerOpen, setDetailsDrawerOpen] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [installDrawerOpen, setInstallDrawerOpen] = useState(false);
  const [buildingImage, setBuildingImage] = useState(false);
  const [buildStatus, setBuildStatus] = useState<{
    status: 'idle' | 'building' | 'complete' | 'failed';
    stage?: string;
    message: string;
    version?: string;
    error?: string;
  } | null>(null);
  const buildPollRef = useRef<NodeJS.Timeout | null>(null);
  const [form] = Form.useForm();
  const [healthStatus, setHealthStatus] = useState<HealthStatusResponse | null>(null);
  // Live per-agent update status (keyed by agent id) so the table shows an
  // "Updating…" indicator while an update is in flight or just finished.
  const [updateStatuses, setUpdateStatuses] = useState<Record<string, AgentUpdateStatus>>({});

  // Poll for build status
  const pollBuildStatus = useCallback(async () => {
    try {
      const status = await agentsApi.getBuildStatus();
      setBuildStatus(status);

      // Stop polling if build is complete or failed
      if (['complete', 'failed', 'idle'].includes(status.status)) {
        if (buildPollRef.current) {
          clearInterval(buildPollRef.current);
          buildPollRef.current = null;
        }
        setBuildingImage(false);

        if (status.status === 'complete') {
          message.success(status.message || 'Build completed successfully');
          fetchAgents(); // Refresh to get updated standard version
        } else if (status.status === 'failed') {
          message.error(status.message || 'Build failed');
        }
      }
    } catch (err) {
      console.error('Failed to poll build status:', err);
    }
  }, [fetchAgents]);

  // Cleanup build polling on unmount
  useEffect(() => {
    return () => {
      if (buildPollRef.current) {
        clearInterval(buildPollRef.current);
      }
    };
  }, []);

  // Fetch health status alongside agents
  const fetchHealth = useCallback(async () => {
    try {
      const status = await healthMonitorApi.getStatus();
      setHealthStatus(status);
    } catch {
      // Silently ignore
    }
  }, []);

  const fetchUpdateStatuses = useCallback(async () => {
    try {
      const all = await agentsApi.getActiveUpdateStatuses();
      const map: Record<string, AgentUpdateStatus> = {};
      for (const s of all) map[s.agent_id] = s;
      setUpdateStatuses(map);
    } catch {
      // Silently ignore
    }
  }, []);

  // Fetch agents on mount and set up polling
  useEffect(() => {
    fetchAgents();
    fetchHealth();
    fetchUpdateStatuses();

    // Poll status every 10s; poll in-flight update progress more often (3s).
    const interval = setInterval(() => {
      fetchAgents();
      fetchHealth();
    }, 10000);
    const updateInterval = setInterval(fetchUpdateStatuses, 3000);

    return () => {
      clearInterval(interval);
      clearInterval(updateInterval);
    };
  }, [fetchAgents, fetchHealth, fetchUpdateStatuses]);

  // Handlers
  const handleCreate = () => {
    setEditingAgent(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (agent: TrafficAgent) => {
    setEditingAgent(agent);
    form.setFieldsValue({
      name: agent.name,
      description: agent.description,
      default_interface: agent.default_interface,
    });
    setModalVisible(true);
  };

  const handleSubmit = async (values: AgentCreate) => {
    try {
      if (editingAgent) {
        await updateAgent(editingAgent.id, values);
        message.success('Agent updated successfully');
      } else {
        const agentWithToken = await createAgent(values);
        setNewAgentToken(agentWithToken);
        setTokenModalVisible(true);
        message.success('Agent created successfully');
      }
      setModalVisible(false);
      form.resetFields();
    } catch {
      // Error handled by store
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteAgent(id);
      message.success('Agent deleted successfully');
    } catch {
      // Error handled by store
    }
  };

  const handleRegenerateToken = async (agent: TrafficAgent) => {
    try {
      const agentWithToken = await regenerateToken(agent.id);
      setNewAgentToken(agentWithToken);
      setTokenModalVisible(true);
      message.success('Token regenerated successfully');
    } catch {
      // Error handled by store
    }
  };

  const handleViewDetails = (agent: TrafficAgent) => {
    setSelectedAgentId(agent.id);
    setDetailsDrawerOpen(true);
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    message.success(`${label} copied to clipboard`);
  };

  const handleBuildImage = async () => {
    setBuildingImage(true);
    try {
      const result = await agentsApi.buildImage();

      // If already building, just start polling
      if (result.status === 'building') {
        setBuildStatus({
          status: 'building',
          stage: 'starting',
          message: result.message,
          version: result.version,
        });

        // Start polling for build status
        if (!buildPollRef.current) {
          buildPollRef.current = setInterval(pollBuildStatus, 2000);
        }

        message.info('Agent image build started. This may take a few minutes.');
      }
    } catch (err: unknown) {
      message.error(extractErrorMessage(err, 'Failed to start image build'));
      setBuildingImage(false);
    }
  };

  // Table columns
  const columns: ColumnsType<TrafficAgent> = [
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 150,
      render: (status: string, record) => {
        const isOnline = status === 'online';
        const neverConnected = !record.first_connected_at;
        const agentHealth = healthStatus?.agents?.[record.id];
        const healthState = agentHealth?.status;

        // Use health status if available, fall back to simple online/offline
        let badgeStatus: 'success' | 'warning' | 'error' | 'default' = 'default';
        let tagColor = 'default';
        let tagLabel = 'Offline';
        let tooltipText = '';

        if (neverConnected) {
          badgeStatus = 'warning';
          tagColor = 'orange';
          tagLabel = 'Pending';
        } else if (healthState === 'critical') {
          badgeStatus = 'error';
          tagColor = 'red';
          tagLabel = 'Critical';
          const issues: string[] = [];
          if (!agentHealth?.heartbeat_ok) issues.push('Heartbeat timeout');
          if (!agentHealth?.resource_ok) issues.push('Resource exhaustion');
          if (agentHealth?.stalled_scenarios?.length) issues.push(`${agentHealth.stalled_scenarios.length} stalled`);
          tooltipText = issues.join(', ');
        } else if (healthState === 'warning') {
          badgeStatus = 'warning';
          tagColor = 'orange';
          tagLabel = 'Warning';
          const issues: string[] = [];
          if (!agentHealth?.heartbeat_ok) issues.push('Heartbeat timeout');
          if (!agentHealth?.resource_ok) issues.push('High resource usage');
          if (agentHealth?.stalled_scenarios?.length) issues.push(`${agentHealth.stalled_scenarios.length} stalled`);
          tooltipText = issues.join(', ');
        } else if (isOnline) {
          badgeStatus = 'success';
          tagColor = 'green';
          tagLabel = 'Healthy';
        }

        const tag = (
          <Space>
            <Badge status={badgeStatus} />
            <Tag color={tagColor}>{tagLabel}</Tag>
            {!record.is_active && <Tag color="red">Disabled</Tag>}
          </Space>
        );

        return tooltipText ? <Tooltip title={tooltipText}>{tag}</Tooltip> : tag;
      },
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Space direction="vertical" size={0}>
          <Space size={6}>
            <Text strong>{name}</Text>
            {record.local_lab_id ? (
              <Tag color="cyan">Local</Tag>
            ) : record.cml_lab_id ? (
              <Tag color="geekblue">CML</Tag>
            ) : (
              <Tag>Manual</Tag>
            )}
          </Space>
          {record.description && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.description}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Host Info',
      key: 'host_info',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          {record.hostname ? (
            <>
              <Text>
                <DesktopOutlined style={{ marginRight: 4 }} />
                {record.hostname}
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {record.platform}
              </Text>
            </>
          ) : (
            <Text type="secondary">Not connected</Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Version',
      key: 'version',
      width: 180,
      render: (_, record) => {
        const upd = updateStatuses[record.id];
        const activeUpd = upd && !['idle', 'complete'].includes(upd.status);
        const inProgress = upd && ['initiated', 'downloading', 'loading', 'restarting'].includes(upd.status);
        const failedUpd = upd && ['failed', 'timeout', 'error'].includes(upd.status);
        if (!record.version && !upd) {
          return <Text type="secondary">-</Text>;
        }
        const isOutdated = standardVersion && record.version !== standardVersion;
        return (
          <Space size={4} wrap>
            {record.version && (
              <Text code style={isOutdated ? { color: '#faad14' } : undefined}>
                v{record.version}
              </Text>
            )}
            {/* Live update state takes precedence over the outdated/latest tag */}
            {inProgress && (
              <Tooltip title={upd!.message}>
                <Tag color="processing" icon={<LoadingOutlined />} style={{ margin: 0 }}>
                  Updating{upd!.status === 'downloading' && upd!.progress != null ? ` ${upd!.progress}%` : `: ${upd!.status}`}
                </Tag>
              </Tooltip>
            )}
            {failedUpd && (
              <Tooltip title={upd!.error || upd!.message}>
                <Tag color="error" icon={<CloseCircleOutlined />} style={{ margin: 0 }}>
                  Update failed
                </Tag>
              </Tooltip>
            )}
            {!activeUpd && isOutdated && (
              <Tooltip title={`Update available: v${standardVersion}`}>
                <Tag color="warning" icon={<ArrowUpOutlined />} style={{ margin: 0 }}>
                  v{standardVersion}
                </Tag>
              </Tooltip>
            )}
            {!activeUpd && !isOutdated && standardVersion && record.version && (
              <Tag color="success" style={{ margin: 0 }}>Latest</Tag>
            )}
          </Space>
        );
      },
    },
    {
      title: 'Interface',
      dataIndex: 'default_interface',
      key: 'default_interface',
      render: (iface: string | null) => (
        <Text code>{iface || 'eth0'}</Text>
      ),
    },
    {
      title: 'Last Seen',
      dataIndex: 'last_seen',
      key: 'last_seen',
      render: (lastSeen: string | null, record) => {
        // If never connected, show special badge
        if (!record.first_connected_at) {
          return <Tag color="orange">Never connected</Tag>;
        }
        if (!lastSeen) return <Text type="secondary">Unknown</Text>;
        const relative = formatRelativeTime(lastSeen);
        const isRecent = relative === 'just now' || relative.includes('minute');
        return <Text type={isRecent ? 'success' : undefined}>{relative}</Text>;
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="View Details">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetails(record)}
            />
          </Tooltip>
          <Tooltip title="Edit">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="Regenerate Token">
            <Popconfirm
              title="Regenerate authentication token?"
              description="The agent will be disconnected and must be reconfigured."
              onConfirm={() => handleRegenerateToken(record)}
              okText="Regenerate"
              okButtonProps={{ danger: true }}
            >
              <Button type="text" icon={<KeyOutlined />} />
            </Popconfirm>
          </Tooltip>
          <Tooltip title="Delete">
            <Popconfirm
              title="Delete this agent?"
              description={
                <div style={{ maxWidth: 300 }}>
                  <p style={{ margin: '0 0 8px 0' }}>
                    This will disconnect the agent and remove all deployment history.
                  </p>
                  <p style={{ margin: 0, fontWeight: 500 }}>
                    Note: You must manually uninstall the agent software from the remote host
                    by running: <Text code style={{ fontSize: 11 }}>docker compose down</Text> in
                    /opt/packetarch-agent/
                  </p>
                </div>
              }
              onConfirm={() => handleDelete(record.id)}
              okText="Delete"
              okButtonProps={{ danger: true }}
            >
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ];

  // Count online agents
  const onlineCount = agents.filter((a) => a.status === 'online').length;

  return (
    <div>
      <ErrorAlert error={error} onClose={clearError} style={{ marginBottom: 16 }} />

      <Card
        title={
          <Space>
            <RocketOutlined />
            <span>Traffic Agents</span>
            <Badge
              count={onlineCount}
              showZero
              style={{ backgroundColor: onlineCount > 0 ? '#52c41a' : '#d9d9d9' }}
            />
            {standardVersion && (
              <Tooltip title="Current standard agent version available for deployment">
                <Tag color="blue">Standard: v{standardVersion}</Tag>
              </Tooltip>
            )}
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="Refresh">
              <Button icon={<ReloadOutlined />} onClick={() => fetchAgents()} loading={isLoading} />
            </Tooltip>
            <Tooltip
              title={
                buildingImage && buildStatus
                  ? `${buildStatus.message}${buildStatus.version ? ` (v${buildStatus.version})` : ''}`
                  : "Build the agent Docker image for distribution to remote agents"
              }
            >
              <Button
                icon={buildingImage ? <LoadingOutlined spin /> : <BuildOutlined />}
                onClick={handleBuildImage}
                disabled={buildingImage}
              >
                {buildingImage && buildStatus
                  ? `Building${buildStatus.stage ? ` (${buildStatus.stage})` : ''}...`
                  : 'Build Image'}
              </Button>
            </Tooltip>
            <Button icon={<QuestionCircleOutlined />} onClick={() => setInstallDrawerOpen(true)}>
              Installation Guide
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Add Agent
            </Button>
          </Space>
        }
      >
        <Paragraph type="secondary" style={{ marginBottom: 16 }}>
          Traffic agents are remote hosts that connect to PacketArch via WebSocket and execute
          traffic generation commands. Agents automatically update via Watchtower.
        </Paragraph>

        <Table
          columns={columns}
          dataSource={agents}
          rowKey="id"
          loading={isLoading}
          pagination={total > 50 ? { total, pageSize: 50, showSizeChanger: false } : false}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingAgent ? 'Edit Agent' : 'Add Agent'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={500}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="name"
            label="Agent Name"
            rules={[{ required: true, message: 'Please enter a name' }]}
          >
            <Input placeholder="e.g., Traffic-Agent-1" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={2} placeholder="Optional description" />
          </Form.Item>

          <Form.Item
            name="default_interface"
            label={
              <Space>
                Default Interface
                <Tooltip title="Network interface for traffic injection (e.g., eth0, ens192)">
                  <InfoCircleOutlined />
                </Tooltip>
              </Space>
            }
          >
            <Input placeholder="eth0" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setModalVisible(false)}>Cancel</Button>
              <Button type="primary" htmlType="submit" loading={isLoading}>
                {editingAgent ? 'Update' : 'Create'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Token Display Modal */}
      <Modal
        title={
          <Space>
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
            Agent Token
          </Space>
        }
        open={tokenModalVisible}
        onCancel={() => {
          setTokenModalVisible(false);
          setNewAgentToken(null);
        }}
        footer={
          <Button type="primary" onClick={() => setTokenModalVisible(false)}>
            Done
          </Button>
        }
        width={600}
      >
        {newAgentToken && (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <Alert
              message="Save this token!"
              description="This token will only be shown once. Store it securely for use when installing the agent."
              type="warning"
              showIcon
            />

            <div>
              <Text strong>Agent Name:</Text>
              <Paragraph>{newAgentToken.name}</Paragraph>
            </div>

            <div>
              <Text strong>Authentication Token:</Text>
              <Input.Group compact style={{ marginTop: 8 }}>
                <Input
                  value={newAgentToken.token}
                  readOnly
                  style={{ width: 'calc(100% - 100px)', fontFamily: 'monospace' }}
                />
                <Button
                  icon={<CopyOutlined />}
                  onClick={() => copyToClipboard(newAgentToken.token, 'Token')}
                >
                  Copy
                </Button>
              </Input.Group>
            </div>

            <Card size="small" title="Quick Install Command">
              <Paragraph copyable style={{ fontFamily: 'monospace', fontSize: 12 }}>
                {`curl -fsSLk https://${window.location.hostname}/agent/install.sh | sudo bash -s -- --server https://${window.location.hostname} --token "${newAgentToken.token}" --insecure`}
              </Paragraph>
              <Text type="secondary" style={{ fontSize: 11 }}>
                Note: <Text code>-k</Text> and <Text code>--insecure</Text> flags skip SSL verification for self-signed certificates.
              </Text>
            </Card>
          </Space>
        )}
      </Modal>

      {/* Details Drawer */}
      <AgentDetailsDrawer
        agentId={selectedAgentId}
        open={detailsDrawerOpen}
        onClose={() => {
          setDetailsDrawerOpen(false);
          setSelectedAgentId(null);
        }}
      />

      {/* Installation Guide Drawer */}
      <AgentInstallDrawer
        open={installDrawerOpen}
        onClose={() => setInstallDrawerOpen(false)}
      />
    </div>
  );
};

export default AgentsTab;
