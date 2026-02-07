/**
 * TemplateWizardModal - Multi-step wizard for creating a scenario from template.
 *
 * Steps:
 *   1. Select Industry Vertical
 *   2. Select Template
 *   3. Name Your Scenario (with optional AI naming)
 */

import React, { useState } from 'react';
import {
  Modal,
  Form,
  Input,
  Space,
  Button,
  Typography,
  Card,
  Row,
  Col,
  Spin,
  Tag,
  Checkbox,
  Divider,
  Tooltip,
} from 'antd';
import {
  RocketOutlined,
  FolderOutlined,
  ExperimentOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { templatesApi, type TemplateSummary } from '../../api/templates';
import type { CreateFromTemplateRequest } from '../../api/templates';
import { verticalConfig } from './scenarioConstants';

const { Text, Paragraph } = Typography;

export interface TemplateWizardModalProps {
  open: boolean;
  loading: boolean;
  onCancel: () => void;
  onSubmit: (data: CreateFromTemplateRequest) => void;
}

const TemplateWizardModal: React.FC<TemplateWizardModalProps> = ({
  open,
  loading,
  onCancel,
  onSubmit,
}) => {
  const [selectedVertical, setSelectedVertical] = useState<string | null>(
    null,
  );
  const [selectedTemplate, setSelectedTemplate] =
    useState<TemplateSummary | null>(null);
  const [useAINaming, setUseAINaming] = useState(false);
  const [processContext, setProcessContext] = useState('');
  const [form] = Form.useForm();

  // Fetch verticals
  const { data: verticals, isLoading: verticalsLoading } = useQuery({
    queryKey: ['verticals'],
    queryFn: () => templatesApi.getVerticals(),
    enabled: open,
  });

  // Fetch templates for selected vertical
  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ['templates', selectedVertical],
    queryFn: () => templatesApi.list(selectedVertical || undefined),
    enabled: open && !!selectedVertical,
  });

  const handleCancel = () => {
    setSelectedVertical(null);
    setSelectedTemplate(null);
    setUseAINaming(false);
    setProcessContext('');
    form.resetFields();
    onCancel();
  };

  const handleFinish = (values: {
    scenario_name: string;
    description?: string;
    apply_learned_patterns?: boolean;
  }) => {
    if (!selectedTemplate) return;
    onSubmit({
      vertical: selectedTemplate.vertical,
      template_name: selectedTemplate.name,
      scenario_name: values.scenario_name,
      description: values.description,
      auto_assign_addresses: true,
      phase_preset: 'standard',
      apply_learned_patterns: values.apply_learned_patterns ?? true,
      use_ai_naming: useAINaming,
      process_context: useAINaming ? processContext : undefined,
    });
  };

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background:
                'linear-gradient(135deg, #6CC04A20 0%, #6CC04A10 100%)',
              border: '1px solid #6CC04A40',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#6CC04A',
            }}
          >
            <RocketOutlined style={{ fontSize: 18 }} />
          </div>
          <span style={{ color: '#fff', fontSize: 16 }}>
            Create from Template
          </span>
        </div>
      }
      open={open}
      onCancel={handleCancel}
      footer={null}
      width={800}
      styles={{
        header: {
          background: '#141428',
          borderBottom: '1px solid #2d2d52',
        },
        body: { background: '#1a1a2e', padding: 24 },
        content: { background: '#141428' },
      }}
    >
      {/* Step 1: Select Vertical */}
      <div style={{ marginBottom: 24 }}>
        <Text
          strong
          style={{ color: '#fff', display: 'block', marginBottom: 12 }}
        >
          1. Select Industry Vertical
        </Text>
        {verticalsLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin />
            <div style={{ marginTop: 12, color: '#6b6b8a' }}>
              Loading verticals...
            </div>
          </div>
        ) : !verticals || verticals.length === 0 ? (
          <div
            style={{ textAlign: 'center', padding: 40, color: '#6b6b8a' }}
          >
            No verticals available. Please check the backend templates
            configuration.
          </div>
        ) : (
          <Row gutter={[12, 12]}>
            {verticals.map((vertical) => {
              const config = verticalConfig[vertical.id];
              const isSelected = selectedVertical === vertical.id;
              return (
                <Col span={6} key={vertical.id}>
                  <Card
                    hoverable
                    onClick={() => {
                      setSelectedVertical(vertical.id);
                      setSelectedTemplate(null);
                    }}
                    style={{
                      background: isSelected
                        ? `${config?.color || '#049FD9'}20`
                        : '#141428',
                      border: `1px solid ${isSelected ? config?.color || '#049FD9' : '#2d2d52'}`,
                      cursor: 'pointer',
                    }}
                    bodyStyle={{ padding: 16, textAlign: 'center' }}
                  >
                    <div
                      style={{
                        fontSize: 24,
                        color: config?.color || '#049FD9',
                        marginBottom: 8,
                      }}
                    >
                      {config?.icon || <FolderOutlined />}
                    </div>
                    <Text style={{ color: '#fff', display: 'block' }}>
                      {config?.label || vertical.name}
                    </Text>
                    <Text style={{ color: '#6b6b8a', fontSize: 11 }}>
                      {vertical.template_count} template
                      {vertical.template_count !== 1 ? 's' : ''}
                    </Text>
                  </Card>
                </Col>
              );
            })}
          </Row>
        )}
      </div>

      {/* Step 2: Select Template */}
      {selectedVertical && (
        <div style={{ marginBottom: 24 }}>
          <Text
            strong
            style={{ color: '#fff', display: 'block', marginBottom: 12 }}
          >
            2. Select Template
          </Text>
          {templatesLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin />
              <div style={{ marginTop: 12, color: '#6b6b8a' }}>
                Loading templates...
              </div>
            </div>
          ) : !templates ||
            templates.filter((t) => t.vertical === selectedVertical)
              .length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: 40,
                color: '#6b6b8a',
              }}
            >
              No templates available for this vertical.
            </div>
          ) : (
            <Row gutter={[12, 12]}>
              {templates
                .filter((t) => t.vertical === selectedVertical)
                .map((template) => {
                  const isSelected =
                    selectedTemplate?.name === template.name;
                  const verticalInfo = verticalConfig[template.vertical];
                  return (
                    <Col span={12} key={template.name}>
                      <Card
                        hoverable
                        onClick={() => setSelectedTemplate(template)}
                        style={{
                          background: isSelected ? '#1a3320' : '#141428',
                          border: `1px solid ${isSelected ? '#6CC04A' : '#2d2d52'}`,
                          cursor: 'pointer',
                        }}
                        bodyStyle={{ padding: 16 }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'flex-start',
                          }}
                        >
                          <div style={{ flex: 1 }}>
                            <Text
                              strong
                              style={{
                                color: '#fff',
                                display: 'block',
                                marginBottom: 4,
                              }}
                            >
                              {template.display_name}
                            </Text>
                            <Paragraph
                              ellipsis={{ rows: 2 }}
                              style={{
                                color: '#a8a8c0',
                                fontSize: 12,
                                marginBottom: 8,
                              }}
                            >
                              {template.description}
                            </Paragraph>
                            <Space size={4}>
                              <Tag
                                style={{
                                  background: '#2d2d52',
                                  border: 'none',
                                  color: '#fff',
                                  fontSize: 10,
                                }}
                              >
                                {template.device_count} devices
                              </Tag>
                              {template.protocols.slice(0, 2).map((p) => (
                                <Tag
                                  key={p}
                                  style={{
                                    background: `${verticalInfo?.color || '#049FD9'}20`,
                                    border: 'none',
                                    color:
                                      verticalInfo?.color || '#049FD9',
                                    fontSize: 10,
                                  }}
                                >
                                  {p}
                                </Tag>
                              ))}
                            </Space>
                          </div>
                          {isSelected && (
                            <div
                              style={{
                                width: 24,
                                height: 24,
                                borderRadius: 12,
                                background: '#6CC04A',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: '#fff',
                                fontSize: 14,
                                flexShrink: 0,
                                marginLeft: 8,
                              }}
                            >
                              ✓
                            </div>
                          )}
                        </div>
                      </Card>
                    </Col>
                  );
                })}
            </Row>
          )}
        </div>
      )}

      {/* Step 3: Name Your Scenario */}
      {selectedTemplate && (
        <div>
          <Text
            strong
            style={{ color: '#fff', display: 'block', marginBottom: 12 }}
          >
            3. Name Your Scenario
          </Text>
          <Form form={form} layout="vertical" onFinish={handleFinish}>
            <Form.Item
              name="scenario_name"
              label={
                <Text style={{ color: '#a8a8c0' }}>Scenario Name</Text>
              }
              rules={[
                {
                  required: true,
                  message: 'Please enter a scenario name',
                },
              ]}
              initialValue={`${selectedTemplate.display_name} - ${new Date().toLocaleDateString()}`}
            >
              <Input placeholder="My OT Scenario" />
            </Form.Item>

            <Form.Item
              name="description"
              label={
                <Text style={{ color: '#a8a8c0' }}>
                  Description (optional)
                </Text>
              }
              initialValue={selectedTemplate.description}
            >
              <Input.TextArea rows={2} />
            </Form.Item>

            <Form.Item
              name="apply_learned_patterns"
              valuePropName="checked"
              initialValue={true}
            >
              <Checkbox style={{ color: '#a8a8c0' }}>
                <Space>
                  <span>Apply learned traffic patterns</span>
                  <Tooltip title="Enhance realism using patterns learned from real PCAP traffic data">
                    <ExperimentOutlined style={{ color: '#52c41a' }} />
                  </Tooltip>
                </Space>
              </Checkbox>
            </Form.Item>

            <Divider style={{ borderColor: '#2d2d52', margin: '16px 0' }} />

            <Form.Item style={{ marginBottom: useAINaming ? 12 : 0 }}>
              <Space
                direction="vertical"
                style={{ width: '100%' }}
                size={8}
              >
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Templates include meaningful device names by default
                  (e.g., &quot;CNC_Machining_Main_PLC&quot;).
                </Text>
                <Checkbox
                  checked={useAINaming}
                  onChange={(e) => setUseAINaming(e.target.checked)}
                  style={{ color: '#a8a8c0' }}
                >
                  <Space>
                    <span>Customize device names with AI</span>
                    <Tooltip title="Use AI to generate device names based on your specific facility or process">
                      <RobotOutlined style={{ color: '#5a9fd4' }} />
                    </Tooltip>
                  </Space>
                </Checkbox>
              </Space>
            </Form.Item>

            {useAINaming && (
              <Form.Item
                label={
                  <Text style={{ color: '#a8a8c0' }}>
                    Describe your facility or process
                  </Text>
                }
                help="e.g., 'candy factory', 'dairy processing plant', 'solar panel manufacturing'"
              >
                <Input.TextArea
                  value={processContext}
                  onChange={(e) => setProcessContext(e.target.value)}
                  placeholder="Enter process description for AI to generate contextual device names"
                  rows={2}
                  maxLength={200}
                  showCount
                />
              </Form.Item>
            )}

            <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
              <Space
                style={{ width: '100%', justifyContent: 'flex-end' }}
              >
                <Button onClick={handleCancel}>Cancel</Button>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  style={{
                    background: '#6CC04A',
                    borderColor: '#6CC04A',
                  }}
                  icon={<RocketOutlined />}
                >
                  Create Scenario
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </div>
      )}
    </Modal>
  );
};

export default TemplateWizardModal;
