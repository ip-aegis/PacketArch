/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Campaign Builder - Configure and create anomaly injection campaigns
 */

import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  InputNumber,
  Space,
  Typography,
  Tag,
  Button,
  List,
  Divider,
  Alert,
  message,
} from 'antd';
import {
  ThunderboltOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import {
  createCampaign,
  deleteCampaign,
  getAnomalyTemplate,
  type AnomalyCampaign,
  type AnomalyTemplate,
} from '../../api/anomalies';

const { Text } = Typography;

interface CampaignBuilderProps {
  scenarioId: string;
  visible: boolean;
  selectedTemplateIds: string[];
  onClose: () => void;
  onCampaignCreated?: (campaign: AnomalyCampaign) => void;
}

const severityColors: Record<string, string> = {
  low: 'default',
  medium: 'warning',
  high: 'orange',
  critical: 'error',
};

const CampaignBuilder: React.FC<CampaignBuilderProps> = ({
  scenarioId,
  visible,
  selectedTemplateIds,
  onClose,
  onCampaignCreated,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<AnomalyTemplate[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);

  // Fetch selected templates
  useEffect(() => {
    if (!visible || selectedTemplateIds.length === 0) return;

    const fetchTemplates = async () => {
      setLoadingTemplates(true);
      try {
        const templatePromises = selectedTemplateIds.map((id) =>
          getAnomalyTemplate(id)
        );
        const fetchedTemplates = await Promise.all(templatePromises);
        setTemplates(fetchedTemplates);
      } catch (err) {
        console.error('Failed to fetch templates:', err);
        message.error('Failed to load template details');
      } finally {
        setLoadingTemplates(false);
      }
    };

    fetchTemplates();
  }, [visible, selectedTemplateIds]);

  // Handle form submit
  const handleSubmit = async (values: {
    name: string;
    start_time_seconds: number;
    duration_seconds?: number;
  }) => {
    if (templates.length === 0) {
      message.warning('No anomaly templates selected');
      return;
    }

    setLoading(true);
    try {
      const result = await createCampaign(scenarioId, {
        name: values.name,
        anomaly_types: templates.map((t) => t.anomaly_type),
        start_time_ms: values.start_time_seconds * 1000,
        duration_ms: values.duration_seconds
          ? values.duration_seconds * 1000
          : undefined,
      });

      message.success(`Campaign "${result.name}" created with ${result.anomaly_count} anomalies`);
      onCampaignCreated?.({
        id: result.campaign_id,
        name: result.name,
        start_time_ms: values.start_time_seconds * 1000,
        duration_ms: values.duration_seconds ? values.duration_seconds * 1000 : null,
        target_flow_ids: null,
        anomaly_types: templates.map((t) => t.anomaly_type),
        templates: result.templates,
      });
      form.resetFields();
      onClose();
    } catch (err) {
      console.error('Failed to create campaign:', err);
      message.error('Failed to create campaign');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={
        <Space>
          <ThunderboltOutlined />
          <span>Create Anomaly Campaign</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>
          Cancel
        </Button>,
        <Button
          key="create"
          type="primary"
          loading={loading}
          onClick={() => form.submit()}
        >
          Create Campaign
        </Button>,
      ]}
      width={600}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          start_time_seconds: 60,
          duration_seconds: 300,
        }}
      >
        <Form.Item
          name="name"
          label="Campaign Name"
          rules={[{ required: true, message: 'Enter a campaign name' }]}
        >
          <Input placeholder="e.g., Timing Attack Test" />
        </Form.Item>

        <Divider style={{ margin: '16px 0' }} />

        {/* Selected Anomalies */}
        <div style={{ marginBottom: 16 }}>
          <Text strong style={{ display: 'block', marginBottom: 8 }}>
            <ThunderboltOutlined /> Selected Anomalies ({templates.length})
          </Text>
          {loadingTemplates ? (
            <Text style={{ color: '#6a8caf', fontSize: 12 }}>
              Loading templates...
            </Text>
          ) : (
            <List
              size="small"
              dataSource={templates}
              renderItem={(template) => (
                <List.Item
                  style={{
                    padding: '6px 8px',
                    background: '#0d1117',
                    borderRadius: 4,
                    marginBottom: 4,
                  }}
                >
                  <Space size={4}>
                    <Text style={{ fontSize: 11, color: '#c9d1d9' }}>
                      {template.name}
                    </Text>
                    <Tag
                      color={severityColors[template.severity]}
                      style={{ fontSize: 9 }}
                    >
                      {template.severity}
                    </Tag>
                    <Tag style={{ fontSize: 9 }}>{template.category}</Tag>
                  </Space>
                </List.Item>
              )}
            />
          )}
        </div>

        <Divider style={{ margin: '16px 0' }} />

        {/* Timing Configuration */}
        <Text strong style={{ display: 'block', marginBottom: 8 }}>
          <ClockCircleOutlined /> Timing Configuration
        </Text>

        <Space style={{ width: '100%' }} size="middle">
          <Form.Item
            name="start_time_seconds"
            label="Start Time (seconds)"
            rules={[{ required: true, message: 'Enter start time' }]}
            style={{ marginBottom: 0, flex: 1 }}
          >
            <InputNumber
              min={0}
              style={{ width: '100%' }}
              placeholder="60"
              addonAfter="s"
            />
          </Form.Item>

          <Form.Item
            name="duration_seconds"
            label="Duration (seconds)"
            style={{ marginBottom: 0, flex: 1 }}
          >
            <InputNumber
              min={0}
              style={{ width: '100%' }}
              placeholder="Leave empty for entire scenario"
              addonAfter="s"
            />
          </Form.Item>
        </Space>

        <Alert
          message="Campaign will inject anomalies randomly during the specified time window"
          type="info"
          showIcon
          style={{ marginTop: 16 }}
        />
      </Form>
    </Modal>
  );
};

// Campaign List Component for displaying active campaigns
interface CampaignListProps {
  scenarioId: string;
  campaigns: AnomalyCampaign[];
  onDelete: (campaignId: string) => void;
  onRefresh: () => void;
}

export const CampaignList: React.FC<CampaignListProps> = ({
  scenarioId,
  campaigns,
  onDelete,
  onRefresh,
}) => {
  const [deleting, setDeleting] = useState<string | null>(null);

  const handleDelete = async (campaignId: string) => {
    setDeleting(campaignId);
    try {
      await deleteCampaign(scenarioId, campaignId);
      message.success('Campaign deleted');
      onDelete(campaignId);
      onRefresh();
    } catch (err) {
      console.error('Failed to delete campaign:', err);
      message.error('Failed to delete campaign');
    } finally {
      setDeleting(null);
    }
  };

  if (campaigns.length === 0) {
    return null;
  }

  return (
    <div style={{ marginTop: 16 }}>
      <Text strong style={{ display: 'block', marginBottom: 8, fontSize: 12 }}>
        <ThunderboltOutlined /> Active Campaigns ({campaigns.length})
      </Text>
      <List
        size="small"
        dataSource={campaigns}
        renderItem={(campaign) => (
          <List.Item
            style={{
              padding: '8px',
              background: '#0d1117',
              borderRadius: 4,
              marginBottom: 4,
            }}
            actions={[
              <Button
                key="delete"
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                loading={deleting === campaign.id}
                onClick={() => handleDelete(campaign.id)}
              />,
            ]}
          >
            <List.Item.Meta
              title={
                <Text style={{ fontSize: 11, color: '#c9d1d9' }}>
                  {campaign.name}
                </Text>
              }
              description={
                <Space direction="vertical" size={0}>
                  <Text style={{ fontSize: 10, color: '#6a8caf' }}>
                    Start: {(campaign.start_time_ms / 1000).toFixed(0)}s
                    {campaign.duration_ms && ` | Duration: ${(campaign.duration_ms / 1000).toFixed(0)}s`}
                  </Text>
                  <Space size={4} wrap>
                    {campaign.anomaly_types.map((type) => (
                      <Tag key={type} style={{ fontSize: 9 }}>
                        {type}
                      </Tag>
                    ))}
                  </Space>
                </Space>
              }
            />
          </List.Item>
        )}
      />
    </div>
  );
};

export default CampaignBuilder;
