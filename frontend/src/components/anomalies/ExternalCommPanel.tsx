/**
 * External Communications Panel - Configure C2, exfil, exploits, and port scans
 *
 * This panel allows users to create external communication campaigns that
 * generate IDS-triggering traffic for security testing.
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
  Collapse,
  Tooltip,
  message,
  Form,
  Input,
  InputNumber,
  Switch,
  Divider,
  Alert,
  Popconfirm,
} from 'antd';
import {
  ApiOutlined,
  CloudServerOutlined,
  RadarChartOutlined,
  BugOutlined,
  DeleteOutlined,
  PlusOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  ScanOutlined,
  SendOutlined,
} from '@ant-design/icons';
import {
  getExternalCommTypes,
  listExternalCampaigns,
  createExternalCampaign,
  deleteExternalCampaign,
  getEventTypeDisplayName,
  getEventTypeColor,
  getMITREUrl,
  formatDuration,
  type ExternalCommTypesResponse,
} from '../../api/externalComms';
import { PanelContainer, LoadingSpinner } from '../common';
import type {
  BeaconPattern,
  ExploitPattern,
  ExternalTemplate,
  ExternalCampaign,
  ExternalEventType,
  CreateExternalCampaignRequest,
} from '../../types';
import { extractErrorMessage } from '../../utils/errorUtils';
import { TEXT_BODY, TEXT_MUTED, BG_PANEL, BG_CODE } from '../../constants/theme';

const { Text, Title } = Typography;
const { Panel } = Collapse;
const { Option } = Select;

interface ExternalCommPanelProps {
  scenarioId: string | null;
  deviceIps?: string[];
}

const EVENT_TYPES: { value: ExternalEventType; label: string; icon: React.ReactNode; description: string }[] = [
  { value: 'c2_beacon', label: 'C2 Beaconing', icon: <CloudServerOutlined />, description: 'Command and control callbacks' },
  { value: 'dns_tunnel', label: 'DNS Tunneling', icon: <ApiOutlined />, description: 'Data exfiltration via DNS' },
  { value: 'http_exfil', label: 'HTTP Exfiltration', icon: <SendOutlined />, description: 'Data exfiltration via HTTP POST' },
  { value: 'exploit', label: 'Exploit Attempt', icon: <BugOutlined />, description: 'ICS exploit signatures' },
  { value: 'port_scan', label: 'Port Scan', icon: <ScanOutlined />, description: 'OT port reconnaissance' },
];

const ExternalCommPanel: React.FC<ExternalCommPanelProps> = ({
  scenarioId,
  deviceIps = [],
}) => {
  const [form] = Form.useForm();
  const [types, setTypes] = useState<ExternalCommTypesResponse | null>(null);
  const [campaigns, setCampaigns] = useState<ExternalCampaign[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingCampaigns, setLoadingCampaigns] = useState(false);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [selectedEventTypes, setSelectedEventTypes] = useState<ExternalEventType[]>([]);

  // Fetch external comm types
  const fetchTypes = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getExternalCommTypes();
      setTypes(data);
    } catch (err) {
      console.error('Failed to fetch external types:', err);
      message.error('Failed to load external communication options');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch campaigns for scenario
  const fetchCampaigns = useCallback(async () => {
    if (!scenarioId) return;

    setLoadingCampaigns(true);
    try {
      const data = await listExternalCampaigns(scenarioId);
      setCampaigns(data);
    } catch (err) {
      console.error('Failed to fetch campaigns:', err);
    } finally {
      setLoadingCampaigns(false);
    }
  }, [scenarioId]);

  useEffect(() => {
    fetchTypes();
  }, [fetchTypes]);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  // Create campaign
  const handleCreateCampaign = async (values: any) => {
    if (!scenarioId) {
      message.error('Please select a scenario first');
      return;
    }

    if (values.internal_device_ips.length === 0) {
      message.error('Please select at least one device');
      return;
    }

    if (selectedEventTypes.length === 0) {
      message.error('Please select at least one event type');
      return;
    }

    setCreating(true);
    try {
      const request: CreateExternalCampaignRequest = {
        name: values.name,
        internal_device_ips: values.internal_device_ips,
        event_types: selectedEventTypes,
        start_time_ms: (values.start_time_s || 0) * 1000,
        duration_ms: (values.duration_s || 300) * 1000,
        use_realistic_ips: values.use_realistic_ips || false,
        c2_pattern: values.c2_pattern,
        c2_protocol: values.c2_protocol,
        beacon_count: values.beacon_count,
        exfil_data_size: values.exfil_data_size,
        exploit_pattern: values.exploit_pattern,
        scan_type: values.scan_type,
        scan_ot_ports: values.scan_ot_ports ?? true,
      };

      await createExternalCampaign(scenarioId, request);
      message.success('External campaign created');
      form.resetFields();
      setSelectedEventTypes([]);
      setShowForm(false);
      fetchCampaigns();
    } catch (err: unknown) {
      console.error('Failed to create campaign:', err);
      message.error(extractErrorMessage(err, 'Failed to create campaign'));
    } finally {
      setCreating(false);
    }
  };

  // Delete campaign
  const handleDeleteCampaign = async (campaignId: string) => {
    if (!scenarioId) return;

    try {
      await deleteExternalCampaign(scenarioId, campaignId);
      message.success('Campaign deleted');
      fetchCampaigns();
    } catch (err) {
      console.error('Failed to delete campaign:', err);
      message.error('Failed to delete campaign');
    }
  };

  const showC2Options = selectedEventTypes.includes('c2_beacon');
  const showExfilOptions = selectedEventTypes.includes('dns_tunnel') || selectedEventTypes.includes('http_exfil');
  const showExploitOptions = selectedEventTypes.includes('exploit');
  const showScanOptions = selectedEventTypes.includes('port_scan');

  return (
    <PanelContainer padding={0}>
      {/* Header Alert */}
      <Alert
        type="warning"
        showIcon
        icon={<WarningOutlined />}
        message="External Communication Traffic"
        description="These patterns generate IDS-triggering traffic. Use only in authorized test environments."
        style={{ background: '#2a1a00' }}
      />

      {/* Active Campaigns */}
      {campaigns.length > 0 && (
        <Card
          size="small"
          title={
            <Space>
              <RadarChartOutlined />
              <span>Active Campaigns</span>
              <Tag>{campaigns.length}</Tag>
            </Space>
          }
          style={{ background: BG_PANEL }}
          styles={{ body: { padding: '8px' } }}
        >
          <List
            size="small"
            dataSource={campaigns}
            renderItem={(campaign) => (
              <CampaignItem
                key={campaign.campaign_id}
                campaign={campaign}
                onDelete={() => handleDeleteCampaign(campaign.campaign_id)}
              />
            )}
          />
        </Card>
      )}

      {/* Available Patterns */}
      {types && (
        <Card
          size="small"
          title={
            <Space>
              <ApiOutlined />
              <span>Available Patterns</span>
            </Space>
          }
          style={{ background: BG_PANEL }}
          styles={{ body: { padding: '8px' } }}
        >
          {loading ? (
            <LoadingSpinner />
          ) : (
            <Collapse ghost expandIconPosition="start">
              {/* Beacon Patterns */}
              <Panel
                key="beacon"
                header={
                  <Space>
                    <CloudServerOutlined style={{ color: '#722ed1' }} />
                    <Text style={{ fontSize: 11 }}>C2 Beacon Patterns</Text>
                    <Tag style={{ fontSize: 9 }}>{types.beacon_patterns.length}</Tag>
                  </Space>
                }
              >
                <List
                  size="small"
                  dataSource={types.beacon_patterns}
                  renderItem={(pattern) => (
                    <PatternItem
                      key={pattern.name}
                      name={pattern.display_name}
                      description={pattern.description}
                      mitre={pattern.mitre_technique}
                      extra={`${formatDuration(pattern.base_interval_ms)} interval`}
                    />
                  )}
                />
              </Panel>

              {/* Exploit Patterns */}
              <Panel
                key="exploit"
                header={
                  <Space>
                    <BugOutlined style={{ color: '#f5222d' }} />
                    <Text style={{ fontSize: 11 }}>Exploit Patterns</Text>
                    <Tag style={{ fontSize: 9 }}>{types.exploit_patterns.length}</Tag>
                  </Space>
                }
              >
                <List
                  size="small"
                  dataSource={types.exploit_patterns}
                  renderItem={(pattern) => (
                    <PatternItem
                      key={pattern.name}
                      name={pattern.display_name}
                      description={pattern.description}
                      mitre={pattern.mitre_technique}
                      extra={`Port ${pattern.target_port} (${pattern.target_protocol})`}
                    />
                  )}
                />
              </Panel>

              {/* Templates */}
              <Panel
                key="templates"
                header={
                  <Space>
                    <WarningOutlined style={{ color: '#fa8c16' }} />
                    <Text style={{ fontSize: 11 }}>External Templates</Text>
                    <Tag style={{ fontSize: 9 }}>{types.external_templates.length}</Tag>
                  </Space>
                }
              >
                <List
                  size="small"
                  dataSource={types.external_templates}
                  renderItem={(template) => (
                    <PatternItem
                      key={template.id}
                      name={template.name}
                      description={template.description || ''}
                      mitre={template.mitre_technique || ''}
                      extra={template.external_protocol || template.anomaly_type}
                    />
                  )}
                />
              </Panel>
            </Collapse>
          )}
        </Card>
      )}

      {/* Create Campaign Form */}
      {showForm ? (
        <Card
          size="small"
          title={
            <Space>
              <PlusOutlined />
              <span>Create External Campaign</span>
            </Space>
          }
          style={{ background: BG_PANEL }}
          extra={
            <Button size="small" onClick={() => setShowForm(false)}>
              Cancel
            </Button>
          }
        >
          <Form
            form={form}
            layout="vertical"
            size="small"
            onFinish={handleCreateCampaign}
            initialValues={{
              duration_s: 300,
              start_time_s: 0,
              beacon_count: 10,
              exfil_data_size: 1024,
              c2_protocol: 'http',
              scan_type: 'syn',
              scan_ot_ports: true,
            }}
          >
            <Form.Item
              label="Campaign Name"
              name="name"
              rules={[{ required: true, message: 'Enter a campaign name' }]}
            >
              <Input placeholder="e.g., C2 Beacon Test" />
            </Form.Item>

            <Form.Item
              label="Target Devices"
              name="internal_device_ips"
              rules={[{ required: true, message: 'Select target devices' }]}
            >
              <Select
                mode="multiple"
                placeholder="Select internal devices"
                options={deviceIps.map((ip) => ({ value: ip, label: ip }))}
              />
            </Form.Item>

            <Form.Item label="Event Types" required>
              <Select
                mode="multiple"
                placeholder="Select event types"
                value={selectedEventTypes}
                onChange={setSelectedEventTypes}
              >
                {EVENT_TYPES.map((type) => (
                  <Option key={type.value} value={type.value}>
                    <Space>
                      {type.icon}
                      <span>{type.label}</span>
                    </Space>
                  </Option>
                ))}
              </Select>
              {selectedEventTypes.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  {selectedEventTypes.map((type) => (
                    <Tag
                      key={type}
                      color={getEventTypeColor(type)}
                      style={{ marginBottom: 4 }}
                    >
                      {getEventTypeDisplayName(type)}
                    </Tag>
                  ))}
                </div>
              )}
            </Form.Item>

            <Space style={{ width: '100%' }} split={<Divider type="vertical" />}>
              <Form.Item label="Start Time (s)" name="start_time_s" style={{ marginBottom: 8 }}>
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item label="Duration (s)" name="duration_s" style={{ marginBottom: 8 }}>
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Space>

            <Form.Item
              name="use_realistic_ips"
              valuePropName="checked"
              style={{ marginBottom: 8 }}
            >
              <Space>
                <Switch size="small" />
                <Text style={{ fontSize: 11 }}>Use Realistic IPs (vs TEST-NET)</Text>
                <Tooltip title="WARNING: Use only in isolated lab environments">
                  <WarningOutlined style={{ color: '#fa8c16' }} />
                </Tooltip>
              </Space>
            </Form.Item>

            {/* C2 Options */}
            {showC2Options && (
              <>
                <Divider style={{ margin: '12px 0' }}>
                  <Text style={{ fontSize: 10, color: TEXT_MUTED }}>C2 Beacon Options</Text>
                </Divider>
                <Space style={{ width: '100%' }}>
                  <Form.Item label="Pattern" name="c2_pattern" style={{ marginBottom: 8 }}>
                    <Select style={{ width: 140 }} placeholder="Select pattern">
                      {types?.beacon_patterns.map((p) => (
                        <Option key={p.name} value={p.name}>{p.display_name}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                  <Form.Item label="Protocol" name="c2_protocol" style={{ marginBottom: 8 }}>
                    <Select style={{ width: 100 }}>
                      <Option value="http">HTTP</Option>
                      <Option value="https">HTTPS</Option>
                      <Option value="dns">DNS</Option>
                    </Select>
                  </Form.Item>
                  <Form.Item label="Count" name="beacon_count" style={{ marginBottom: 8 }}>
                    <InputNumber min={1} max={100} style={{ width: 80 }} />
                  </Form.Item>
                </Space>
              </>
            )}

            {/* Exfil Options */}
            {showExfilOptions && (
              <>
                <Divider style={{ margin: '12px 0' }}>
                  <Text style={{ fontSize: 10, color: TEXT_MUTED }}>Exfiltration Options</Text>
                </Divider>
                <Form.Item label="Data Size (bytes)" name="exfil_data_size" style={{ marginBottom: 8 }}>
                  <InputNumber min={1} max={1048576} style={{ width: '100%' }} />
                </Form.Item>
              </>
            )}

            {/* Exploit Options */}
            {showExploitOptions && (
              <>
                <Divider style={{ margin: '12px 0' }}>
                  <Text style={{ fontSize: 10, color: TEXT_MUTED }}>Exploit Options</Text>
                </Divider>
                <Form.Item label="Exploit Pattern" name="exploit_pattern" style={{ marginBottom: 8 }}>
                  <Select placeholder="Select exploit pattern">
                    {types?.exploit_patterns.map((p) => (
                      <Option key={p.name} value={p.name}>{p.display_name}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </>
            )}

            {/* Scan Options */}
            {showScanOptions && (
              <>
                <Divider style={{ margin: '12px 0' }}>
                  <Text style={{ fontSize: 10, color: TEXT_MUTED }}>Port Scan Options</Text>
                </Divider>
                <Space style={{ width: '100%' }}>
                  <Form.Item label="Scan Type" name="scan_type" style={{ marginBottom: 8 }}>
                    <Select style={{ width: 100 }}>
                      <Option value="syn">SYN</Option>
                      <Option value="fin">FIN</Option>
                      <Option value="xmas">XMAS</Option>
                      <Option value="null">NULL</Option>
                    </Select>
                  </Form.Item>
                  <Form.Item name="scan_ot_ports" valuePropName="checked" style={{ marginBottom: 8 }}>
                    <Space>
                      <Switch size="small" defaultChecked />
                      <Text style={{ fontSize: 11 }}>OT Ports Only</Text>
                    </Space>
                  </Form.Item>
                </Space>
              </>
            )}

            <Button
              type="primary"
              htmlType="submit"
              loading={creating}
              block
              style={{ marginTop: 12 }}
            >
              Create Campaign
            </Button>
          </Form>
        </Card>
      ) : (
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={() => setShowForm(true)}
          block
          disabled={!scenarioId}
        >
          Create External Campaign
        </Button>
      )}
    </PanelContainer>
  );
};

// Pattern Item Component
interface PatternItemProps {
  name: string;
  description: string;
  mitre: string;
  extra?: string;
}

const PatternItem: React.FC<PatternItemProps> = ({ name, description, mitre, extra }) => (
  <div
    style={{
      padding: '6px 8px',
      background: BG_CODE,
      borderRadius: 4,
      marginBottom: 4,
    }}
  >
    <Space direction="vertical" size={2} style={{ width: '100%' }}>
      <Space size={4}>
        <Text style={{ fontSize: 11, color: TEXT_BODY }}>{name}</Text>
        {mitre && (
          <Tooltip title="View MITRE ATT&CK technique">
            <Tag
              color="volcano"
              style={{ fontSize: 9, cursor: 'pointer' }}
              onClick={() => window.open(getMITREUrl(mitre), '_blank')}
            >
              {mitre}
            </Tag>
          </Tooltip>
        )}
        {extra && (
          <Text style={{ fontSize: 9, color: TEXT_MUTED }}>{extra}</Text>
        )}
      </Space>
      <Text style={{ fontSize: 10, color: TEXT_MUTED }}>{description}</Text>
    </Space>
  </div>
);

// Campaign Item Component
interface CampaignItemProps {
  campaign: ExternalCampaign;
  onDelete: () => void;
}

const CampaignItem: React.FC<CampaignItemProps> = ({ campaign, onDelete }) => (
  <div
    style={{
      padding: '8px',
      background: BG_CODE,
      borderRadius: 4,
      marginBottom: 4,
    }}
  >
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
      <Space direction="vertical" size={2}>
        <Text style={{ fontSize: 11, color: TEXT_BODY, fontWeight: 500 }}>
          {campaign.name}
        </Text>
        <Space size={4} wrap>
          {campaign.event_types.map((type) => (
            <Tag
              key={type}
              color={getEventTypeColor(type as ExternalEventType)}
              style={{ fontSize: 9 }}
            >
              {getEventTypeDisplayName(type as ExternalEventType)}
            </Tag>
          ))}
        </Space>
        <Text style={{ fontSize: 10, color: TEXT_MUTED }}>
          {campaign.event_count} events • {campaign.internal_devices.length} devices •{' '}
          {formatDuration(campaign.duration_ms)}
        </Text>
      </Space>
      <Popconfirm
        title="Delete this campaign?"
        onConfirm={onDelete}
        okText="Delete"
        cancelText="Cancel"
      >
        <Button
          type="text"
          size="small"
          danger
          icon={<DeleteOutlined />}
        />
      </Popconfirm>
    </div>
  </div>
);

export default ExternalCommPanel;
