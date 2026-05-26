/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Scenarios Page - List, create, and manage scenarios
 */

import React, { useState, useMemo } from 'react';
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
  Checkbox,
  Modal,
  App,
  Dropdown,
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
  FolderOutlined,
  RocketOutlined,
  RobotOutlined,
  FileAddOutlined,
  ThunderboltOutlined,
  CompassOutlined,
  FileMarkdownOutlined,
  FilePdfOutlined,
  CodeOutlined,
  DatabaseOutlined,
  DownOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useFeatures } from '../hooks/useFeatures';
import {
  scenariosApi,
  type ScenarioFilters,
  type ScenarioSummary,
  type ScenarioCreate,
} from '../api/scenarios';
import { dashboardApi, type DashboardDeployment } from '../api/dashboard';
import type { CreateFromTemplateRequest } from '../api/templates';
import { GenerateDescriptionModal } from '../components/ai';
import GeneratePcapModal from '../components/GeneratePcapModal';
import ScenarioCard from '../components/scenarios/ScenarioCard';
import { verticalConfig } from '../components/scenarios/scenarioConstants';
import CreateScenarioModal from '../components/scenarios/CreateScenarioModal';
import TemplateWizardModal from '../components/scenarios/TemplateWizardModal';
import ImportScenarioModal from '../components/scenarios/ImportScenarioModal';
import { downloadsApi } from '../api/downloads';
import QuickDemoModal from '../components/scenarios/QuickDemoModal';
import ContextualHelpIcon from '../components/help/ContextualHelpIcon';
import { EmptyState } from '../components/common';
import {
  useScenarioMutations,
  type ImportedScenarioData,
} from '../hooks/useScenarioMutations';

const { Title, Text } = Typography;
const { Option } = Select;

const ScenariosPage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const { aiEnabled } = useFeatures();
  const [filters, setFilters] = useState<ScenarioFilters>({
    page: 1,
    page_size: 12,
  });
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [generateDescModalOpen, setGenerateDescModalOpen] = useState(false);
  const [selectedScenarioForDesc, setSelectedScenarioForDesc] =
    useState<ScenarioSummary | null>(null);
  const [quickDemoOpen, setQuickDemoOpen] = useState(false);
  const [generatePcapModalOpen, setGeneratePcapModalOpen] = useState(false);
  const [selectedScenarioForPcap, setSelectedScenarioForPcap] =
    useState<ScenarioSummary | null>(null);

  // Fetch scenarios
  const { data, isLoading, error } = useQuery({
    queryKey: ['scenarios', filters],
    queryFn: () => scenariosApi.list(filters),
  });

  // Poll dashboard for live deployment status
  const { data: dashboardData } = useQuery({
    queryKey: ['dashboard-live-scenarios'],
    queryFn: () => dashboardApi.getLive(),
    refetchInterval: 5000,
    staleTime: 3000,
  });

  const deploymentMap = useMemo(() => {
    const map = new Map<string, DashboardDeployment>();
    dashboardData?.deployments?.forEach((d) => {
      if (d.state === 'running' || d.state === 'starting') {
        map.set(d.scenario_id, d);
      }
    });
    return map;
  }, [dashboardData]);

  // ── Mutations ────────────────────────────────────────────────────
  const {
    createMutation,
    duplicateMutation,
    deleteMutation,
    bulkDeleteMutation,
    createFromTemplateMutation,
    importMutation,
    updateMutation,
    forceDeleteModal,
    resetForceDeleteModal,
    confirmDelete,
    confirmBulkDelete,
  } = useScenarioMutations({
    scenarioItems: data?.items,
    onCreated: () => {
      setCreateModalOpen(false);
    },
    onTemplateCreated: () => {
      setTemplateModalOpen(false);
    },
    onImported: () => {
      setImportModalOpen(false);
    },
  });

  // ── Selection ────────────────────────────────────────────────────
  const handleToggleSelect = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
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
    confirmBulkDelete(selectedIds);
    if (!bulkDeleteMutation.isPending) {
      setSelectedIds(new Set());
    }
  };

  // ── Filtering / Pagination ───────────────────────────────────────
  const handleFilterChange = (
    key: keyof ScenarioFilters,
    value: string | undefined,
  ) => {
    setFilters((prev) => ({ ...prev, [key]: value || undefined, page: 1 }));
  };

  const handlePageChange = (page: number, pageSize: number) => {
    setFilters((prev) => ({ ...prev, page, page_size: pageSize }));
  };

  // ── Open scenario ────────────────────────────────────────────────
  const handleOpenScenario = (id: string) => {
    navigate(`/studio?scenario=${id}`);
  };

  // ── Export ───────────────────────────────────────────────────────
  const handleExportScenario = async (id: string, name: string) => {
    try {
      const exportData = await scenariosApi.export(id);
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: 'application/json',
      });
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

  // ── Card menu ────────────────────────────────────────────────────
  const getScenarioMenuItems = (): MenuProps['items'] => {
    const items: MenuProps['items'] = [
      { key: 'open', icon: <EditOutlined />, label: 'Open in Studio' },
      { key: 'generate-pcap', icon: <FileAddOutlined />, label: 'Generate PCAP' },
    ];
    if (aiEnabled) {
      items.push({ key: 'generate-description', icon: <RobotOutlined />, label: 'Generate Description' });
    }
    items.push(
      { key: 'duplicate', icon: <CopyOutlined />, label: 'Duplicate' },
      { key: 'export', icon: <ExportOutlined />, label: 'Export JSON' },
      { key: 'download-report', icon: <FilePdfOutlined />, label: 'Download Report (PDF)' },
      { type: 'divider' },
      { key: 'delete', icon: <DeleteOutlined />, label: 'Delete', danger: true },
    );
    return items;
  };

  const handleMenuClick = (
    scenario: ScenarioSummary,
    info: { key: string; domEvent: React.MouseEvent },
  ) => {
    info.domEvent.stopPropagation();
    info.domEvent.preventDefault();

    switch (info.key) {
      case 'open':
        handleOpenScenario(scenario.id);
        break;
      case 'generate-pcap':
        setSelectedScenarioForPcap(scenario);
        setGeneratePcapModalOpen(true);
        break;
      case 'generate-description':
        setSelectedScenarioForDesc(scenario);
        setGenerateDescModalOpen(true);
        break;
      case 'duplicate':
        duplicateMutation.mutate(scenario.id);
        break;
      case 'export':
        handleExportScenario(scenario.id, scenario.name);
        break;
      case 'download-report':
        void (async () => {
          try {
            await scenariosApi.downloadReport(scenario.id, scenario.name);
            message.success('Scenario report downloaded');
          } catch {
            message.error('Failed to generate scenario report');
          }
        })();
        break;
      case 'delete':
        confirmDelete(scenario);
        break;
    }
  };

  // ── Description save ─────────────────────────────────────────────
  const handleSaveDescription = async (description: string) => {
    if (!selectedScenarioForDesc) return;
    await updateMutation.mutateAsync({
      id: selectedScenarioForDesc.id,
      data: { description },
    });
  };

  // ── Create handlers ──────────────────────────────────────────────
  const handleCreateScenario = (values: ScenarioCreate) => {
    createMutation.mutate(values);
  };

  const handleCreateFromTemplate = (data: CreateFromTemplateRequest) => {
    createFromTemplateMutation.mutate(data);
  };

  const handleImportScenario = (fileData: ImportedScenarioData) => {
    importMutation.mutate(fileData);
  };

  return (
    <div>
      {/* Page Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 24,
        }}
      >
        <div>
          <Title level={3} style={{ color: '#fff', margin: 0 }}>
            Scenarios
            <ContextualHelpIcon articleId="scenarios" tooltip="Scenario management help" />
          </Title>
          <Text style={{ color: '#6b6b8a' }}>
            Create and manage your OT traffic simulation scenarios
          </Text>
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
          <Button
            icon={<ThunderboltOutlined />}
            style={{ borderColor: '#FBAB18', color: '#FBAB18' }}
            onClick={() => setQuickDemoOpen(true)}
          >
            Quick Demo
          </Button>
          <Button
            icon={<CompassOutlined />}
            style={{ borderColor: '#049FD9', color: '#049FD9' }}
            onClick={() => navigate('/scenarios/guided-builder')}
          >
            Guided Builder
          </Button>
          <Button
            icon={<ImportOutlined />}
            style={{ borderColor: '#2d2d52' }}
            onClick={() => setImportModalOpen(true)}
          >
            Import
          </Button>
          <Dropdown
            menu={{
              items: [
                {
                  key: 'header',
                  type: 'group',
                  label: 'Portable Scenario Authoring Kit',
                },
                {
                  key: 'prompt',
                  icon: <RobotOutlined />,
                  label: 'LLM prompt — start here (LLM_PROMPT.md)',
                  onClick: () => downloadsApi.downloadFile('LLM_PROMPT.md'),
                },
                {
                  key: 'spec',
                  icon: <FileMarkdownOutlined />,
                  label: 'Authoring guide (SCENARIO_SPEC.md)',
                  onClick: () => downloadsApi.downloadFile('SCENARIO_SPEC.md'),
                },
                {
                  key: 'schema',
                  icon: <CodeOutlined />,
                  label: 'JSON Schema (packetarch-scenario.v1.json)',
                  onClick: () =>
                    downloadsApi.downloadFile('packetarch-scenario.v1.json'),
                },
                {
                  key: 'registry',
                  icon: <DatabaseOutlined />,
                  label: 'Fingerprint registry snapshot',
                  onClick: () =>
                    downloadsApi.downloadFile('fingerprint-registry.v1.json'),
                },
                { type: 'divider' },
                {
                  key: 'all',
                  label: 'See all downloads in Settings →',
                  onClick: () => navigate('/admin/settings?tab=downloads'),
                  extra: <span style={{ fontSize: 11, color: '#888' }}>Downloads tab</span>,
                },
              ],
            }}
            placement="bottomRight"
            trigger={['click']}
          >
            <Button
              icon={<ExportOutlined />}
              style={{ borderColor: '#2d2d52' }}
              title="Download the LLM prompt, schema, spec, and registry so external authors or AI tools can produce importable scenario files."
            >
              Format spec <DownOutlined style={{ fontSize: 10 }} />
            </Button>
          </Dropdown>
          <Button
            icon={<RocketOutlined />}
            style={{ borderColor: '#6CC04A', color: '#6CC04A' }}
            onClick={() => setTemplateModalOpen(true)}
          >
            From Template
          </Button>
          {aiEnabled && (
            <Button
              icon={<RobotOutlined />}
              style={{ borderColor: '#5a9fd4', color: '#5a9fd4' }}
              onClick={() => navigate('/scenarios/ai-create')}
            >
              AI Create
            </Button>
          )}
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalOpen(true)}
          >
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
              onChange={(e) =>
                handleFilterChange('search', e.target.value)
              }
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
          <div style={{ marginTop: 16, color: '#6b6b8a' }}>
            Loading scenarios...
          </div>
        </div>
      ) : error ? (
        <Card
          style={{ background: '#141428', border: '1px solid #2d2d52' }}
        >
          <Empty
            description={
              <Text style={{ color: '#6b6b8a' }}>
                Failed to load scenarios
              </Text>
            }
          />
        </Card>
      ) : data?.items.length === 0 ? (
        <Card
          style={{
            background: '#141428',
            border: '1px solid #2d2d52',
            padding: 40,
          }}
        >
          <EmptyState
            icon={<FolderOutlined />}
            message="No scenarios yet"
            hint="Pick the workflow that matches how you want to start."
            marginTop={0}
            actions={[
              {
                label: 'From Template',
                icon: <CompassOutlined />,
                primary: true,
                onClick: () => navigate('/scenarios/guided-builder'),
              },
              {
                label: 'Generate with AI',
                icon: <RobotOutlined />,
                onClick: () => navigate('/scenarios/ai-create'),
              },
              {
                label: 'Blank Scenario',
                icon: <PlusOutlined />,
                onClick: () => setCreateModalOpen(true),
              },
            ]}
            helpArticleId="scenarios"
          />
        </Card>
      ) : (
        <>
          {/* Stats & Select All */}
          <div
            style={{
              marginBottom: 16,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ color: '#6b6b8a', fontSize: 13 }}>
              Showing {data?.items.length} of {data?.total} scenarios
            </div>
            <Checkbox
              checked={
                !!data?.items &&
                selectedIds.size === data.items.length &&
                data.items.length > 0
              }
              indeterminate={
                selectedIds.size > 0 &&
                selectedIds.size < (data?.items?.length || 0)
              }
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
                <ScenarioCard
                  scenario={scenario}
                  isSelected={selectedIds.has(scenario.id)}
                  menuItems={getScenarioMenuItems()}
                  onOpen={handleOpenScenario}
                  onToggleSelect={handleToggleSelect}
                  onMenuClick={handleMenuClick}
                  deployment={deploymentMap.get(scenario.id)}
                />
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

      {/* ── Modals ─────────────────────────────────────────────── */}
      <QuickDemoModal
        open={quickDemoOpen}
        onCancel={() => setQuickDemoOpen(false)}
      />

      <CreateScenarioModal
        open={createModalOpen}
        loading={createMutation.isPending}
        onCancel={() => setCreateModalOpen(false)}
        onSubmit={handleCreateScenario}
      />

      <TemplateWizardModal
        open={templateModalOpen}
        loading={createFromTemplateMutation.isPending}
        onCancel={() => setTemplateModalOpen(false)}
        onSubmit={handleCreateFromTemplate}
      />

      <ImportScenarioModal
        open={importModalOpen}
        loading={importMutation.isPending}
        onCancel={() => setImportModalOpen(false)}
        onImport={handleImportScenario}
      />

      {/* Generate Description Modal */}
      {selectedScenarioForDesc && (
        <GenerateDescriptionModal
          open={generateDescModalOpen}
          onClose={() => {
            setGenerateDescModalOpen(false);
            setSelectedScenarioForDesc(null);
          }}
          onSave={handleSaveDescription}
          scenarioId={selectedScenarioForDesc.id}
          scenarioName={selectedScenarioForDesc.name}
          currentDescription={
            selectedScenarioForDesc.description || undefined
          }
        />
      )}

      {/* Generate PCAP Modal */}
      {selectedScenarioForPcap && (
        <GeneratePcapModal
          open={generatePcapModalOpen}
          onClose={() => {
            setGeneratePcapModalOpen(false);
            setSelectedScenarioForPcap(null);
          }}
          scenarioId={selectedScenarioForPcap.id}
          scenarioName={selectedScenarioForPcap.name}
          defaultDurationMs={selectedScenarioForPcap.total_duration_ms}
        />
      )}

      {/* Force Delete Confirmation Modal */}
      <Modal
        title="Cannot Delete Scenario"
        open={forceDeleteModal.visible}
        onCancel={resetForceDeleteModal}
        footer={[
          <Button key="cancel" onClick={resetForceDeleteModal}>
            Cancel
          </Button>,
          <Button
            key="force"
            danger
            type="primary"
            loading={deleteMutation.isPending}
            onClick={() => {
              if (forceDeleteModal.scenarioId) {
                deleteMutation.mutate({
                  id: forceDeleteModal.scenarioId,
                  force: true,
                });
              }
            }}
          >
            Force Delete
          </Button>,
        ]}
        styles={{
          header: {
            background: '#141428',
            borderBottom: '1px solid #2d2d52',
          },
          body: { background: '#1a1a2e', padding: 24 },
          content: { background: '#141428' },
        }}
      >
        <Space
          direction="vertical"
          size="middle"
          style={{ width: '100%' }}
        >
          <Text style={{ color: '#e6e6f0' }}>
            The scenario &quot;{forceDeleteModal.scenarioName}&quot; has
            active dependencies:
          </Text>
          <div
            style={{
              background: '#141428',
              padding: 16,
              borderRadius: 8,
            }}
          >
            {forceDeleteModal.activeAgentDeployments > 0 && (
              <div style={{ marginBottom: 8 }}>
                <Tag color="blue">
                  {forceDeleteModal.activeAgentDeployments}
                </Tag>
                <Text style={{ color: '#a8a8c0' }}>
                  active agent deployment(s)
                </Text>
              </div>
            )}
            {forceDeleteModal.activeDockerDeployments > 0 && (
              <div>
                <Tag color="purple">
                  {forceDeleteModal.activeDockerDeployments}
                </Tag>
                <Text style={{ color: '#a8a8c0' }}>
                  active Docker deployment(s)
                </Text>
              </div>
            )}
          </div>
          <Text type="warning" style={{ fontSize: 12 }}>
            Force delete will stop all active deployments and remove all
            related records.
          </Text>
        </Space>
      </Modal>
    </div>
  );
};

export default ScenariosPage;
