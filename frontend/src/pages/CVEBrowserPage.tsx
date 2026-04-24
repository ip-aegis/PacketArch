/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * CVE Browser Page - Browse CVE vulnerabilities for security testing
 */

import React, { useState, useMemo } from 'react';
import {
  Typography,
  Input,
  Select,
  Card,
  Row,
  Col,
  Tag,
  Space,
  Empty,
  Spin,
  Button,
  Tooltip,
  Drawer,
  Descriptions,
  Divider,
  Statistic,
  Switch,
  List,
  App,
} from 'antd';
import {
  SearchOutlined,
  BugOutlined,
  SafetyCertificateOutlined,
  ReloadOutlined,
  LinkOutlined,
  CopyOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import {
  listCVEs,
  getCVEStats,
  getCVEDetail,
  listVulnerableVariants,
  getSeverityColor,
  formatCVSSScore,
  type CVEListResponse,
  type CVEStatsResponse,
  type VulnerableVariantsResponse,
} from '../api/cve';
import type { CVEVulnerability, VulnerableFingerprintVariant, CVESeverity } from '../types';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// Vendor colors (matching backend vendor names)
const vendorColors: Record<string, string> = {
  'Rockwell': '#B22222',
  'Siemens': '#009999',
  'Schneider': '#3DCD58',
  'Honeywell': '#E31937',
  'GE': '#005EB8',
  'ABB': '#FF000F',
};

// Severity icons
const severityIcons: Record<string, React.ReactNode> = {
  critical: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
  high: <ExclamationCircleOutlined style={{ color: '#fa8c16' }} />,
  medium: <WarningOutlined style={{ color: '#faad14' }} />,
  low: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
};

const CVEBrowserPage: React.FC = () => {
  const { message: antMessage } = App.useApp();
  const [searchText, setSearchText] = useState('');
  const [selectedVendor, setSelectedVendor] = useState<string | undefined>();
  const [selectedSeverity, setSelectedSeverity] = useState<CVESeverity | undefined>();
  const [cyberVisionOnly, setCyberVisionOnly] = useState(false);
  const [selectedCVEId, setSelectedCVEId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Fetch CVE stats
  const { data: stats, isLoading: loadingStats, refetch: refetchStats } = useQuery({
    queryKey: ['cveStats'],
    queryFn: getCVEStats,
  });

  // Fetch CVEs with filters
  const { data: cveData, isLoading: loadingCVEs, refetch: refetchCVEs } = useQuery({
    queryKey: ['cves', selectedVendor, selectedSeverity, cyberVisionOnly],
    queryFn: () => listCVEs({
      vendor: selectedVendor,
      severity: selectedSeverity,
      cyber_vision_only: cyberVisionOnly || undefined,
    }),
  });

  // Fetch full CVE details when selected
  const { data: selectedCVE, isLoading: loadingDetail } = useQuery({
    queryKey: ['cveDetail', selectedCVEId],
    queryFn: () => selectedCVEId ? getCVEDetail(selectedCVEId) : Promise.reject('No CVE selected'),
    enabled: !!selectedCVEId,
  });

  // Fetch variants for selected CVE
  const { data: variantsData, isLoading: loadingVariants } = useQuery({
    queryKey: ['cveVariants', selectedCVEId],
    queryFn: () => selectedCVEId ? listVulnerableVariants({ cve_id: selectedCVEId }) : Promise.resolve({ variants: [], count: 0 }),
    enabled: !!selectedCVEId,
  });

  // Filter CVEs by search text
  const filteredCVEs = useMemo(() => {
    if (!cveData?.cves) return [];
    if (!searchText) return cveData.cves;

    const search = searchText.toLowerCase();
    return cveData.cves.filter(
      (cve) =>
        cve.cve_id.toLowerCase().includes(search) ||
        cve.title.toLowerCase().includes(search) ||
        cve.product_family.toLowerCase().includes(search)
    );
  }, [cveData?.cves, searchText]);

  // Get unique vendors for filter
  const vendors = useMemo(() => {
    return cveData?.vendors || [];
  }, [cveData?.vendors]);

  const handleRefresh = () => {
    refetchStats();
    refetchCVEs();
  };

  const handleCVEClick = (cve: CVEVulnerability) => {
    setSelectedCVEId(cve.cve_id);
    setDrawerOpen(true);
  };

  const handleCopyId = (cveId: string) => {
    navigator.clipboard.writeText(cveId);
    antMessage.success('CVE ID copied to clipboard');
  };

  const isLoading = loadingStats || loadingCVEs;

  return (
    <div style={{ padding: '24px', background: '#0d0d1a', minHeight: '100vh' }}>
      {/* Page Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Title level={2} style={{ color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: 12 }}>
              <BugOutlined style={{ color: '#ff4d4f' }} />
              CVE Browser
            </Title>
            <Text style={{ color: '#8b8fa3' }}>
              Browse vulnerabilities for ICS/OT security testing with Cisco Cyber Vision
            </Text>
          </div>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            loading={isLoading}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card
            style={{ background: '#1a1a2e', border: '1px solid #2d2d52' }}
            styles={{ body: { padding: '16px' } }}
          >
            <Statistic
              title={<Text style={{ color: '#8b8fa3' }}>Total CVEs</Text>}
              value={stats?.total_cves || 0}
              valueStyle={{ color: '#fff', fontSize: 28 }}
              prefix={<BugOutlined style={{ color: '#5a9fd4', marginRight: 8 }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card
            style={{ background: '#1a1a2e', border: '1px solid #2d2d52' }}
            styles={{ body: { padding: '16px' } }}
          >
            <Statistic
              title={<Text style={{ color: '#8b8fa3' }}>Critical</Text>}
              value={stats?.by_severity?.critical || 0}
              valueStyle={{ color: '#ff4d4f', fontSize: 28 }}
              prefix={<CloseCircleOutlined style={{ marginRight: 8 }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card
            style={{ background: '#1a1a2e', border: '1px solid #2d2d52' }}
            styles={{ body: { padding: '16px' } }}
          >
            <Statistic
              title={<Text style={{ color: '#8b8fa3' }}>Vendors</Text>}
              value={Object.keys(stats?.by_vendor || {}).length}
              valueStyle={{ color: '#fff', fontSize: 28 }}
              prefix={<SafetyCertificateOutlined style={{ color: '#52c41a', marginRight: 8 }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card
            style={{ background: '#1a1a2e', border: '1px solid #2d2d52' }}
            styles={{ body: { padding: '16px' } }}
          >
            <Statistic
              title={<Text style={{ color: '#8b8fa3' }}>Cyber Vision</Text>}
              value={stats?.cyber_vision_detectable || 0}
              valueStyle={{ color: '#13c2c2', fontSize: 28 }}
              prefix={<CheckCircleOutlined style={{ marginRight: 8 }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Card
        style={{ background: '#1a1a2e', border: '1px solid #2d2d52', marginBottom: 24 }}
        styles={{ body: { padding: '16px' } }}
      >
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={8} md={6}>
            <Input
              placeholder="Search CVE ID, title, product..."
              prefix={<SearchOutlined style={{ color: '#6b6b8a' }} />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
              style={{ background: '#0d0d1a', borderColor: '#2d2d52' }}
            />
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Select
              placeholder="Vendor"
              value={selectedVendor}
              onChange={setSelectedVendor}
              allowClear
              style={{ width: '100%' }}
            >
              {vendors.map((vendor) => (
                <Option key={vendor} value={vendor}>
                  <Space>
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: vendorColors[vendor] || '#666',
                        display: 'inline-block',
                      }}
                    />
                    {vendor}
                  </Space>
                </Option>
              ))}
            </Select>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Select
              placeholder="Severity"
              value={selectedSeverity}
              onChange={setSelectedSeverity}
              allowClear
              style={{ width: '100%' }}
            >
              <Option value="critical">
                <Space>{severityIcons.critical} Critical</Space>
              </Option>
              <Option value="high">
                <Space>{severityIcons.high} High</Space>
              </Option>
              <Option value="medium">
                <Space>{severityIcons.medium} Medium</Space>
              </Option>
              <Option value="low">
                <Space>{severityIcons.low} Low</Space>
              </Option>
            </Select>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Space>
              <Switch
                checked={cyberVisionOnly}
                onChange={setCyberVisionOnly}
                size="small"
              />
              <Text style={{ color: '#8b8fa3', fontSize: 13 }}>
                Cyber Vision Detectable Only
              </Text>
            </Space>
          </Col>
          <Col flex="auto" style={{ textAlign: 'right' }}>
            <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
              {filteredCVEs.length} CVEs found
            </Text>
          </Col>
        </Row>
      </Card>

      {/* CVE List */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text style={{ color: '#8b8fa3' }}>Loading vulnerabilities...</Text>
          </div>
        </div>
      ) : filteredCVEs.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Text style={{ color: '#8b8fa3' }}>
              No CVEs found matching your criteria
            </Text>
          }
        />
      ) : (
        <Row gutter={[16, 16]}>
          {filteredCVEs.map((cve) => (
            <Col xs={24} sm={12} lg={8} xl={6} key={cve.cve_id}>
              <CVECard cve={cve} onClick={() => handleCVEClick(cve)} />
            </Col>
          ))}
        </Row>
      )}

      {/* CVE Detail Drawer */}
      <Drawer
        title={
          <Space>
            <BugOutlined style={{ color: '#ff4d4f' }} />
            <span>{selectedCVE?.cve_id}</span>
            <Button
              type="text"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => selectedCVE && handleCopyId(selectedCVE.cve_id)}
            />
          </Space>
        }
        placement="right"
        width={480}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setSelectedCVEId(null);
        }}
        styles={{
          header: { background: '#1a1a2e', borderBottom: '1px solid #2d2d52' },
          body: { background: '#0d0d1a', padding: '16px' },
        }}
      >
        {loadingDetail ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
          </div>
        ) : selectedCVE ? (
          <CVEDetailContent
            cve={selectedCVE}
            variants={variantsData?.variants || []}
            loadingVariants={loadingVariants}
          />
        ) : null}
      </Drawer>
    </div>
  );
};

// CVE Card Component
interface CVECardProps {
  cve: CVEVulnerability;
  onClick: () => void;
}

const CVECard: React.FC<CVECardProps> = ({ cve, onClick }) => {
  return (
    <Card
      hoverable
      onClick={onClick}
      style={{
        background: '#1a1a2e',
        border: '1px solid #2d2d52',
        cursor: 'pointer',
      }}
      styles={{ body: { padding: '16px' } }}
    >
      {/* Header with CVE ID and Severity */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <Text style={{ color: '#fff', fontWeight: 600, fontSize: 14 }}>
          {cve.cve_id}
        </Text>
        <Tag
          color={getSeverityColor(cve.severity)}
          style={{ margin: 0, textTransform: 'uppercase', fontSize: 10, fontWeight: 600 }}
        >
          {cve.severity}
        </Tag>
      </div>

      {/* Title */}
      <Paragraph
        ellipsis={{ rows: 2 }}
        style={{ color: '#c9d1d9', fontSize: 12, marginBottom: 8, minHeight: 36 }}
      >
        {cve.title}
      </Paragraph>

      {/* CVSS Score */}
      <div style={{ marginBottom: 12 }}>
        <Space size={4}>
          <Text style={{ color: '#8b8fa3', fontSize: 11 }}>CVSS</Text>
          <Tag
            color={cve.cvss_score >= 9 ? 'red' : cve.cvss_score >= 7 ? 'orange' : 'gold'}
            style={{ fontSize: 11, fontWeight: 600 }}
          >
            {formatCVSSScore(cve.cvss_score)}
          </Tag>
        </Space>
      </div>

      {/* Tags */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        <Tag
          style={{
            fontSize: 10,
            background: vendorColors[cve.vendor] || '#444',
            border: 'none',
            color: '#fff',
          }}
        >
          {cve.vendor}
        </Tag>
        <Tag style={{ fontSize: 10, background: '#2d2d52', border: 'none', color: '#c9d1d9' }}>
          {cve.product_family}
        </Tag>
        {cve.cyber_vision_detectable && (
          <Tooltip title="Detectable by Cisco Cyber Vision">
            <Tag color="cyan" style={{ fontSize: 10 }}>
              <CheckCircleOutlined /> CV
            </Tag>
          </Tooltip>
        )}
      </div>
    </Card>
  );
};

// CVE Detail Content Component
interface CVEDetailContentProps {
  cve: CVEVulnerability;
  variants: VulnerableFingerprintVariant[];
  loadingVariants: boolean;
}

const CVEDetailContent: React.FC<CVEDetailContentProps> = ({ cve, variants, loadingVariants }) => {
  return (
    <div>
      {/* Severity and CVSS */}
      <div style={{ marginBottom: 16 }}>
        <Space size="middle">
          <Tag
            color={getSeverityColor(cve.severity)}
            style={{ fontSize: 14, padding: '4px 12px', textTransform: 'uppercase' }}
          >
            {severityIcons[cve.severity]} {cve.severity}
          </Tag>
          <Statistic
            title={<Text style={{ color: '#8b8fa3', fontSize: 11 }}>CVSS Score</Text>}
            value={formatCVSSScore(cve.cvss_score)}
            valueStyle={{ color: cve.cvss_score >= 9 ? '#ff4d4f' : '#fa8c16', fontSize: 24 }}
          />
        </Space>
      </div>

      {/* Title */}
      <Title level={4} style={{ color: '#fff', marginBottom: 16 }}>
        {cve.title}
      </Title>

      {/* Description */}
      <Paragraph style={{ color: '#c9d1d9', marginBottom: 16 }}>
        {cve.description}
      </Paragraph>

      <Divider style={{ borderColor: '#2d2d52' }} />

      {/* Details */}
      <Descriptions
        column={1}
        size="small"
        labelStyle={{ color: '#8b8fa3' }}
        contentStyle={{ color: '#fff' }}
      >
        <Descriptions.Item label="Vendor">
          <Tag color={vendorColors[cve.vendor] || 'default'}>{cve.vendor}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Product Family">{cve.product_family}</Descriptions.Item>
        <Descriptions.Item label="Affected Models">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {(cve.affected_models || []).map((model) => (
              <Tag key={model} style={{ fontSize: 10 }}>{model}</Tag>
            ))}
          </div>
        </Descriptions.Item>
        <Descriptions.Item label="Affected Firmware">
          {cve.affected_firmware_min ? `${cve.affected_firmware_min} - ` : '< '}
          {cve.affected_firmware_max}
        </Descriptions.Item>
        <Descriptions.Item label="Fixed Version">
          {cve.fixed_firmware_version || <Text type="danger">No fix available</Text>}
        </Descriptions.Item>
        <Descriptions.Item label="Cyber Vision">
          {cve.cyber_vision_detectable ? (
            <Tag color="cyan"><CheckCircleOutlined /> Detectable</Tag>
          ) : (
            <Tag color="default">Not Detectable</Tag>
          )}
        </Descriptions.Item>
      </Descriptions>

      <Divider style={{ borderColor: '#2d2d52' }} />

      {/* Vulnerable Variants */}
      <div>
        <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
          Vulnerable Firmware Variants ({variants.length})
        </Title>
        {loadingVariants ? (
          <Spin size="small" />
        ) : variants.length === 0 ? (
          <Text style={{ color: '#8b8fa3' }}>No variants available</Text>
        ) : (
          <List
            size="small"
            dataSource={variants}
            renderItem={(variant) => (
              <List.Item
                style={{
                  background: '#1a1a2e',
                  borderRadius: 4,
                  padding: '8px 12px',
                  marginBottom: 8,
                  border: '1px solid #2d2d52',
                }}
              >
                <Space direction="vertical" size={0} style={{ width: '100%' }}>
                  <Text style={{ color: '#fff', fontWeight: 500 }}>
                    {variant.display_name}
                  </Text>
                  <Text style={{ color: '#8b8fa3', fontSize: 11 }}>
                    Firmware: {variant.firmware_version}
                  </Text>
                </Space>
              </List.Item>
            )}
          />
        )}
      </div>

      {/* Advisory Link */}
      {cve.advisory_url && (
        <>
          <Divider style={{ borderColor: '#2d2d52' }} />
          <Button
            type="primary"
            icon={<LinkOutlined />}
            href={cve.advisory_url}
            target="_blank"
            block
          >
            View Vendor Advisory
          </Button>
        </>
      )}
    </div>
  );
};

export default CVEBrowserPage;
