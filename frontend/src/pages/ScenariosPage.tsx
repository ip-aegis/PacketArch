/**
 * Scenarios Page - List, create, and manage scenarios
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Typography,
  Input,
  Select,
  Card,
  Row,
  Col,
  Tag,
  Space,
  Pagination,
  Empty,
  Spin,
  Button,
  Tooltip,
  Modal,
  Form,
  Dropdown,
  Popconfirm,
  App,
  Checkbox,
} from 'antd';
import type { MenuProps } from 'antd';
import {
  SearchOutlined,
  PlusOutlined,
  EditOutlined,
  CopyOutlined,
  DeleteOutlined,
  ExportOutlined,
  ImportOutlined,
  ClockCircleOutlined,
  ApiOutlined,
  MoreOutlined,
  FolderOutlined,
  ToolOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
  FileAddOutlined,
  RocketOutlined,
  InboxOutlined,
} from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { Upload } from 'antd';

const { Dragger } = Upload;
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { scenariosApi, type ScenarioFilters, type ScenarioSummary, type ScenarioCreate } from '../api/scenarios';
import { templatesApi, type TemplateSummary, type CreateFromTemplateRequest } from '../api/templates';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// Vertical colors and icons
const verticalConfig: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  manufacturing: { icon: <ToolOutlined />, color: '#6CC04A', label: 'Manufacturing' },
  water_wastewater: { icon: <ExperimentOutlined />, color: '#00BCEB', label: 'Water/Wastewater' },
  energy_power: { icon: <ThunderboltOutlined />, color: '#FBAB18', label: 'Energy/Power' },
  oil_gas: { icon: <ApiOutlined />, color: '#FF7043', label: 'Oil & Gas' },
};

const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`;
  return `${(ms / 3600000).toFixed(1)}h`;
};

const ScenariosPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { modal, message } = App.useApp();
  const [filters, setFilters] = useState<ScenarioFilters>({
    page: 1,
    page_size: 12,
  });
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [selectedVertical, setSelectedVertical] = useState<string | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateSummary | null>(null);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importFileData, setImportFileData] = useState<Record<string, unknown> | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [createForm] = Form.useForm();
  const [templateForm] = Form.useForm();

  // Fetch scenarios
  const { data, isLoading, error } = useQuery({
    queryKey: ['scenarios', filters],
    queryFn: () => scenariosApi.list(filters),
  });

  // Fetch templates
  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ['templates', selectedVertical],
    queryFn: () => templatesApi.list(selectedVertical || undefined),
    enabled: templateModalOpen && !!selectedVertical,
  });

  // Fetch verticals
  const { data: verticals, isLoading: verticalsLoading } = useQuery({
    queryKey: ['verticals'],
    queryFn: () => templatesApi.getVerticals(),
    enabled: templateModalOpen,
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: ScenarioCreate) => scenariosApi.create(data),
    onSuccess: (scenario) => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      message.success('Scenario created successfully');
      setCreateModalOpen(false);
      createForm.resetFields();
      // Navigate to the scenario studio with the new scenario
      navigate(`/studio?scenario=${scenario.id}`);
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail || error.message || 'Unknown error';
      message.error(`Failed to create scenario: ${detail}`);
    },
  });

  // Duplicate mutation
  const duplicateMutation = useMutation({
    mutationFn: (id: string) => scenariosApi.duplicate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      message.success('Scenario duplicated successfully');
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail || error.message || 'Unknown error';
      message.error(`Failed to duplicate scenario: ${detail}`);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => scenariosApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      message.success('Scenario deleted successfully');
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail || error.message || 'Unknown error';
      message.error(`Failed to delete scenario: ${detail}`);
    },
  });

  // Create from template mutation
  const createFromTemplateMutation = useMutation({
    mutationFn: (data: CreateFromTemplateRequest) => templatesApi.createFromTemplate(data),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      const learnedInfo = result.learned_patterns_applied
        ? ` (enhanced with learned patterns for ${result.protocols_enhanced?.join(', ') || 'all protocols'})`
        : '';
      message.success(`Scenario created with ${result.device_count} devices and ${result.flow_count} flows${learnedInfo}`);
      setTemplateModalOpen(false);
      setSelectedVertical(null);
      setSelectedTemplate(null);
      templateForm.resetFields();
      navigate(`/studio?scenario=${result.scenario_id}`);
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail || error.message || 'Unknown error';
      message.error(`Failed to create scenario from template: ${detail}`);
    },
  });

  // Import scenario mutation
  const importMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => scenariosApi.import(data),
    onSuccess: (scenario) => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      message.success('Scenario imported successfully');
      setImportModalOpen(false);
      setImportFileData(null);
      navigate(`/studio?scenario=${scenario.id}`);
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail || error.message || 'Unknown error';
      message.error(`Failed to import scenario: ${detail}`);
    },
  });

  // Bulk delete mutation
  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: string[]) => scenariosApi.bulkDelete(ids),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      message.success(result.message);
      setSelectedIds(new Set());
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail || error.message || 'Unknown error';
      message.error(`Failed to delete scenarios: ${detail}`);
    },
  });

  const handleToggleSelect = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (!data?.items) return;
    if (selectedIds.size === data.items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(data.items.map((s) => s.id)));
    }
  };

  const handleBulkDelete = () => {
    modal.confirm({
      title: 'Delete Selected Scenarios',
      content: `Are you sure you want to delete ${selectedIds.size} scenario(s)? This action cannot be undone.`,
      okText: 'Delete All',
      okType: 'danger',
      centered: true,
      onOk: () => bulkDeleteMutation.mutateAsync(Array.from(selectedIds)),
    });
  };

  const handleFilterChange = (key: keyof ScenarioFilters, value: string | undefined) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value || undefined,
      page: 1,
    }));
  };

  const handlePageChange = (page: number, pageSize: number) => {
    setFilters((prev) => ({
      ...prev,
      page,
      page_size: pageSize,
    }));
  };

  const handleCreateScenario = (values: ScenarioCreate) => {
    createMutation.mutate({
      ...values,
      definition: {
        devices: {},
        flows: {},
        zones: {},
        phases: [],
      },
    });
  };

  const handleCreateFromTemplate = (values: { scenario_name: string; description?: string; apply_learned_patterns?: boolean }) => {
    if (!selectedTemplate) {
      message.error('Please select a template');
      return;
    }
    createFromTemplateMutation.mutate({
      vertical: selectedTemplate.vertical,
      template_name: selectedTemplate.name,
      scenario_name: values.scenario_name,
      description: values.description,
      auto_assign_addresses: true,
      phase_preset: 'standard',
      apply_learned_patterns: values.apply_learned_patterns ?? true,
    });
  };

  const handleOpenScenario = (id: string) => {
    navigate(`/studio?scenario=${id}`);
  };

  const handleExportScenario = async (id: string, name: string) => {
    try {
      const data = await scenariosApi.export(id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_scenario.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      message.success('Scenario exported successfully');
    } catch {
      message.error('Failed to export scenario');
    }
  };

  const getScenarioMenuItems = (scenario: ScenarioSummary): MenuProps['items'] => [
    {
      key: 'open',
      icon: <EditOutlined />,
      label: 'Open in Studio',
    },
    {
      key: 'duplicate',
      icon: <CopyOutlined />,
      label: 'Duplicate',
    },
    {
      key: 'export',
      icon: <ExportOutlined />,
      label: 'Export JSON',
    },
    { type: 'divider' },
    {
      key: 'delete',
      icon: <DeleteOutlined />,
      label: 'Delete',
      danger: true,
    },
  ];

  const handleMenuClick = (scenario: ScenarioSummary, info: { key: string; domEvent: React.MouseEvent }) => {
    // Stop event propagation to prevent Card onClick from firing
    info.domEvent.stopPropagation();
    info.domEvent.preventDefault();

    switch (info.key) {
      case 'open':
        handleOpenScenario(scenario.id);
        break;
      case 'duplicate':
        duplicateMutation.mutate(scenario.id);
        break;
      case 'export':
        handleExportScenario(scenario.id, scenario.name);
        break;
      case 'delete':
        modal.confirm({
          title: 'Delete Scenario',
          content: `Are you sure you want to delete "${scenario.name}"? This action cannot be undone.`,
          okText: 'Delete',
          okType: 'danger',
          centered: true,
          onOk: () => deleteMutation.mutateAsync(scenario.id),
        });
        break;
    }
  };

  const renderScenarioCard = (scenario: ScenarioSummary) => {
    const verticalInfo = scenario.vertical ? verticalConfig[scenario.vertical] : null;
    const isSelected = selectedIds.has(scenario.id);

    return (
      <Card
        key={scenario.id}
        hoverable
        style={{
          background: isSelected ? '#1a2433' : '#141428',
          border: isSelected ? '1px solid #1890ff' : '1px solid #2d2d52',
          borderRadius: 12,
        }}
        bodyStyle={{ padding: 20 }}
        onClick={() => handleOpenScenario(scenario.id)}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 0 }}>
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
              onClick={(e) => handleToggleSelect(scenario.id, e)}
            >
              {isSelected ? (
                <Checkbox checked style={{ position: 'absolute' }} onClick={(e) => e.stopPropagation()} />
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
              items: getScenarioMenuItems(scenario),
              onClick: (info) => handleMenuClick(scenario, info),
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
            style={{ color: '#a8a8c0', fontSize: 13, marginBottom: 16, minHeight: 40 }}
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
            <Text style={{ color: '#6b6b8a', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Devices
            </Text>
            <div style={{ color: '#fff', fontSize: 18, fontWeight: 600 }}>{scenario.device_count}</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <Text style={{ color: '#6b6b8a', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Flows
            </Text>
            <div style={{ color: '#fff', fontSize: 18, fontWeight: 600 }}>{scenario.flow_count}</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <Text style={{ color: '#6b6b8a', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
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
              Updated {new Date(scenario.updated_at).toLocaleDateString()}
            </Text>
          </Space>
          <Space size={4}>
            {scenario.has_learned_patterns && (
              <Tooltip title={`Enhanced with learned patterns for: ${scenario.protocols_enhanced?.join(', ') || 'multiple protocols'}`}>
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
            <Tag style={{ background: '#2d2d52', border: 'none', color: '#6b6b8a', fontSize: 10 }}>
              v{scenario.version}
            </Tag>
          </Space>
        </div>
      </Card>
    );
  };

  return (
    <div>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <Title level={3} style={{ color: '#fff', margin: 0 }}>
            Scenarios
          </Title>
          <Text style={{ color: '#6b6b8a' }}>Create and manage your OT traffic simulation scenarios</Text>
        </div>
        <Space>
          {selectedIds.size > 0 && (
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleBulkDelete}
              loading={bulkDeleteMutation.isPending}
            >
              Delete Selected ({selectedIds.size})
            </Button>
          )}
          <Button icon={<ImportOutlined />} style={{ borderColor: '#2d2d52' }} onClick={() => setImportModalOpen(true)}>
            Import
          </Button>
          <Button
            icon={<RocketOutlined />}
            style={{ borderColor: '#6CC04A', color: '#6CC04A' }}
            onClick={() => setTemplateModalOpen(true)}
          >
            From Template
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
            New Blank
          </Button>
        </Space>
      </div>

      {/* Filters */}
      <Card
        style={{
          background: '#141428',
          border: '1px solid #2d2d52',
          marginBottom: 24,
        }}
        bodyStyle={{ padding: '16px 20px' }}
      >
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Input
              placeholder="Search scenarios..."
              prefix={<SearchOutlined style={{ color: '#6b6b8a' }} />}
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              allowClear
              style={{
                background: '#1a1a2e',
                border: '1px solid #2d2d52',
              }}
            />
          </Col>
          <Col>
            <Select
              placeholder="Vertical"
              allowClear
              value={filters.vertical}
              onChange={(value) => handleFilterChange('vertical', value)}
              style={{ width: 180 }}
              popupClassName="dark-dropdown"
            >
              {Object.entries(verticalConfig).map(([key, config]) => (
                <Option key={key} value={key}>
                  <Space>
                    {config.icon}
                    {config.label}
                  </Space>
                </Option>
              ))}
            </Select>
          </Col>
        </Row>
      </Card>

      {/* Results */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#6b6b8a' }}>Loading scenarios...</div>
        </div>
      ) : error ? (
        <Card style={{ background: '#141428', border: '1px solid #2d2d52' }}>
          <Empty description={<Text style={{ color: '#6b6b8a' }}>Failed to load scenarios</Text>} />
        </Card>
      ) : data?.items.length === 0 ? (
        <Card
          style={{
            background: '#141428',
            border: '1px solid #2d2d52',
            textAlign: 'center',
            padding: 60,
          }}
        >
          <FolderOutlined style={{ fontSize: 48, color: '#2d2d52', marginBottom: 16 }} />
          <Title level={4} style={{ color: '#fff', marginBottom: 8 }}>
            No scenarios yet
          </Title>
          <Text style={{ color: '#6b6b8a', display: 'block', marginBottom: 24 }}>
            Create your first scenario to start simulating OT traffic
          </Text>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
            Create Scenario
          </Button>
        </Card>
      ) : (
        <>
          {/* Stats & Select All */}
          <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ color: '#6b6b8a', fontSize: 13 }}>
              Showing {data?.items.length} of {data?.total} scenarios
            </div>
            <Checkbox
              checked={data?.items && selectedIds.size === data.items.length && data.items.length > 0}
              indeterminate={selectedIds.size > 0 && selectedIds.size < (data?.items?.length || 0)}
              onChange={handleSelectAll}
              style={{ color: '#6b6b8a' }}
            >
              Select All
            </Checkbox>
          </div>

          {/* Grid View */}
          <Row gutter={[16, 16]}>
            {data?.items.map((scenario) => (
              <Col key={scenario.id} xs={24} sm={12} lg={8} xl={6}>
                {renderScenarioCard(scenario)}
              </Col>
            ))}
          </Row>

          {/* Pagination */}
          {(data?.total || 0) > (filters.page_size || 12) && (
            <div style={{ marginTop: 24, textAlign: 'center' }}>
              <Pagination
                current={filters.page}
                pageSize={filters.page_size}
                total={data?.total || 0}
                onChange={handlePageChange}
                showSizeChanger
                showQuickJumper
                pageSizeOptions={['12', '24', '48']}
              />
            </div>
          )}
        </>
      )}

      {/* Create Scenario Modal */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 8,
                background: 'linear-gradient(135deg, #049FD920 0%, #049FD910 100%)',
                border: '1px solid #049FD940',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#049FD9',
              }}
            >
              <PlusOutlined style={{ fontSize: 18 }} />
            </div>
            <span style={{ color: '#fff', fontSize: 16 }}>Create New Scenario</span>
          </div>
        }
        open={createModalOpen}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        footer={null}
        styles={{
          header: { background: '#141428', borderBottom: '1px solid #2d2d52' },
          body: { background: '#1a1a2e', padding: 24 },
          content: { background: '#141428' },
        }}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateScenario}
          initialValues={{
            total_duration_ms: 60000,
          }}
        >
          <Form.Item
            name="name"
            label={<Text style={{ color: '#a8a8c0' }}>Scenario Name</Text>}
            rules={[{ required: true, message: 'Please enter a scenario name' }]}
          >
            <Input placeholder="My OT Scenario" />
          </Form.Item>

          <Form.Item
            name="description"
            label={<Text style={{ color: '#a8a8c0' }}>Description</Text>}
          >
            <Input.TextArea rows={3} placeholder="Describe your scenario..." />
          </Form.Item>

          <Form.Item
            name="vertical"
            label={<Text style={{ color: '#a8a8c0' }}>Industry Vertical</Text>}
          >
            <Select placeholder="Select a vertical (optional)" allowClear>
              {Object.entries(verticalConfig).map(([key, config]) => (
                <Option key={key} value={key}>
                  <Space>
                    {config.icon}
                    {config.label}
                  </Space>
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="total_duration_ms"
            label={<Text style={{ color: '#a8a8c0' }}>Duration (ms)</Text>}
          >
            <Select>
              <Option value={10000}>10 seconds</Option>
              <Option value={30000}>30 seconds</Option>
              <Option value={60000}>1 minute</Option>
              <Option value={300000}>5 minutes</Option>
              <Option value={600000}>10 minutes</Option>
              <Option value={1800000}>30 minutes</Option>
              <Option value={3600000}>1 hour</Option>
            </Select>
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setCreateModalOpen(false)}>Cancel</Button>
              <Button type="primary" htmlType="submit" loading={createMutation.isPending}>
                Create Scenario
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Create from Template Modal */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 8,
                background: 'linear-gradient(135deg, #6CC04A20 0%, #6CC04A10 100%)',
                border: '1px solid #6CC04A40',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#6CC04A',
              }}
            >
              <RocketOutlined style={{ fontSize: 18 }} />
            </div>
            <span style={{ color: '#fff', fontSize: 16 }}>Create from Template</span>
          </div>
        }
        open={templateModalOpen}
        onCancel={() => {
          setTemplateModalOpen(false);
          setSelectedVertical(null);
          setSelectedTemplate(null);
          templateForm.resetFields();
        }}
        footer={null}
        width={800}
        styles={{
          header: { background: '#141428', borderBottom: '1px solid #2d2d52' },
          body: { background: '#1a1a2e', padding: 24 },
          content: { background: '#141428' },
        }}
      >
        {/* Step 1: Select Vertical */}
        <div style={{ marginBottom: 24 }}>
          <Text strong style={{ color: '#fff', display: 'block', marginBottom: 12 }}>
            1. Select Industry Vertical
          </Text>
          {verticalsLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin />
              <div style={{ marginTop: 12, color: '#6b6b8a' }}>Loading verticals...</div>
            </div>
          ) : !verticals || verticals.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#6b6b8a' }}>
              No verticals available. Please check the backend templates configuration.
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
                        background: isSelected ? `${config?.color || '#049FD9'}20` : '#141428',
                        border: `1px solid ${isSelected ? config?.color || '#049FD9' : '#2d2d52'}`,
                        cursor: 'pointer',
                      }}
                      bodyStyle={{ padding: 16, textAlign: 'center' }}
                    >
                      <div style={{ fontSize: 24, color: config?.color || '#049FD9', marginBottom: 8 }}>
                        {config?.icon || <FolderOutlined />}
                      </div>
                      <Text style={{ color: '#fff', display: 'block' }}>{config?.label || vertical.name}</Text>
                      <Text style={{ color: '#6b6b8a', fontSize: 11 }}>
                        {vertical.template_count} template{vertical.template_count !== 1 ? 's' : ''}
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
            <Text strong style={{ color: '#fff', display: 'block', marginBottom: 12 }}>
              2. Select Template
            </Text>
            {templatesLoading ? (
              <div style={{ textAlign: 'center', padding: 40 }}>
                <Spin />
                <div style={{ marginTop: 12, color: '#6b6b8a' }}>Loading templates...</div>
              </div>
            ) : !templates || templates.filter((t) => t.vertical === selectedVertical).length === 0 ? (
              <div style={{ textAlign: 'center', padding: 40, color: '#6b6b8a' }}>
                No templates available for this vertical.
              </div>
            ) : (
              <Row gutter={[12, 12]}>
                {templates
                  .filter((t) => t.vertical === selectedVertical)
                  .map((template) => {
                    const isSelected = selectedTemplate?.name === template.name;
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
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <div style={{ flex: 1 }}>
                              <Text strong style={{ color: '#fff', display: 'block', marginBottom: 4 }}>
                                {template.display_name}
                              </Text>
                              <Paragraph
                                ellipsis={{ rows: 2 }}
                                style={{ color: '#a8a8c0', fontSize: 12, marginBottom: 8 }}
                              >
                                {template.description}
                              </Paragraph>
                              <Space size={4}>
                                <Tag style={{ background: '#2d2d52', border: 'none', color: '#fff', fontSize: 10 }}>
                                  {template.device_count} devices
                                </Tag>
                                {template.protocols.slice(0, 2).map((p) => (
                                  <Tag
                                    key={p}
                                    style={{
                                      background: `${verticalInfo?.color || '#049FD9'}20`,
                                      border: 'none',
                                      color: verticalInfo?.color || '#049FD9',
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
            <Text strong style={{ color: '#fff', display: 'block', marginBottom: 12 }}>
              3. Name Your Scenario
            </Text>
            <Form form={templateForm} layout="vertical" onFinish={handleCreateFromTemplate}>
              <Form.Item
                name="scenario_name"
                label={<Text style={{ color: '#a8a8c0' }}>Scenario Name</Text>}
                rules={[{ required: true, message: 'Please enter a scenario name' }]}
                initialValue={`${selectedTemplate.display_name} - ${new Date().toLocaleDateString()}`}
              >
                <Input placeholder="My OT Scenario" />
              </Form.Item>

              <Form.Item
                name="description"
                label={<Text style={{ color: '#a8a8c0' }}>Description (optional)</Text>}
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

              <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
                <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                  <Button onClick={() => setTemplateModalOpen(false)}>Cancel</Button>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={createFromTemplateMutation.isPending}
                    style={{ background: '#6CC04A', borderColor: '#6CC04A' }}
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

      {/* Import Scenario Modal */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 8,
                background: 'linear-gradient(135deg, #722ed120 0%, #722ed110 100%)',
                border: '1px solid #722ed140',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#722ed1',
              }}
            >
              <ImportOutlined style={{ fontSize: 18 }} />
            </div>
            <span style={{ color: '#fff', fontSize: 16 }}>Import Scenario</span>
          </div>
        }
        open={importModalOpen}
        onCancel={() => {
          setImportModalOpen(false);
          setImportFileData(null);
        }}
        footer={
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setImportModalOpen(false)}>Cancel</Button>
            <Button
              type="primary"
              disabled={!importFileData}
              loading={importMutation.isPending}
              onClick={() => importFileData && importMutation.mutate(importFileData)}
              style={{ background: '#722ed1', borderColor: '#722ed1' }}
            >
              Import Scenario
            </Button>
          </Space>
        }
        styles={{
          header: { background: '#141428', borderBottom: '1px solid #2d2d52' },
          body: { background: '#1a1a2e', padding: 24 },
          content: { background: '#141428' },
        }}
      >
        <Dragger
          name="file"
          accept=".json"
          maxCount={1}
          showUploadList={false}
          beforeUpload={(file) => {
            const reader = new FileReader();
            reader.onload = (e) => {
              try {
                const content = e.target?.result as string;
                const data = JSON.parse(content);
                // Basic validation
                if (!data.name || !data.definition) {
                  message.error('Invalid scenario file: missing required fields (name, definition)');
                  return;
                }
                setImportFileData(data);
                message.success(`File loaded: ${data.name}`);
              } catch (err) {
                message.error('Invalid JSON file');
              }
            };
            reader.readAsText(file);
            return false; // Prevent auto upload
          }}
          style={{
            background: '#141428',
            border: '1px dashed #2d2d52',
            borderRadius: 8,
          }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined style={{ color: '#722ed1', fontSize: 48 }} />
          </p>
          <p className="ant-upload-text" style={{ color: '#fff' }}>
            Click or drag a JSON file to import
          </p>
          <p className="ant-upload-hint" style={{ color: '#6b6b8a' }}>
            Import a scenario previously exported from PacketArch
          </p>
        </Dragger>

        {importFileData && (
          <Card
            style={{
              marginTop: 16,
              background: '#141428',
              border: '1px solid #2d2d52',
            }}
            bodyStyle={{ padding: 16 }}
          >
            <Text strong style={{ color: '#fff', display: 'block', marginBottom: 8 }}>
              Ready to import:
            </Text>
            <Space direction="vertical" size={4}>
              <Text style={{ color: '#a8a8c0' }}>
                <strong>Name:</strong> {(importFileData as any).name}
              </Text>
              {(importFileData as any).vertical && (
                <Text style={{ color: '#a8a8c0' }}>
                  <strong>Vertical:</strong> {verticalConfig[(importFileData as any).vertical]?.label || (importFileData as any).vertical}
                </Text>
              )}
              {(importFileData as any).description && (
                <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
                  {(importFileData as any).description}
                </Text>
              )}
            </Space>
          </Card>
        )}
      </Modal>
    </div>
  );
};

export default ScenariosPage;
