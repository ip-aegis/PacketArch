/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Cyber Vision integration page
 */

import React, { useEffect, useState } from 'react';
import {
  Typography,
  Card,
  Row,
  Col,
  Table,
  Select,
  Button,
  Space,
  Alert,
  Spin,
  Tag,
  Tabs,
  Statistic,
  Progress,
  Empty,
  Tooltip,
  Badge,
  Modal,
  Checkbox,
  message,
} from 'antd';
import {
  ApartmentOutlined,
  BulbOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  SettingOutlined,
  CompressOutlined,
  SafetyOutlined,
  EyeOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ExclamationCircleOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import { useCyberVisionStore } from '../stores/cyberVisionStore';
import { scenariosApi } from '../api/scenarios';
import { extractErrorMessage } from '../utils/errorUtils';
import ContextualHelpIcon from '../components/help/ContextualHelpIcon';
import type {
  CVDevice,
  CVVulnerability,
  MatchedDevice,
  CVDevicePropertyMapping,
  DuplicateMacGroup,
  DuplicateMacDeviceInfo,
} from '../api/cyberVision';

const { Title, Text } = Typography;

// Scenario option type
interface ScenarioOption {
  value: string;
  label: string;
}

const CyberVisionPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    connectionStatus,
    devices,
    vulnerabilities,
    presets,
    comparisonResult,
    isLoading,
    isLoadingDevices,
    isLoadingVulnerabilities,
    isLoadingPresets,
    isComparing,
    isEnriching,
    enrichedSinceCompare,
    error,
    fetchStatus,
    fetchDevices,
    fetchVulnerabilities,
    fetchPresets,
    compareScenario,
    enrichDevices,
    clearError,
    clearComparison,
    macAnalysis,
    isLoadingMacAnalysis,
    analyzeDuplicateMacs,
    clearMacAnalysis,
  } = useCyberVisionStore();

  const [scenarios, setScenarios] = useState<ScenarioOption[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [loadingScenarios, setLoadingScenarios] = useState(false);
  const [activeTab, setActiveTab] = useState('comparison');
  const [macPresetFilter, setMacPresetFilter] = useState<string | null>(null);

  // Enrichment modal state
  const [enrichModalOpen, setEnrichModalOpen] = useState(false);
  const [enrichTarget, setEnrichTarget] = useState<MatchedDevice | null>(null);
  const [selectedProperties, setSelectedProperties] = useState<string[]>([]);
  const [enrichingDeviceId, setEnrichingDeviceId] = useState<string | null>(null);

  // Bulk enrichment state
  const [bulkEnrichModalOpen, setBulkEnrichModalOpen] = useState(false);
  const [bulkEnrichProgress, setBulkEnrichProgress] = useState(0);
  const [bulkEnrichTotal, setBulkEnrichTotal] = useState(0);
  const [bulkEnrichResults, setBulkEnrichResults] = useState<{
    success: number;
    failed: number;
    skipped: number;
    totalProps: number;
    errors: string[];
  } | null>(null);
  const [isBulkEnriching, setIsBulkEnriching] = useState(false);
  const [bulkEnrichPreview, setBulkEnrichPreview] = useState<{
    devicesWithData: number;
    devicesWithoutData: number;
    sampleProperties: { device: string; props: string[] }[];
  } | null>(null);

  // Fetch initial data
  useEffect(() => {
    fetchStatus();
    loadScenarios();
    fetchPresets();
  }, []);

  // Load scenarios for dropdown
  const loadScenarios = async () => {
    setLoadingScenarios(true);
    try {
      const response = await scenariosApi.list({ page: 1, page_size: 100 });
      setScenarios(
        response.items.map((s) => ({
          value: s.id,
          label: s.name,
        }))
      );
    } catch (err) {
      console.error('Failed to load scenarios:', err);
    } finally {
      setLoadingScenarios(false);
    }
  };

  // Handle comparison
  const handleCompare = async () => {
    if (!selectedScenario) return;
    await compareScenario(selectedScenario, selectedPreset || undefined);
  };

  // Get available properties from a matched device for enrichment
  const getAvailableProperties = (match: MatchedDevice): { label: string; value: string }[] => {
    const props: { label: string; value: string }[] = [];
    const sd = match.scenario_device as Record<string, unknown>;

    // Debug: log what we're working with
    console.log('getAvailableProperties for device:', {
      name: sd['name'],
      vendor: sd['vendor'],
      fingerprintModel: sd['fingerprintModel'],
      type: sd['type'],
      role: sd['role'],
      protocols: sd['protocols'],
    });

    // Vendor
    const vendor = sd['vendor'];
    if (vendor && typeof vendor === 'string' && vendor.trim()) {
      props.push({ label: 'Vendor', value: vendor });
    }

    // Model (fingerprintModel or model)
    const model = sd['fingerprintModel'] || sd['model'];
    if (model && typeof model === 'string' && model.trim()) {
      props.push({ label: 'Model', value: model });
    }

    // Device Type
    const deviceType = sd['type'];
    if (deviceType && typeof deviceType === 'string' && deviceType.trim()) {
      props.push({ label: 'Device Type', value: deviceType });
    }

    // Role
    const role = sd['role'];
    if (role && typeof role === 'string' && role.trim()) {
      props.push({ label: 'Role', value: role });
    }

    // Protocols
    const protocols = sd['protocols'];
    if (protocols && Array.isArray(protocols) && protocols.length > 0) {
      props.push({ label: 'Protocols', value: protocols.join(', ') });
    }

    // Hostname from network config
    const network = sd['network'] as Record<string, unknown> | undefined;
    if (network?.['hostname'] && typeof network['hostname'] === 'string') {
      props.push({ label: 'Hostname', value: network['hostname'] });
    }

    console.log('Found properties:', props);
    return props;
  };

  // Open enrich modal for a matched device
  const openEnrichModal = (match: MatchedDevice) => {
    setEnrichTarget(match);
    const props = getAvailableProperties(match);
    // Pre-select all properties by default
    setSelectedProperties(props.map((p) => p.label));
    setEnrichModalOpen(true);
  };

  // Handle enrichment submission
  const handleEnrich = async () => {
    if (!enrichTarget) return;

    const props = getAvailableProperties(enrichTarget);
    const propsToSend: Record<string, string> = {};
    for (const prop of props) {
      if (selectedProperties.includes(prop.label)) {
        propsToSend[prop.label] = prop.value;
      }
    }

    if (Object.keys(propsToSend).length === 0) {
      message.warning('Please select at least one property to push');
      return;
    }

    // Get scenario device info for matching and labeling
    const scenarioDeviceName = enrichTarget.scenario_device.name as string | undefined;
    const scenarioNetwork = enrichTarget.scenario_device.network as Record<string, unknown> | undefined;
    const scenarioMac = scenarioNetwork?.macAddress as string | undefined;
    const scenarioIp = scenarioNetwork?.ipAddress as string | undefined;

    const mapping: CVDevicePropertyMapping = {
      cv_device_id: enrichTarget.cv_device.id,
      // Use SCENARIO device MAC/IP for resolution (these match real CV devices)
      cv_device_mac: scenarioMac || enrichTarget.cv_device.mac || undefined,
      cv_device_ip: scenarioIp || enrichTarget.cv_device.ip || undefined,
      device_label: scenarioDeviceName || undefined,
      properties: propsToSend,
    };

    // Set loading state for the specific device
    setEnrichingDeviceId(enrichTarget.cv_device.id);

    const result = await enrichDevices({
      device_mappings: [mapping],
      skip_existing: true,
    });

    setEnrichingDeviceId(null);

    if (result && result.success_count > 0) {
      message.success(
        `Successfully pushed ${result.total_properties_added} properties to Cyber Vision`
      );
      setEnrichModalOpen(false);
      setEnrichTarget(null);
    } else if (result && result.failed_count > 0) {
      message.error('Failed to enrich device. Check the error above.');
    }
  };

  // Open bulk enrich modal with preview
  const openBulkEnrichModal = () => {
    if (!comparisonResult || comparisonResult.matched_devices.length === 0) return;

    // Analyze what data is available
    const devicesWithData: MatchedDevice[] = [];
    const devicesWithoutData: MatchedDevice[] = [];
    const sampleProperties: { device: string; props: string[] }[] = [];

    for (const match of comparisonResult.matched_devices) {
      const props = getAvailableProperties(match);
      if (props.length > 0) {
        devicesWithData.push(match);
        // Show first 3 devices as samples
        if (sampleProperties.length < 3) {
          sampleProperties.push({
            device: match.cv_device.name,
            props: props.map(p => `${p.label}: ${p.value}`),
          });
        }
      } else {
        devicesWithoutData.push(match);
      }
    }

    // Debug: log what we found
    console.log('Bulk enrich analysis:', {
      devicesWithData: devicesWithData.length,
      devicesWithoutData: devicesWithoutData.length,
      sampleProperties,
    });

    // Also log a sample device to see its structure
    if (comparisonResult.matched_devices.length > 0) {
      console.log('Sample scenario_device structure:', comparisonResult.matched_devices[0].scenario_device);
    }

    setBulkEnrichPreview({
      devicesWithData: devicesWithData.length,
      devicesWithoutData: devicesWithoutData.length,
      sampleProperties,
    });
    setBulkEnrichResults(null);
    setBulkEnrichModalOpen(true);
  };

  // Handle bulk enrichment of all matched devices
  const handleBulkEnrich = async () => {
    if (!comparisonResult || comparisonResult.matched_devices.length === 0) return;

    // Filter to devices that have properties to enrich
    const devicesToEnrich = comparisonResult.matched_devices.filter(
      (m) => getAvailableProperties(m).length > 0
    );

    if (devicesToEnrich.length === 0) {
      message.warning('No devices have properties available to enrich');
      return;
    }

    setIsBulkEnriching(true);
    setBulkEnrichProgress(0);
    setBulkEnrichTotal(devicesToEnrich.length);
    setBulkEnrichPreview(null);

    let success = 0;
    let failed = 0;
    let skipped = 0;
    let totalProps = 0;
    const errors: string[] = [];

    for (let i = 0; i < devicesToEnrich.length; i++) {
      const match = devicesToEnrich[i];
      const props = getAvailableProperties(match);

      if (props.length === 0) {
        skipped++;
        setBulkEnrichProgress(i + 1);
        continue;
      }

      const propsToSend: Record<string, string> = {};
      for (const prop of props) {
        propsToSend[prop.label] = prop.value;
      }

      // Get scenario device info for matching and labeling
      const scenarioDeviceName = match.scenario_device.name as string | undefined;
      const scenarioNetwork = match.scenario_device.network as Record<string, unknown> | undefined;
      const scenarioMac = scenarioNetwork?.macAddress as string | undefined;
      const scenarioIp = scenarioNetwork?.ipAddress as string | undefined;

      // Debug log
      console.log(`Enriching ${match.cv_device.name}:`, propsToSend, `label: ${scenarioDeviceName}`, `scenarioMAC: ${scenarioMac}`);

      try {
        const result = await enrichDevices({
          device_mappings: [{
            cv_device_id: match.cv_device.id,
            // Use SCENARIO device MAC/IP for resolution (these match real CV devices)
            cv_device_mac: scenarioMac || match.cv_device.mac || undefined,
            cv_device_ip: scenarioIp || match.cv_device.ip || undefined,
            device_label: scenarioDeviceName || undefined,
            properties: propsToSend,
          }],
          skip_existing: true,
        });

        console.log(`Result for ${match.cv_device.name}:`, result);

        if (result && result.success_count > 0) {
          success++;
          totalProps += result.total_properties_added;
        } else if (result && result.failed_count > 0) {
          failed++;
          const deviceError = result.results[0]?.error;
          if (deviceError) {
            errors.push(`${match.cv_device.name}: ${deviceError}`);
          }
        }
      } catch (err) {
        failed++;
        errors.push(`${match.cv_device.name}: ${extractErrorMessage(err, 'Unknown error')}`);
      }

      setBulkEnrichProgress(i + 1);
    }

    setIsBulkEnriching(false);
    setBulkEnrichResults({ success, failed, skipped, totalProps, errors });
  };

  // Load devices when tab changes
  useEffect(() => {
    if (activeTab === 'devices' && devices.length === 0 && connectionStatus?.connected) {
      fetchDevices();
    } else if (activeTab === 'vulnerabilities' && vulnerabilities.length === 0 && connectionStatus?.connected) {
      fetchVulnerabilities();
    }
  }, [activeTab, connectionStatus?.connected]);

  // Device columns
  const deviceColumns: ColumnsType<CVDevice> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: 'IP Address',
      dataIndex: 'ip',
      key: 'ip',
      render: (ip: string | null) => ip || <Text type="secondary">-</Text>,
    },
    {
      title: 'Vendor',
      dataIndex: 'vendor',
      key: 'vendor',
      render: (vendor: string | null) => vendor || <Text type="secondary">Unknown</Text>,
    },
    {
      title: 'Model',
      dataIndex: 'model',
      key: 'model',
      render: (model: string | null) => model || <Text type="secondary">-</Text>,
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (category: string | null) => (
        category ? <Tag>{category}</Tag> : <Text type="secondary">-</Text>
      ),
    },
    {
      title: 'Risk Score',
      dataIndex: 'risk_score',
      key: 'risk_score',
      render: (score: number | null) => (
        score !== null ? (
          <Tag color={score > 70 ? 'red' : score > 40 ? 'orange' : 'green'}>
            {score}
          </Tag>
        ) : <Text type="secondary">-</Text>
      ),
    },
  ];

  // Vulnerability columns
  const vulnerabilityColumns: ColumnsType<CVVulnerability> = [
    {
      title: 'CVE ID',
      dataIndex: 'cve_id',
      key: 'cve_id',
      render: (cve: string) => <Text strong>{cve}</Text>,
    },
    {
      title: 'Title',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => {
        const color = severity === 'critical' ? 'red' :
          severity === 'high' ? 'orange' :
          severity === 'medium' ? 'gold' : 'green';
        return <Tag color={color}>{severity.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'CVSS Score',
      dataIndex: 'cvss_score',
      key: 'cvss_score',
      render: (score: number | null) => (
        score !== null ? (
          <Tag color={score >= 9 ? 'red' : score >= 7 ? 'orange' : score >= 4 ? 'gold' : 'green'}>
            {score.toFixed(1)}
          </Tag>
        ) : <Text type="secondary">-</Text>
      ),
    },
    {
      title: 'Affected Devices',
      dataIndex: 'affected_device_count',
      key: 'affected_device_count',
    },
  ];

  // Matched device columns
  const matchedColumns: ColumnsType<MatchedDevice> = [
    {
      title: 'Scenario Device',
      key: 'scenario',
      render: (_, record) => {
        const network = record.scenario_device.network as Record<string, unknown> | undefined;
        return (
          <Space direction="vertical" size={0}>
            <Text strong>{record.scenario_device.name as string || 'Unnamed'}</Text>
            <Text type="secondary">IP: {network?.ipAddress as string || '-'}</Text>
            <Text type="secondary" style={{ fontSize: 11 }}>MAC: {network?.macAddress as string || '-'}</Text>
          </Space>
        );
      },
    },
    {
      title: 'CV Device (Real Network)',
      key: 'cv',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.cv_device.name}</Text>
          <Text type="secondary">IP: {record.cv_device.ip || '-'}</Text>
          <Text type="secondary" style={{ fontSize: 11 }}>MAC: {record.cv_device.mac || '-'}</Text>
          {record.cv_device.vendor && (
            <Text type="secondary" style={{ fontSize: 11 }}>Vendor: {record.cv_device.vendor}</Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Match Type',
      dataIndex: 'match_type',
      key: 'match_type',
      render: (type: string) => (
        <Tooltip title={
          type === 'mac' ? 'Matched by MAC address (exact)' :
          type === 'ip' ? 'Matched by IP address (exact)' :
          type === 'vendor_model' ? 'Matched by vendor and model' :
          'Matched by vendor only'
        }>
          <Tag color={type === 'mac' ? 'blue' : type === 'ip' ? 'green' : 'orange'}>
            {type.toUpperCase()}
          </Tag>
        </Tooltip>
      ),
    },
    {
      title: 'Confidence',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 120,
      render: (confidence: number) => (
        <Progress
          percent={Math.round(confidence * 100)}
          size="small"
          status={confidence >= 0.8 ? 'success' : confidence >= 0.5 ? 'normal' : 'exception'}
        />
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_, record) => {
        const props = getAvailableProperties(record);
        const isLoading = enrichingDeviceId === record.cv_device.id;
        return props.length > 0 ? (
          <Tooltip title="Push PacketArch data to Cyber Vision">
            <Button
              type="link"
              size="small"
              icon={<CloudUploadOutlined spin={isLoading} />}
              onClick={() => openEnrichModal(record)}
              loading={isLoading}
              disabled={isLoading}
            >
              {isLoading ? 'Pushing...' : 'Enrich'}
            </Button>
          </Tooltip>
        ) : (
          <Text type="secondary">No data</Text>
        );
      },
    },
  ];

  // Not connected state
  if (connectionStatus && !connectionStatus.connected) {
    return (
      <div style={{ padding: 24 }}>
        <Title level={2}>
          <EyeOutlined /> Cyber Vision
          <ContextualHelpIcon articleId="cyber-vision" tooltip="Cyber Vision integration help" />
        </Title>
        <Alert
          message="Not Connected"
          description={
            <Space direction="vertical">
              <Text>{connectionStatus.message || 'Cyber Vision is not configured or connection failed.'}</Text>
              <Button
                type="primary"
                icon={<SettingOutlined />}
                onClick={() => navigate('/settings')}
              >
                Configure Cyber Vision
              </Button>
            </Space>
          }
          type="warning"
          showIcon
        />
      </div>
    );
  }

  const tabItems = [
    {
      key: 'comparison',
      label: (
        <span>
          <CompressOutlined /> Scenario Comparison
        </span>
      ),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* Scenario selector */}
          <Card title="Compare Scenario to Cyber Vision" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary">
                Select a scenario to compare its devices against the devices discovered by Cyber Vision.
                Optionally filter CV devices by preset.
              </Text>
              <Row gutter={[8, 8]}>
                <Col flex="1">
                  <Select
                    placeholder="Select a scenario..."
                    style={{ width: '100%' }}
                    loading={loadingScenarios}
                    options={scenarios}
                    value={selectedScenario}
                    onChange={(value) => {
                      setSelectedScenario(value);
                      clearComparison();
                    }}
                    showSearch
                    filterOption={(input, option) =>
                      (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                  />
                </Col>
                <Col flex="200px">
                  <Select
                    placeholder="CV Preset (optional)"
                    style={{ width: '100%' }}
                    loading={isLoadingPresets}
                    options={presets.map((p) => ({ value: p.id, label: p.label }))}
                    value={selectedPreset}
                    onChange={(value) => {
                      setSelectedPreset(value);
                      clearComparison();
                    }}
                    allowClear
                    showSearch
                    filterOption={(input, option) =>
                      (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                  />
                </Col>
                <Col>
                  <Button
                    type="primary"
                    onClick={handleCompare}
                    loading={isComparing}
                    disabled={!selectedScenario}
                  >
                    Compare
                  </Button>
                </Col>
              </Row>
            </Space>
          </Card>

          {/* Comparison results */}
          {comparisonResult && (
            <>
              {/* Stats */}
              <Row gutter={16}>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="Scenario Devices"
                      value={comparisonResult.scenario_device_count}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="CV Devices"
                      value={comparisonResult.cv_device_count}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="Matched"
                      value={comparisonResult.matched_devices.length}
                      valueStyle={{ color: '#52c41a' }}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="Match Rate"
                      value={Math.round(comparisonResult.match_rate * 100)}
                      suffix="%"
                      valueStyle={{
                        color: comparisonResult.match_rate >= 0.7 ? '#52c41a' :
                               comparisonResult.match_rate >= 0.4 ? '#faad14' : '#f5222d'
                      }}
                    />
                  </Card>
                </Col>
              </Row>

              {/* Re-compare prompt after enrichment */}
              {enrichedSinceCompare && (
                <Alert
                  message="Enrichment complete — re-compare to verify changes took effect in Cyber Vision."
                  type="info"
                  showIcon
                  icon={<SyncOutlined />}
                  action={
                    <Button size="small" type="primary" onClick={handleCompare} loading={isComparing}>
                      Re-compare
                    </Button>
                  }
                />
              )}

              {/* Comparison insights */}
              {comparisonResult.insights.length > 0 && (
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  {comparisonResult.insights.map((insight, idx) => (
                    <Alert
                      key={idx}
                      message={insight.message}
                      type={insight.severity === 'warning' ? 'warning' : insight.severity === 'suggestion' ? 'info' : 'info'}
                      showIcon
                      icon={
                        insight.severity === 'suggestion' ? <BulbOutlined /> :
                        insight.severity === 'warning' ? <WarningOutlined /> :
                        <InfoCircleOutlined />
                      }
                      banner
                    />
                  ))}
                </Space>
              )}

              {/* Matched devices */}
              <Card
                title={
                  <Space>
                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                    Matched Devices ({comparisonResult.matched_devices.length})
                  </Space>
                }
                size="small"
                extra={
                  comparisonResult.matched_devices.length > 0 && (
                    <Button
                      type="primary"
                      icon={<CloudUploadOutlined />}
                      onClick={openBulkEnrichModal}
                      disabled={isBulkEnriching}
                    >
                      Enrich All
                    </Button>
                  )
                }
              >
                {comparisonResult.matched_devices.length > 0 ? (
                  <Table
                    columns={matchedColumns}
                    dataSource={comparisonResult.matched_devices}
                    rowKey={(record) => record.cv_device.id}
                    pagination={false}
                    size="small"
                  />
                ) : (
                  <Empty description="No matching devices found" />
                )}
              </Card>

              {/* Scenario devices not found in CV */}
              {comparisonResult.scenario_only.length > 0 && (
                <Card
                  title={
                    <Space>
                      <ExclamationCircleOutlined style={{ color: '#faad14' }} />
                      Not Found in CV ({comparisonResult.scenario_only.length})
                    </Space>
                  }
                  size="small"
                >
                  <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                    These scenario devices were not found in Cyber Vision (no matching MAC, IP, or vendor/model).
                  </Text>
                  <Table
                    columns={[
                      { title: 'Name', dataIndex: 'name', key: 'name' },
                      {
                        title: 'IP',
                        key: 'ip',
                        render: (_, record: Record<string, unknown>) => {
                          const network = record.network as Record<string, unknown> | undefined;
                          return network?.ipAddress as string || '-';
                        }
                      },
                      {
                        title: 'MAC',
                        key: 'mac',
                        render: (_, record: Record<string, unknown>) => {
                          const network = record.network as Record<string, unknown> | undefined;
                          return network?.macAddress as string || '-';
                        }
                      },
                      { title: 'Vendor', dataIndex: 'vendor', key: 'vendor' },
                      { title: 'Model', dataIndex: 'fingerprintModel', key: 'model' },
                    ]}
                    dataSource={comparisonResult.scenario_only.map((d, i) => ({ ...d, key: i }))}
                    pagination={false}
                    size="small"
                  />
                </Card>
              )}

              {/* CV-only devices */}
              {comparisonResult.cv_only.length > 0 && (
                <Card
                  title={
                    <Space>
                      <EyeOutlined style={{ color: '#1890ff' }} />
                      Only in Cyber Vision ({comparisonResult.cv_only.length})
                    </Space>
                  }
                  size="small"
                >
                  <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                    These devices were discovered by Cyber Vision but are not represented in your scenario.
                  </Text>
                  <Table
                    columns={[
                      {
                        title: 'Name',
                        dataIndex: 'name',
                        key: 'name',
                        render: (name: string) => <Text strong>{name}</Text>,
                      },
                      {
                        title: 'IP',
                        dataIndex: 'ip',
                        key: 'ip',
                        render: (ip: string | null) => ip || <Text type="secondary">-</Text>,
                      },
                      {
                        title: 'MAC',
                        dataIndex: 'mac',
                        key: 'mac',
                        render: (mac: string | null) => mac ? <Text style={{ fontSize: 11 }}>{mac}</Text> : <Text type="secondary">-</Text>,
                      },
                      {
                        title: 'Vendor',
                        dataIndex: 'vendor',
                        key: 'vendor',
                        render: (vendor: string | null) => vendor || <Text type="secondary">Unknown</Text>,
                      },
                      {
                        title: 'Category',
                        dataIndex: 'category',
                        key: 'category',
                        render: (category: string | null) => (
                          category ? <Tag>{category}</Tag> : <Text type="secondary">-</Text>
                        ),
                      },
                      {
                        title: 'Risk Score',
                        dataIndex: 'risk_score',
                        key: 'risk_score',
                        render: (score: number | null) => (
                          score !== null ? (
                            <Tag color={score > 70 ? 'red' : score > 40 ? 'orange' : 'green'}>
                              {score}
                            </Tag>
                          ) : <Text type="secondary">-</Text>
                        ),
                      },
                    ]}
                    dataSource={comparisonResult.cv_only}
                    rowKey="id"
                    pagination={{ pageSize: 10 }}
                    size="small"
                  />
                </Card>
              )}
            </>
          )}
        </Space>
      ),
    },
    {
      key: 'devices',
      label: (
        <span>
          <Badge count={devices.length} offset={[10, 0]} showZero={false}>
            <EyeOutlined /> Discovered Devices
          </Badge>
        </span>
      ),
      children: (
        <Card
          title="Devices Discovered by Cyber Vision"
          size="small"
          extra={
            <Button
              icon={<SyncOutlined />}
              onClick={() => fetchDevices()}
              loading={isLoadingDevices}
            >
              Refresh
            </Button>
          }
        >
          <Table
            columns={deviceColumns}
            dataSource={devices}
            rowKey="id"
            loading={isLoadingDevices}
            pagination={{ pageSize: 20 }}
          />
        </Card>
      ),
    },
    {
      key: 'vulnerabilities',
      label: (
        <span>
          <Badge count={vulnerabilities.length} offset={[10, 0]} showZero={false}>
            <SafetyOutlined /> Vulnerabilities
          </Badge>
        </span>
      ),
      children: (
        <Card
          title="Vulnerabilities Detected by Cyber Vision"
          size="small"
          extra={
            <Button
              icon={<SyncOutlined />}
              onClick={() => fetchVulnerabilities()}
              loading={isLoadingVulnerabilities}
            >
              Refresh
            </Button>
          }
        >
          <Table
            columns={vulnerabilityColumns}
            dataSource={vulnerabilities}
            rowKey="id"
            loading={isLoadingVulnerabilities}
            pagination={{ pageSize: 20 }}
          />
        </Card>
      ),
    },
    {
      key: 'mac-analysis',
      label: (
        <span>
          <Badge
            count={macAnalysis?.duplicate_groups_count ?? 0}
            offset={[10, 0]}
            showZero={false}
          >
            <ApartmentOutlined /> MAC Analysis
          </Badge>
        </span>
      ),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* Scan controls */}
          <Card title="Duplicate MAC Detection" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary">
                Scan all Cyber Vision assets for devices sharing the same MAC address.
                Duplicates are classified by severity to help identify spoofing, cloned devices,
                or data quality issues.
              </Text>
              <Row gutter={[8, 8]}>
                <Col flex="200px">
                  <Select
                    placeholder="CV Preset (optional)"
                    style={{ width: '100%' }}
                    loading={isLoadingPresets}
                    options={presets.map((p) => ({ value: p.id, label: p.label }))}
                    value={macPresetFilter}
                    onChange={(value) => {
                      setMacPresetFilter(value);
                      clearMacAnalysis();
                    }}
                    allowClear
                    showSearch
                    filterOption={(input, option) =>
                      (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                  />
                </Col>
                <Col>
                  <Button
                    type="primary"
                    onClick={() => analyzeDuplicateMacs(macPresetFilter || undefined)}
                    loading={isLoadingMacAnalysis}
                    icon={<SyncOutlined />}
                  >
                    Scan for Duplicates
                  </Button>
                </Col>
              </Row>
            </Space>
          </Card>

          {/* Results */}
          {macAnalysis && (
            <>
              {/* Summary statistics */}
              <Row gutter={16}>
                <Col span={4}>
                  <Card size="small">
                    <Statistic title="Devices Analyzed" value={macAnalysis.total_devices_analyzed} />
                  </Card>
                </Col>
                <Col span={4}>
                  <Card size="small">
                    <Statistic title="Unique MACs" value={macAnalysis.unique_macs} />
                  </Card>
                </Col>
                <Col span={4}>
                  <Card size="small">
                    <Statistic
                      title="Duplicate Groups"
                      value={macAnalysis.duplicate_groups_count}
                      valueStyle={{
                        color: macAnalysis.duplicate_groups_count > 0 ? '#faad14' : '#52c41a',
                      }}
                    />
                  </Card>
                </Col>
                <Col span={3}>
                  <Card size="small">
                    <Statistic
                      title="Critical"
                      value={macAnalysis.severity_counts.critical}
                      valueStyle={
                        macAnalysis.severity_counts.critical > 0 ? { color: '#f5222d' } : undefined
                      }
                    />
                  </Card>
                </Col>
                <Col span={3}>
                  <Card size="small">
                    <Statistic
                      title="High"
                      value={macAnalysis.severity_counts.high}
                      valueStyle={
                        macAnalysis.severity_counts.high > 0 ? { color: '#fa8c16' } : undefined
                      }
                    />
                  </Card>
                </Col>
                <Col span={3}>
                  <Card size="small">
                    <Statistic
                      title="Medium"
                      value={macAnalysis.severity_counts.medium}
                      valueStyle={
                        macAnalysis.severity_counts.medium > 0 ? { color: '#fadb14' } : undefined
                      }
                    />
                  </Card>
                </Col>
                <Col span={3}>
                  <Card size="small">
                    <Statistic
                      title="No MAC"
                      value={macAnalysis.devices_without_mac}
                      valueStyle={
                        macAnalysis.devices_without_mac > 0 ? { color: '#8c8c8c' } : undefined
                      }
                    />
                  </Card>
                </Col>
              </Row>

              {/* Duplicate groups table */}
              {macAnalysis.duplicate_groups.length > 0 ? (
                <Card
                  title={
                    <Space>
                      <WarningOutlined style={{ color: '#faad14' }} />
                      Duplicate MAC Groups ({macAnalysis.duplicate_groups_count})
                    </Space>
                  }
                  size="small"
                >
                  <Table<DuplicateMacGroup>
                    columns={[
                      {
                        title: 'MAC Address',
                        dataIndex: 'mac',
                        key: 'mac',
                        width: 160,
                        render: (mac: string) => (
                          <Text code style={{ fontSize: 12 }}>
                            {mac}
                          </Text>
                        ),
                      },
                      {
                        title: 'OUI Vendor',
                        dataIndex: 'oui_vendor',
                        key: 'oui_vendor',
                        width: 150,
                        render: (vendor: string | null) =>
                          vendor || <Text type="secondary">Unknown</Text>,
                      },
                      {
                        title: 'Severity',
                        dataIndex: 'severity',
                        key: 'severity',
                        width: 110,
                        filters: [
                          { text: 'Critical', value: 'critical' },
                          { text: 'High', value: 'high' },
                          { text: 'Medium', value: 'medium' },
                          { text: 'Low', value: 'low' },
                        ],
                        onFilter: (value, record) => record.severity === value,
                        render: (severity: string) => {
                          const colorMap: Record<string, string> = {
                            critical: 'red',
                            high: 'orange',
                            medium: 'gold',
                            low: 'blue',
                          };
                          return (
                            <Tag color={colorMap[severity] || 'default'}>
                              {severity.toUpperCase()}
                            </Tag>
                          );
                        },
                      },
                      {
                        title: 'Devices',
                        dataIndex: 'device_count',
                        key: 'device_count',
                        width: 90,
                        sorter: (a, b) => a.device_count - b.device_count,
                      },
                      {
                        title: 'Reason',
                        dataIndex: 'reason',
                        key: 'reason',
                        ellipsis: true,
                      },
                    ]}
                    dataSource={macAnalysis.duplicate_groups}
                    rowKey="mac"
                    expandable={{
                      expandedRowRender: (record: DuplicateMacGroup) => (
                        <Table<DuplicateMacDeviceInfo>
                          columns={[
                            {
                              title: 'Name',
                              dataIndex: 'name',
                              key: 'name',
                              render: (name: string) => <Text strong>{name}</Text>,
                            },
                            {
                              title: 'IP Address',
                              dataIndex: 'ip',
                              key: 'ip',
                              render: (ip: string | null) =>
                                ip || <Text type="secondary">-</Text>,
                            },
                            {
                              title: 'Vendor',
                              dataIndex: 'vendor',
                              key: 'vendor',
                              render: (vendor: string | null) =>
                                vendor || <Text type="secondary">Unknown</Text>,
                            },
                            {
                              title: 'Model',
                              dataIndex: 'model',
                              key: 'model',
                              render: (model: string | null) =>
                                model || <Text type="secondary">-</Text>,
                            },
                            {
                              title: 'Category',
                              dataIndex: 'category',
                              key: 'category',
                              render: (cat: string | null) =>
                                cat ? <Tag>{cat}</Tag> : <Text type="secondary">-</Text>,
                            },
                            {
                              title: 'Group',
                              dataIndex: 'group_name',
                              key: 'group_name',
                              render: (g: string | null) =>
                                g || <Text type="secondary">-</Text>,
                            },
                            {
                              title: 'First Seen',
                              dataIndex: 'first_seen',
                              key: 'first_seen',
                              render: (v: string | null) =>
                                v || <Text type="secondary">-</Text>,
                            },
                          ]}
                          dataSource={record.devices}
                          rowKey="id"
                          pagination={{ pageSize: 10 }}
                          size="small"
                        />
                      ),
                    }}
                    pagination={{ pageSize: 20 }}
                    size="small"
                  />
                </Card>
              ) : (
                <Card size="small">
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description={
                      <Text type="secondary">
                        No duplicate MAC addresses found across{' '}
                        {macAnalysis.total_devices_analyzed} devices.
                      </Text>
                    }
                  />
                </Card>
              )}

              {/* Devices without MAC */}
              {macAnalysis.no_mac_devices.length > 0 && (
                <Card
                  title={
                    <Space>
                      <InfoCircleOutlined style={{ color: '#8c8c8c' }} />
                      Devices Without MAC ({macAnalysis.devices_without_mac})
                    </Space>
                  }
                  size="small"
                >
                  <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                    These devices have no MAC address recorded in Cyber Vision, which may
                    indicate Layer 3 only visibility or incomplete discovery.
                  </Text>
                  <Table
                    columns={[
                      {
                        title: 'Name',
                        dataIndex: 'name',
                        key: 'name',
                        render: (name: string) => <Text strong>{name}</Text>,
                      },
                      {
                        title: 'IP',
                        dataIndex: 'ip',
                        key: 'ip',
                        render: (ip: string | null) =>
                          ip || <Text type="secondary">-</Text>,
                      },
                      {
                        title: 'Vendor',
                        dataIndex: 'vendor',
                        key: 'vendor',
                        render: (v: string | null) =>
                          v || <Text type="secondary">Unknown</Text>,
                      },
                      {
                        title: 'Category',
                        dataIndex: 'category',
                        key: 'category',
                        render: (c: string | null) =>
                          c ? <Tag>{c}</Tag> : <Text type="secondary">-</Text>,
                      },
                      {
                        title: 'Group',
                        dataIndex: 'group_name',
                        key: 'group_name',
                      },
                    ]}
                    dataSource={macAnalysis.no_mac_devices}
                    rowKey="id"
                    pagination={{ pageSize: 10 }}
                    size="small"
                  />
                </Card>
              )}
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header */}
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={2} style={{ margin: 0 }}>
              <EyeOutlined /> Cyber Vision
              <ContextualHelpIcon articleId="cyber-vision" tooltip="Cyber Vision integration help" />
            </Title>
            <Text type="secondary">
              View discovered devices and compare with scenarios
            </Text>
          </Col>
          <Col>
            <Space>
              {connectionStatus?.connected ? (
                <Tag icon={<CheckCircleOutlined />} color="success">
                  Connected
                </Tag>
              ) : (
                <Tag icon={<CloseCircleOutlined />} color="error">
                  Disconnected
                </Tag>
              )}
              <Button
                icon={<SettingOutlined />}
                onClick={() => navigate('/settings')}
              >
                Settings
              </Button>
            </Space>
          </Col>
        </Row>

        {error && (
          <Alert
            message="Error"
            description={error}
            type="error"
            showIcon
            closable
            onClose={clearError}
          />
        )}

        {isLoading ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>
              <Text type="secondary">Loading...</Text>
            </div>
          </div>
        ) : (
          <Card>
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              items={tabItems}
            />
          </Card>
        )}
      </Space>

      {/* Enrichment Modal */}
      <Modal
        title={
          <Space>
            <CloudUploadOutlined />
            Push Data to Cyber Vision
          </Space>
        }
        open={enrichModalOpen}
        onCancel={() => {
          setEnrichModalOpen(false);
          setEnrichTarget(null);
        }}
        onOk={handleEnrich}
        okText="Push to CV"
        okButtonProps={{ loading: isEnriching, icon: <CloudUploadOutlined /> }}
        cancelButtonProps={{ disabled: isEnriching }}
      >
        {enrichTarget && (() => {
          const availableProps = getAvailableProperties(enrichTarget);
          const cvDevice = enrichTarget.cv_device;
          // Map property labels to current CV values for before/after preview
          const cvCurrentValues: Record<string, string | null> = {
            'Vendor': cvDevice.vendor || null,
            'Model': cvDevice.model || null,
            'Device Type': cvDevice.category || null,
            'Role': null,
            'Protocols': null,
            'Hostname': null,
          };
          return (
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">Source:</Text>
                <div>
                  <Text strong>{enrichTarget.scenario_device.name as string || 'Unnamed'}</Text>
                  <Text type="secondary"> (PacketArch Scenario)</Text>
                </div>
              </div>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">Target:</Text>
                <div>
                  <Text strong>{cvDevice.name}</Text>
                  <Text type="secondary"> (Cyber Vision ID: {cvDevice.id})</Text>
                </div>
              </div>

              {/* Before / After preview */}
              <Table
                size="small"
                pagination={false}
                dataSource={availableProps.map((prop) => ({
                  key: prop.label,
                  property: prop.label,
                  cvCurrent: cvCurrentValues[prop.label] || null,
                  proposed: prop.value,
                }))}
                columns={[
                  {
                    title: 'Property',
                    dataIndex: 'property',
                    key: 'property',
                    render: (v: string) => <Text strong>{v}</Text>,
                  },
                  {
                    title: 'CV Current',
                    dataIndex: 'cvCurrent',
                    key: 'cvCurrent',
                    render: (v: string | null) => v ? <Text>{v}</Text> : <Text type="secondary" italic>empty</Text>,
                  },
                  {
                    title: 'PacketArch',
                    dataIndex: 'proposed',
                    key: 'proposed',
                    render: (v: string, record: { cvCurrent: string | null }) => (
                      <Text style={{ color: record.cvCurrent ? undefined : '#52c41a' }}>{v}</Text>
                    ),
                  },
                ]}
                style={{ marginBottom: 16 }}
              />

              <div>
                <Text style={{ display: 'block', marginBottom: 8 }}>
                  Select properties to push:
                </Text>
                <Checkbox.Group
                  value={selectedProperties}
                  onChange={(values) => setSelectedProperties(values as string[])}
                  style={{ width: '100%' }}
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {availableProps.map((prop) => (
                      <Checkbox key={prop.label} value={prop.label}>
                        <Text strong>{prop.label}:</Text> {prop.value}
                      </Checkbox>
                    ))}
                  </Space>
                </Checkbox.Group>
              </div>
              <Alert
                message="Note"
                description="Properties will be added as custom user properties in Cyber Vision. Existing properties with the same label will be skipped."
                type="info"
                showIcon
                style={{ marginTop: 16 }}
              />
            </Space>
          );
        })()}
      </Modal>

      {/* Bulk Enrichment Progress Modal */}
      <Modal
        title={
          <Space>
            <CloudUploadOutlined />
            Bulk Enrich Devices
          </Space>
        }
        open={bulkEnrichModalOpen}
        onCancel={() => {
          if (!isBulkEnriching) {
            setBulkEnrichModalOpen(false);
            setBulkEnrichResults(null);
            setBulkEnrichPreview(null);
          }
        }}
        footer={
          bulkEnrichResults ? (
            <Space>
              <Button onClick={() => {
                setBulkEnrichModalOpen(false);
                setBulkEnrichResults(null);
                setBulkEnrichPreview(null);
              }}>
                Done
              </Button>
              <Button type="primary" icon={<SyncOutlined />} onClick={() => {
                setBulkEnrichModalOpen(false);
                setBulkEnrichResults(null);
                setBulkEnrichPreview(null);
                handleCompare();
              }}>
                Re-compare
              </Button>
            </Space>
          ) : bulkEnrichPreview ? (
            <Space>
              <Button onClick={() => {
                setBulkEnrichModalOpen(false);
                setBulkEnrichPreview(null);
              }}>
                Cancel
              </Button>
              <Button
                type="primary"
                icon={<CloudUploadOutlined />}
                onClick={handleBulkEnrich}
                disabled={bulkEnrichPreview.devicesWithData === 0}
              >
                Start Enrichment ({bulkEnrichPreview.devicesWithData} devices)
              </Button>
            </Space>
          ) : null
        }
        closable={!isBulkEnriching}
        maskClosable={!isBulkEnriching}
        width={600}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {bulkEnrichPreview && !isBulkEnriching && !bulkEnrichResults ? (
            <>
              <Alert
                message="Enrichment Preview"
                description={
                  <Space direction="vertical">
                    <Text>
                      <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                      <strong>{bulkEnrichPreview.devicesWithData}</strong> devices have data to enrich
                    </Text>
                    <Text type="secondary">
                      <WarningOutlined style={{ marginRight: 8 }} />
                      {bulkEnrichPreview.devicesWithoutData} devices have no enrichment data
                    </Text>
                  </Space>
                }
                type={bulkEnrichPreview.devicesWithData > 0 ? 'info' : 'warning'}
                showIcon
              />

              {bulkEnrichPreview.sampleProperties.length > 0 ? (
                <Card size="small" title="Sample data to be pushed:">
                  {bulkEnrichPreview.sampleProperties.map((sample, i) => (
                    <div key={i} style={{ marginBottom: i < bulkEnrichPreview.sampleProperties.length - 1 ? 12 : 0 }}>
                      <Text strong>{sample.device}:</Text>
                      <ul style={{ margin: '4px 0 0 0', paddingLeft: 20 }}>
                        {sample.props.map((prop, j) => (
                          <li key={j}><Text type="secondary">{prop}</Text></li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </Card>
              ) : (
                <Alert
                  message="No Data Available"
                  description={
                    <div>
                      <Text>The matched scenario devices don't have enrichment data (vendor, model, type, etc.).</Text>
                      <br />
                      <Text type="secondary">
                        Check browser console (F12) to see the scenario_device structure and available fields.
                      </Text>
                    </div>
                  }
                  type="warning"
                  showIcon
                />
              )}
            </>
          ) : isBulkEnriching ? (
            <>
              <Text>
                Enriching device {bulkEnrichProgress} of {bulkEnrichTotal}...
              </Text>
              <Progress
                percent={Math.round((bulkEnrichProgress / bulkEnrichTotal) * 100)}
                status="active"
                strokeColor={{ from: '#108ee9', to: '#87d068' }}
              />
              <Text type="secondary">
                Please wait while properties are pushed to Cyber Vision.
              </Text>
            </>
          ) : bulkEnrichResults ? (
            <>
              <Alert
                message="Enrichment Complete"
                description={
                  <Space direction="vertical">
                    <Text>
                      <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                      <strong>{bulkEnrichResults.success}</strong> devices processed
                    </Text>
                    <Text>
                      <CloudUploadOutlined style={{ color: '#1890ff', marginRight: 8 }} />
                      <strong>{bulkEnrichResults.totalProps}</strong> properties pushed to CV
                    </Text>
                    {bulkEnrichResults.failed > 0 && (
                      <Text>
                        <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
                        <strong>{bulkEnrichResults.failed}</strong> devices failed
                      </Text>
                    )}
                    {bulkEnrichResults.skipped > 0 && (
                      <Text type="secondary">
                        {bulkEnrichResults.skipped} devices skipped (no data)
                      </Text>
                    )}
                  </Space>
                }
                type={bulkEnrichResults.totalProps > 0 ? 'success' : bulkEnrichResults.failed > 0 ? 'error' : 'warning'}
                showIcon
              />
              {bulkEnrichResults.totalProps === 0 && bulkEnrichResults.failed === 0 && (
                <Alert
                  message="No Properties Added"
                  description="Properties may have been skipped because they already exist in Cyber Vision, or the values were empty."
                  type="info"
                  showIcon
                />
              )}
              {bulkEnrichResults.errors.length > 0 && (
                <Alert
                  message="Errors"
                  description={
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                      {bulkEnrichResults.errors.slice(0, 5).map((err, i) => (
                        <li key={i}><Text type="danger">{err}</Text></li>
                      ))}
                      {bulkEnrichResults.errors.length > 5 && (
                        <li><Text type="secondary">...and {bulkEnrichResults.errors.length - 5} more</Text></li>
                      )}
                    </ul>
                  }
                  type="error"
                  showIcon
                />
              )}
            </>
          ) : (
            <Text>Preparing bulk enrichment...</Text>
          )}
        </Space>
      </Modal>
    </div>
  );
};

export default CyberVisionPage;
