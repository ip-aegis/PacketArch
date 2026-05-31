/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Device Library Page - Browse protocols, vendors, device templates, and fingerprints
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
  Tabs,
  List,
  App,
  Badge,
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ApiOutlined,
  ClusterOutlined,
  BuildOutlined,
  NodeIndexOutlined,
  WifiOutlined,
  CodeOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
  BugOutlined,
  LaptopOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import {
  listProtocols,
  getProtocolDetail,
  listVendorsComplete,
  getStats,
  listDeviceTemplates,
  getDeviceTemplateDetail,
  getCategoryColor,
  formatPort,
  getVendorCategory,
  type ProtocolInfo,
  type ProtocolDetail,
  type VendorComplete,
  type DeviceTemplateSummary,
  type DeviceTemplateDetail,
} from '../api/fingerprints';
import { TEXT_BODY, BORDER_ELEVATED } from '../constants/theme';
import ContextualHelpIcon from '../components/help/ContextualHelpIcon';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// Protocol category icons
const categoryIcons: Record<string, React.ReactNode> = {
  'Core Industrial': <BuildOutlined />,
  'SCADA/Utility': <ClusterOutlined />,
  'Power/Energy': <NodeIndexOutlined />,
  'Building Automation': <ApiOutlined />,
  'Network Management': <WifiOutlined />,
  'Vendor-Specific': <CodeOutlined />,
  'DCS Systems': <ClusterOutlined />,
  'Specialized': <ApiOutlined />,
};

const FingerprintingLibraryPage: React.FC<{ embedded?: boolean }> = ({ embedded = false }) => {
  const { message: antMessage } = App.useApp();
  const [activeTab, setActiveTab] = useState('protocols');
  const [searchText, setSearchText] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>();
  const [selectedDeviceType, setSelectedDeviceType] = useState<string | undefined>();

  // Device template filters
  const [templateVendorFilter, setTemplateVendorFilter] = useState<string | undefined>();
  const [templateDeviceTypeFilter, setTemplateDeviceTypeFilter] = useState<string | undefined>();
  const [templateCveFilter, setTemplateCveFilter] = useState<boolean | undefined>();

  // Drawer state
  const [protocolDrawerOpen, setProtocolDrawerOpen] = useState(false);
  const [vendorDrawerOpen, setVendorDrawerOpen] = useState(false);
  const [templateDrawerOpen, setTemplateDrawerOpen] = useState(false);
  const [selectedProtocolId, setSelectedProtocolId] = useState<string | null>(null);
  const [selectedVendor, setSelectedVendor] = useState<VendorComplete | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);

  // Fetch stats
  const { data: stats, isLoading: loadingStats, refetch: refetchStats } = useQuery({
    queryKey: ['fingerprintStats'],
    queryFn: getStats,
  });

  // Fetch protocols
  const { data: protocols, isLoading: loadingProtocols, refetch: refetchProtocols } = useQuery({
    queryKey: ['protocols', selectedCategory],
    queryFn: () => listProtocols(selectedCategory),
  });

  // Fetch vendors
  const { data: vendors, isLoading: loadingVendors, refetch: refetchVendors } = useQuery({
    queryKey: ['vendorsComplete', selectedDeviceType],
    queryFn: () => listVendorsComplete(selectedDeviceType),
  });

  // Fetch device templates
  const { data: deviceTemplates, isLoading: loadingTemplates, refetch: refetchTemplates } = useQuery({
    queryKey: ['deviceTemplates', templateVendorFilter, templateDeviceTypeFilter, templateCveFilter],
    queryFn: () => listDeviceTemplates({
      vendor: templateVendorFilter,
      device_type: templateDeviceTypeFilter,
      has_cves: templateCveFilter,
    }),
  });

  // Fetch template detail
  const { data: templateDetail, isLoading: loadingTemplateDetail } = useQuery({
    queryKey: ['templateDetail', selectedTemplateId],
    queryFn: () => selectedTemplateId ? getDeviceTemplateDetail(selectedTemplateId) : Promise.reject('No template selected'),
    enabled: !!selectedTemplateId,
  });

  // Fetch protocol detail
  const { data: protocolDetail, isLoading: loadingProtocolDetail } = useQuery({
    queryKey: ['protocolDetail', selectedProtocolId],
    queryFn: () => selectedProtocolId ? getProtocolDetail(selectedProtocolId) : Promise.reject('No protocol selected'),
    enabled: !!selectedProtocolId,
  });

  // Get unique categories
  const categories = useMemo(() => {
    if (!protocols) return [];
    return [...new Set(protocols.map(p => p.category))].sort();
  }, [protocols]);

  // Get unique device types from vendors
  const deviceTypes = useMemo(() => {
    if (!vendors) return [];
    const types = new Set<string>();
    vendors.forEach(v => v.device_types.forEach(dt => types.add(dt)));
    return [...types].sort();
  }, [vendors]);

  // Filter protocols by search
  const filteredProtocols = useMemo(() => {
    if (!protocols) return [];
    if (!searchText) return protocols;
    const search = searchText.toLowerCase();
    return protocols.filter(p =>
      p.name.toLowerCase().includes(search) ||
      p.description.toLowerCase().includes(search) ||
      p.category.toLowerCase().includes(search)
    );
  }, [protocols, searchText]);

  // Filter vendors by search
  const filteredVendors = useMemo(() => {
    if (!vendors) return [];
    if (!searchText) return vendors;
    const search = searchText.toLowerCase();
    return vendors.filter(v =>
      v.display_name.toLowerCase().includes(search) ||
      v.id.toLowerCase().includes(search) ||
      v.protocols.some(p => p.toLowerCase().includes(search))
    );
  }, [vendors, searchText]);

  // Filter device templates by search
  const filteredTemplates = useMemo(() => {
    if (!deviceTemplates) return [];
    if (!searchText) return deviceTemplates;
    const search = searchText.toLowerCase();
    return deviceTemplates.filter(t =>
      t.vendor.toLowerCase().includes(search) ||
      t.model.toLowerCase().includes(search) ||
      t.model_name.toLowerCase().includes(search) ||
      t.description.toLowerCase().includes(search) ||
      t.supported_protocols.some(p => p.toLowerCase().includes(search))
    );
  }, [deviceTemplates, searchText]);

  // Get unique vendors from templates
  const templateVendors = useMemo(() => {
    if (!deviceTemplates) return [];
    return [...new Set(deviceTemplates.map(t => t.vendor))].sort();
  }, [deviceTemplates]);

  // Get unique device types from templates
  const templateDeviceTypes = useMemo(() => {
    if (!deviceTemplates) return [];
    return [...new Set(deviceTemplates.map(t => t.device_type))].sort();
  }, [deviceTemplates]);

  const handleRefresh = () => {
    refetchStats();
    refetchProtocols();
    refetchVendors();
    refetchTemplates();
    antMessage.success('Data refreshed');
  };

  const handleProtocolClick = (protocol: ProtocolInfo) => {
    setSelectedProtocolId(protocol.id);
    setProtocolDrawerOpen(true);
  };

  const handleVendorClick = (vendor: VendorComplete) => {
    setSelectedVendor(vendor);
    setVendorDrawerOpen(true);
  };

  const handleTemplateClick = (template: DeviceTemplateSummary) => {
    setSelectedTemplateId(template.id);
    setTemplateDrawerOpen(true);
  };

  const isLoading = loadingStats || loadingProtocols || loadingVendors || loadingTemplates;

  return (
    <div style={embedded ? {} : { padding: '24px', background: '#0d0d1a', minHeight: '100vh' }}>
      {/* Page Header (hidden when embedded in the Library hub) */}
      {!embedded && (
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Title level={2} style={{ color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: 12 }}>
              <DatabaseOutlined style={{ color: '#049FD9' }} />
              Device Library
              <ContextualHelpIcon articleId="device-library" tooltip="Device library help" />
            </Title>
            <Text style={{ color: '#8b8fa3' }}>
              Browse protocols, vendors, and device templates for traffic generation
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
      )}

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={8} lg={4} xl={3}>
          <Card
            style={{ background: '#1a1a2e', border: '1px solid #2d2d52' }}
            styles={{ body: { padding: '12px' } }}
          >
            <Statistic
              title={<Text style={{ color: '#8b8fa3', fontSize: 11 }}>Protocols</Text>}
              value={stats?.total_protocols || 0}
              valueStyle={{ color: '#fff', fontSize: 22 }}
              prefix={<ApiOutlined style={{ color: '#049FD9', marginRight: 6 }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4} xl={3}>
          <Card
            style={{ background: '#1a1a2e', border: '1px solid #2d2d52' }}
            styles={{ body: { padding: '12px' } }}
          >
            <Statistic
              title={<Text style={{ color: '#8b8fa3', fontSize: 11 }}>Vendors</Text>}
              value={stats?.total_vendors || 0}
              valueStyle={{ color: '#fff', fontSize: 22 }}
              prefix={<BuildOutlined style={{ color: '#6CC04A', marginRight: 6 }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4} xl={3}>
          <Card
            style={{ background: '#1a1a2e', border: '1px solid #2d2d52' }}
            styles={{ body: { padding: '12px' } }}
          >
            <Statistic
              title={<Text style={{ color: '#8b8fa3', fontSize: 11 }}>Device Templates</Text>}
              value={stats?.total_device_templates || 0}
              valueStyle={{ color: '#fff', fontSize: 22 }}
              prefix={<LaptopOutlined style={{ color: '#E91E63', marginRight: 6 }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4} xl={3}>
          <Card
            style={{ background: '#1a1a2e', border: '1px solid #2d2d52' }}
            styles={{ body: { padding: '12px' } }}
          >
            <Statistic
              title={<Text style={{ color: '#8b8fa3', fontSize: 11 }}>Firmware Variants</Text>}
              value={stats?.total_firmware_variants || 0}
              valueStyle={{ color: '#fff', fontSize: 22 }}
              prefix={<DatabaseOutlined style={{ color: '#FF7043', marginRight: 6 }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4} xl={3}>
          <Card
            style={{ background: '#1a1a2e', border: '1px solid #2d2d52' }}
            styles={{ body: { padding: '12px' } }}
          >
            <Statistic
              title={<Text style={{ color: '#8b8fa3', fontSize: 11 }}>CVEs Tracked</Text>}
              value={stats?.total_cves || 0}
              valueStyle={{ color: '#fff', fontSize: 22 }}
              prefix={<BugOutlined style={{ color: '#f5222d', marginRight: 6 }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4} xl={3}>
          <Card
            style={{ background: '#1a1a2e', border: '1px solid #2d2d52' }}
            styles={{ body: { padding: '12px' } }}
          >
            <Statistic
              title={<Text style={{ color: '#8b8fa3', fontSize: 11 }}>OUI Prefixes</Text>}
              value={stats?.total_oui_prefixes || 0}
              valueStyle={{ color: '#fff', fontSize: 22 }}
              prefix={<WifiOutlined style={{ color: '#00BCD4', marginRight: 6 }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} lg={4} xl={3}>
          <Card
            style={{ background: '#1a1a2e', border: '1px solid #2d2d52' }}
            styles={{ body: { padding: '12px' } }}
          >
            <Statistic
              title={<Text style={{ color: '#8b8fa3', fontSize: 11 }}>Identity Builders</Text>}
              value={stats?.identity_builders || 0}
              valueStyle={{ color: '#fff', fontSize: 22 }}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a', marginRight: 6 }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabs */}
      <Card
        style={{ background: '#1a1a2e', border: '1px solid #2d2d52' }}
        styles={{ body: { padding: 0 } }}
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          style={{ padding: '0 16px' }}
          items={[
            {
              key: 'protocols',
              label: (
                <span>
                  <ApiOutlined /> Protocols ({protocols?.length || 0})
                </span>
              ),
              children: (
                <div style={{ padding: '16px 0' }}>
                  {/* Protocol Filters */}
                  <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                    <Col xs={24} sm={12} md={8}>
                      <Input
                        placeholder="Search protocols..."
                        prefix={<SearchOutlined style={{ color: '#6b6b8a' }} />}
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        allowClear
                        style={{ background: '#0d0d1a', borderColor: BORDER_ELEVATED }}
                      />
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                      <Select
                        placeholder="Category"
                        value={selectedCategory}
                        onChange={setSelectedCategory}
                        allowClear
                        style={{ width: '100%' }}
                      >
                        {categories.map((cat) => (
                          <Option key={cat} value={cat}>
                            <Space>
                              <span
                                style={{
                                  width: 8,
                                  height: 8,
                                  borderRadius: '50%',
                                  background: getCategoryColor(cat),
                                  display: 'inline-block',
                                }}
                              />
                              {cat}
                            </Space>
                          </Option>
                        ))}
                      </Select>
                    </Col>
                    <Col flex="auto" style={{ textAlign: 'right' }}>
                      <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
                        {filteredProtocols.length} protocols
                      </Text>
                    </Col>
                  </Row>

                  {/* Protocol Cards */}
                  {loadingProtocols ? (
                    <div style={{ textAlign: 'center', padding: 48 }}>
                      <Spin size="large" />
                    </div>
                  ) : filteredProtocols.length === 0 ? (
                    <Empty description="No protocols found" />
                  ) : (
                    <Row gutter={[16, 16]}>
                      {filteredProtocols.map((protocol) => (
                        <Col xs={24} sm={12} lg={8} xl={6} key={protocol.id}>
                          <ProtocolCard protocol={protocol} onClick={() => handleProtocolClick(protocol)} />
                        </Col>
                      ))}
                    </Row>
                  )}
                </div>
              ),
            },
            {
              key: 'vendors',
              label: (
                <span>
                  <BuildOutlined /> Vendors ({vendors?.length || 0})
                </span>
              ),
              children: (
                <div style={{ padding: '16px 0' }}>
                  {/* Vendor Filters */}
                  <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                    <Col xs={24} sm={12} md={8}>
                      <Input
                        placeholder="Search vendors..."
                        prefix={<SearchOutlined style={{ color: '#6b6b8a' }} />}
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        allowClear
                        style={{ background: '#0d0d1a', borderColor: BORDER_ELEVATED }}
                      />
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                      <Select
                        placeholder="Device Type"
                        value={selectedDeviceType}
                        onChange={setSelectedDeviceType}
                        allowClear
                        style={{ width: '100%' }}
                        showSearch
                      >
                        {deviceTypes.map((dt) => (
                          <Option key={dt} value={dt}>
                            {dt.replace(/_/g, ' ')}
                          </Option>
                        ))}
                      </Select>
                    </Col>
                    <Col flex="auto" style={{ textAlign: 'right' }}>
                      <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
                        {filteredVendors.length} vendors
                      </Text>
                    </Col>
                  </Row>

                  {/* Vendor Cards */}
                  {loadingVendors ? (
                    <div style={{ textAlign: 'center', padding: 48 }}>
                      <Spin size="large" />
                    </div>
                  ) : filteredVendors.length === 0 ? (
                    <Empty description="No vendors found" />
                  ) : (
                    <Row gutter={[16, 16]}>
                      {filteredVendors.map((vendor) => (
                        <Col xs={24} sm={12} lg={8} xl={6} key={vendor.id}>
                          <VendorCard vendor={vendor} onClick={() => handleVendorClick(vendor)} />
                        </Col>
                      ))}
                    </Row>
                  )}
                </div>
              ),
            },
            {
              key: 'templates',
              label: (
                <span>
                  <LaptopOutlined /> Device Templates ({deviceTemplates?.length || 0})
                </span>
              ),
              children: (
                <div style={{ padding: '16px 0' }}>
                  {/* Template Filters */}
                  <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                    <Col xs={24} sm={12} md={6}>
                      <Input
                        placeholder="Search templates..."
                        prefix={<SearchOutlined style={{ color: '#6b6b8a' }} />}
                        value={searchText}
                        onChange={(e) => setSearchText(e.target.value)}
                        allowClear
                        style={{ background: '#0d0d1a', borderColor: BORDER_ELEVATED }}
                      />
                    </Col>
                    <Col xs={24} sm={6} md={4}>
                      <Select
                        placeholder="Vendor"
                        value={templateVendorFilter}
                        onChange={setTemplateVendorFilter}
                        allowClear
                        style={{ width: '100%' }}
                        showSearch
                      >
                        {templateVendors.map((v) => (
                          <Option key={v} value={v}>{v}</Option>
                        ))}
                      </Select>
                    </Col>
                    <Col xs={24} sm={6} md={4}>
                      <Select
                        placeholder="Device Type"
                        value={templateDeviceTypeFilter}
                        onChange={setTemplateDeviceTypeFilter}
                        allowClear
                        style={{ width: '100%' }}
                        showSearch
                      >
                        {templateDeviceTypes.map((dt) => (
                          <Option key={dt} value={dt}>{dt.replace(/_/g, ' ')}</Option>
                        ))}
                      </Select>
                    </Col>
                    <Col xs={24} sm={6} md={4}>
                      <Select
                        placeholder="CVE Filter"
                        value={templateCveFilter === undefined ? undefined : templateCveFilter ? 'yes' : 'no'}
                        onChange={(v) => setTemplateCveFilter(v === undefined ? undefined : v === 'yes')}
                        allowClear
                        style={{ width: '100%' }}
                      >
                        <Option value="yes">
                          <Space>
                            <BugOutlined style={{ color: '#f5222d' }} />
                            Has CVEs
                          </Space>
                        </Option>
                        <Option value="no">No CVEs</Option>
                      </Select>
                    </Col>
                    <Col flex="auto" style={{ textAlign: 'right' }}>
                      <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
                        {filteredTemplates.length} templates
                      </Text>
                    </Col>
                  </Row>

                  {/* Template Cards */}
                  {loadingTemplates ? (
                    <div style={{ textAlign: 'center', padding: 48 }}>
                      <Spin size="large" />
                    </div>
                  ) : filteredTemplates.length === 0 ? (
                    <Empty description="No device templates found" />
                  ) : (
                    <Row gutter={[16, 16]}>
                      {filteredTemplates.map((template) => (
                        <Col xs={24} sm={12} lg={8} xl={6} key={template.id}>
                          <DeviceTemplateCard template={template} onClick={() => handleTemplateClick(template)} />
                        </Col>
                      ))}
                    </Row>
                  )}
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* Protocol Detail Drawer */}
      <Drawer
        title={
          <Space>
            <ApiOutlined style={{ color: '#049FD9' }} />
            <span>{protocolDetail?.name || 'Protocol Details'}</span>
          </Space>
        }
        placement="right"
        width={480}
        open={protocolDrawerOpen}
        onClose={() => {
          setProtocolDrawerOpen(false);
          setSelectedProtocolId(null);
        }}
        styles={{
          header: { background: '#1a1a2e', borderBottom: '1px solid #2d2d52' },
          body: { background: '#0d0d1a', padding: '16px' },
        }}
      >
        {loadingProtocolDetail ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
          </div>
        ) : protocolDetail ? (
          <ProtocolDetailContent protocol={protocolDetail} />
        ) : null}
      </Drawer>

      {/* Vendor Detail Drawer */}
      <Drawer
        title={
          <Space>
            <BuildOutlined style={{ color: '#6CC04A' }} />
            <span>{selectedVendor?.display_name || 'Vendor Details'}</span>
          </Space>
        }
        placement="right"
        width={480}
        open={vendorDrawerOpen}
        onClose={() => {
          setVendorDrawerOpen(false);
          setSelectedVendor(null);
        }}
        styles={{
          header: { background: '#1a1a2e', borderBottom: '1px solid #2d2d52' },
          body: { background: '#0d0d1a', padding: '16px' },
        }}
      >
        {selectedVendor && <VendorDetailContent vendor={selectedVendor} />}
      </Drawer>

      {/* Device Template Detail Drawer */}
      <Drawer
        title={
          <Space>
            <LaptopOutlined style={{ color: '#E91E63' }} />
            <span>{templateDetail ? `${templateDetail.vendor} ${templateDetail.model_name}` : 'Device Template Details'}</span>
          </Space>
        }
        placement="right"
        width={600}
        open={templateDrawerOpen}
        onClose={() => {
          setTemplateDrawerOpen(false);
          setSelectedTemplateId(null);
        }}
        styles={{
          header: { background: '#1a1a2e', borderBottom: '1px solid #2d2d52' },
          body: { background: '#0d0d1a', padding: '16px' },
        }}
      >
        {loadingTemplateDetail ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
          </div>
        ) : templateDetail ? (
          <DeviceTemplateDetailContent template={templateDetail} />
        ) : null}
      </Drawer>
    </div>
  );
};

// ========== Card Components ==========

interface ProtocolCardProps {
  protocol: ProtocolInfo;
  onClick: () => void;
}

const ProtocolCard: React.FC<ProtocolCardProps> = ({ protocol, onClick }) => {
  return (
    <Card
      hoverable
      onClick={onClick}
      style={{
        background: '#0d0d1a',
        border: '1px solid #2d2d52',
        cursor: 'pointer',
      }}
      styles={{ body: { padding: '16px' } }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <Space>
          {categoryIcons[protocol.category] || <ApiOutlined />}
          <Text style={{ color: '#fff', fontWeight: 600, fontSize: 14 }}>
            {protocol.name}
          </Text>
        </Space>
        {protocol.has_identity_builder && (
          <Tooltip title="Has Identity Builder">
            <Badge status="success" />
          </Tooltip>
        )}
      </div>

      <Tag
        style={{
          fontSize: 10,
          background: getCategoryColor(protocol.category),
          border: 'none',
          color: '#fff',
          marginBottom: 8,
        }}
      >
        {protocol.category}
      </Tag>

      <Paragraph
        ellipsis={{ rows: 2 }}
        style={{ color: '#8b8fa3', fontSize: 12, marginBottom: 8, minHeight: 36 }}
      >
        {protocol.description}
      </Paragraph>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={{ color: '#6b6b8a', fontSize: 11 }}>
          Port: {formatPort(protocol.port, protocol.layer)}
        </Text>
        <Tag style={{ fontSize: 10, background: '#2d2d52', border: 'none', color: TEXT_BODY }}>
          {protocol.layer}
        </Tag>
      </div>
    </Card>
  );
};

interface VendorCardProps {
  vendor: VendorComplete;
  onClick: () => void;
}

const VendorCard: React.FC<VendorCardProps> = ({ vendor, onClick }) => {
  const category = getVendorCategory(vendor.id);

  return (
    <Card
      hoverable
      onClick={onClick}
      style={{
        background: '#0d0d1a',
        border: '1px solid #2d2d52',
        cursor: 'pointer',
      }}
      styles={{ body: { padding: '16px' } }}
    >
      <div style={{ marginBottom: 8 }}>
        <Text style={{ color: '#fff', fontWeight: 600, fontSize: 14 }}>
          {vendor.display_name}
        </Text>
      </div>

      <div style={{ marginBottom: 12 }}>
        <Text style={{ color: '#8b8fa3', fontSize: 11 }}>{category}</Text>
      </div>

      <Row gutter={8} style={{ marginBottom: 12 }}>
        <Col span={8}>
          <Statistic
            value={vendor.oui_prefixes.length}
            suffix="OUIs"
            valueStyle={{ color: '#fff', fontSize: 14 }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            value={vendor.device_types.length}
            suffix="Types"
            valueStyle={{ color: '#fff', fontSize: 14 }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            value={vendor.fingerprint_count}
            suffix="FPs"
            valueStyle={{ color: '#fff', fontSize: 14 }}
          />
        </Col>
      </Row>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {vendor.protocols.slice(0, 4).map((proto) => (
          <Tag
            key={proto}
            style={{ fontSize: 10, background: '#2d2d52', border: 'none', color: TEXT_BODY }}
          >
            {proto.replace(/_/g, ' ')}
          </Tag>
        ))}
        {vendor.protocols.length > 4 && (
          <Tag style={{ fontSize: 10, background: '#1a1a2e', border: '1px solid #2d2d52', color: '#6b6b8a' }}>
            +{vendor.protocols.length - 4}
          </Tag>
        )}
      </div>
    </Card>
  );
};

interface DeviceTemplateCardProps {
  template: DeviceTemplateSummary;
  onClick: () => void;
}

const DeviceTemplateCard: React.FC<DeviceTemplateCardProps> = ({ template, onClick }) => {
  return (
    <Card
      hoverable
      onClick={onClick}
      style={{
        background: '#0d0d1a',
        border: template.has_cves ? '1px solid rgba(245, 34, 45, 0.5)' : '1px solid #2d2d52',
        cursor: 'pointer',
      }}
      styles={{ body: { padding: '16px' } }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <Text style={{ color: '#fff', fontWeight: 600, fontSize: 14 }}>
          {template.model_name}
        </Text>
        {template.has_cves && (
          <Tooltip title={`${template.vulnerable_firmware_count} vulnerable firmware(s)`}>
            <Badge count={template.vulnerable_firmware_count} style={{ backgroundColor: '#f5222d' }}>
              <BugOutlined style={{ color: '#f5222d', fontSize: 16 }} />
            </Badge>
          </Tooltip>
        )}
      </div>

      <div style={{ marginBottom: 8 }}>
        <Tag style={{ fontSize: 10, background: '#E91E63', border: 'none', color: '#fff' }}>
          {template.vendor}
        </Tag>
        {template.vendor_family && (
          <Tag style={{ fontSize: 10, background: '#2d2d52', border: 'none', color: TEXT_BODY, marginLeft: 4 }}>
            {template.vendor_family}
          </Tag>
        )}
        <Tag style={{ fontSize: 10, background: '#1a1a2e', border: '1px solid #2d2d52', color: '#8b8fa3', marginLeft: 4 }}>
          {template.device_type.replace(/_/g, ' ')}
        </Tag>
      </div>

      <Paragraph
        ellipsis={{ rows: 2 }}
        style={{ color: '#8b8fa3', fontSize: 11, marginBottom: 8, minHeight: 32 }}
      >
        {template.description}
      </Paragraph>

      <Row gutter={8} style={{ marginBottom: 8 }}>
        <Col span={12}>
          <Text style={{ color: '#6b6b8a', fontSize: 10 }}>
            <DatabaseOutlined style={{ marginRight: 4 }} />
            {template.firmware_count} firmware(s)
          </Text>
        </Col>
        <Col span={12}>
          <Text style={{ color: '#6b6b8a', fontSize: 10 }}>
            Model: {template.model}
          </Text>
        </Col>
      </Row>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {template.supported_protocols.slice(0, 3).map((proto) => (
          <Tag
            key={proto}
            style={{ fontSize: 9, background: '#2d2d52', border: 'none', color: TEXT_BODY }}
          >
            {proto.replace(/_/g, ' ')}
          </Tag>
        ))}
        {template.supported_protocols.length > 3 && (
          <Tag style={{ fontSize: 9, background: '#1a1a2e', border: '1px solid #2d2d52', color: '#6b6b8a' }}>
            +{template.supported_protocols.length - 3}
          </Tag>
        )}
      </div>
    </Card>
  );
};

// ========== Detail Content Components ==========

interface ProtocolDetailContentProps {
  protocol: ProtocolDetail;
}

const ProtocolDetailContent: React.FC<ProtocolDetailContentProps> = ({ protocol }) => {
  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Tag
          style={{
            fontSize: 14,
            padding: '4px 12px',
            background: getCategoryColor(protocol.category),
            border: 'none',
            color: '#fff',
          }}
        >
          {protocol.category}
        </Tag>
        {protocol.has_identity_builder && (
          <Tag color="success" style={{ marginLeft: 8 }}>
            <CheckCircleOutlined /> Identity Builder
          </Tag>
        )}
      </div>

      <Paragraph style={{ color: TEXT_BODY, marginBottom: 16 }}>
        {protocol.description}
      </Paragraph>

      <Divider style={{ borderColor: BORDER_ELEVATED }} />

      <Descriptions
        column={1}
        size="small"
        labelStyle={{ color: '#8b8fa3' }}
        contentStyle={{ color: '#fff' }}
      >
        <Descriptions.Item label="Protocol ID">{protocol.id}</Descriptions.Item>
        <Descriptions.Item label="Port">{formatPort(protocol.port, protocol.layer)}</Descriptions.Item>
        <Descriptions.Item label="Layer">{protocol.layer}</Descriptions.Item>
      </Descriptions>

      {protocol.identity_fields && protocol.identity_fields.length > 0 && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            Identity Fields
          </Title>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {protocol.identity_fields.map((field) => (
              <Tag key={field} style={{ fontSize: 11, background: '#2d2d52', border: 'none', color: TEXT_BODY }}>
                {field}
              </Tag>
            ))}
          </div>
        </>
      )}

      {protocol.typical_devices.length > 0 && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            Typical Devices
          </Title>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {protocol.typical_devices.map((device) => (
              <Tag key={device} style={{ fontSize: 11 }}>
                {device.replace(/_/g, ' ')}
              </Tag>
            ))}
          </div>
        </>
      )}

      {protocol.typical_vendors.length > 0 && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            Typical Vendors
          </Title>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {protocol.typical_vendors.map((vendor) => (
              <Tag key={vendor} color="blue" style={{ fontSize: 11 }}>
                {vendor.replace(/_/g, ' ')}
              </Tag>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

interface VendorDetailContentProps {
  vendor: VendorComplete;
}

const VendorDetailContent: React.FC<VendorDetailContentProps> = ({ vendor }) => {
  const category = getVendorCategory(vendor.id);

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Tag style={{ fontSize: 14, padding: '4px 12px' }}>{category}</Tag>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Statistic
            title={<Text style={{ color: '#8b8fa3', fontSize: 11 }}>OUI Prefixes</Text>}
            value={vendor.oui_prefixes.length}
            valueStyle={{ color: '#fff', fontSize: 24 }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title={<Text style={{ color: '#8b8fa3', fontSize: 11 }}>Device Types</Text>}
            value={vendor.device_types.length}
            valueStyle={{ color: '#fff', fontSize: 24 }}
          />
        </Col>
        <Col span={8}>
          <Statistic
            title={<Text style={{ color: '#8b8fa3', fontSize: 11 }}>Fingerprints</Text>}
            value={vendor.fingerprint_count}
            valueStyle={{ color: '#fff', fontSize: 24 }}
          />
        </Col>
      </Row>

      <Divider style={{ borderColor: BORDER_ELEVATED }} />

      <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
        OUI Prefixes (MAC)
      </Title>
      <List
        size="small"
        dataSource={vendor.oui_prefixes}
        renderItem={(oui) => (
          <List.Item
            style={{
              background: '#1a1a2e',
              borderRadius: 4,
              padding: '6px 12px',
              marginBottom: 4,
              border: '1px solid #2d2d52',
            }}
          >
            <Text style={{ color: '#fff', fontFamily: 'monospace' }}>{oui}</Text>
          </List.Item>
        )}
      />

      {vendor.device_types.length > 0 && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            Device Types
          </Title>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {vendor.device_types.map((dt) => (
              <Tag key={dt} style={{ fontSize: 11 }}>
                {dt.replace(/_/g, ' ')}
              </Tag>
            ))}
          </div>
        </>
      )}

      {vendor.protocols.length > 0 && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            Protocols
          </Title>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {vendor.protocols.map((proto) => (
              <Tag key={proto} color="blue" style={{ fontSize: 11 }}>
                {proto.replace(/_/g, ' ')}
              </Tag>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

interface DeviceTemplateDetailContentProps {
  template: DeviceTemplateDetail;
}

const DeviceTemplateDetailContent: React.FC<DeviceTemplateDetailContentProps> = ({ template }) => {
  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <Tag style={{ fontSize: 14, padding: '4px 12px', background: '#E91E63', border: 'none', color: '#fff' }}>
          {template.vendor}
        </Tag>
        <Tag style={{ fontSize: 14, padding: '4px 12px', marginLeft: 8 }}>
          {template.vendor_family}
        </Tag>
        <Tag style={{ fontSize: 12, padding: '4px 8px', marginLeft: 8 }}>
          {template.device_type.replace(/_/g, ' ')}
        </Tag>
        {template.is_builtin && (
          <Tag color="green" style={{ marginLeft: 8 }}>
            Built-in
          </Tag>
        )}
      </div>

      <Paragraph style={{ color: TEXT_BODY, marginBottom: 16 }}>
        {template.description}
      </Paragraph>

      <Descriptions
        column={2}
        size="small"
        labelStyle={{ color: '#8b8fa3' }}
        contentStyle={{ color: '#fff' }}
      >
        <Descriptions.Item label="Model">{template.model}</Descriptions.Item>
        <Descriptions.Item label="Template ID">{template.id}</Descriptions.Item>
      </Descriptions>

      {/* Firmware Variants - THE KEY FEATURE */}
      <Divider style={{ borderColor: BORDER_ELEVATED }} />
      <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
        <DatabaseOutlined style={{ marginRight: 8 }} />
        Firmware Variants ({template.firmware_variants.length})
      </Title>
      <List
        size="small"
        dataSource={template.firmware_variants}
        renderItem={(fw) => (
          <List.Item
            style={{
              background: fw.cves.length > 0 ? 'rgba(245, 34, 45, 0.1)' : '#1a1a2e',
              borderRadius: 6,
              padding: '12px',
              marginBottom: 8,
              border: fw.cves.length > 0 ? '1px solid rgba(245, 34, 45, 0.3)' : '1px solid #2d2d52',
            }}
          >
            <div style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <Space>
                  <Text style={{ color: '#fff', fontWeight: 600, fontFamily: 'monospace' }}>
                    {fw.version}
                  </Text>
                  {fw.is_latest && (
                    <Tag color="green" style={{ fontSize: 10 }}>Latest</Tag>
                  )}
                  {fw.is_default && (
                    <Tag color="blue" style={{ fontSize: 10 }}>Default</Tag>
                  )}
                </Space>
                <Text style={{ color: '#6b6b8a', fontSize: 11 }}>
                  {fw.release_date}
                </Text>
              </div>

              {fw.cves.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <Space wrap size={4}>
                    <ExclamationCircleOutlined style={{ color: '#f5222d' }} />
                    {fw.cves.map((cve) => (
                      <Tag key={cve} color="error" style={{ fontSize: 10 }}>
                        {cve}
                      </Tag>
                    ))}
                  </Space>
                </div>
              )}

              {fw.notes && (
                <Text style={{ color: '#8b8fa3', fontSize: 11 }}>
                  {fw.notes}
                </Text>
              )}
            </div>
          </List.Item>
        )}
      />

      {/* Instance Rules */}
      {template.instance_rules && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            Instance Generation Rules
          </Title>
          <Descriptions
            column={1}
            size="small"
            labelStyle={{ color: '#8b8fa3' }}
            contentStyle={{ color: '#fff', fontFamily: 'monospace' }}
          >
            <Descriptions.Item label="Serial Format">{template.instance_rules.serial_format}</Descriptions.Item>
            <Descriptions.Item label="Station Name Pattern">{template.instance_rules.station_name_pattern}</Descriptions.Item>
            <Descriptions.Item label="Vendor Short">{template.instance_rules.vendor_short}</Descriptions.Item>
            <Descriptions.Item label="Model Short">{template.instance_rules.model_short}</Descriptions.Item>
          </Descriptions>
        </>
      )}

      {/* OUI Prefixes */}
      {template.oui_prefixes.length > 0 && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            OUI Prefixes
          </Title>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {template.oui_prefixes.map((oui) => (
              <Tag key={oui} style={{ fontFamily: 'monospace', fontSize: 11 }}>
                {oui}
              </Tag>
            ))}
          </div>
        </>
      )}

      {/* Supported Protocols */}
      <Divider style={{ borderColor: BORDER_ELEVATED }} />
      <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
        Supported Protocols
      </Title>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {template.supported_protocols.map((proto) => (
          <Tag key={proto} color="blue" style={{ fontSize: 11 }}>
            {proto.replace(/_/g, ' ')}
          </Tag>
        ))}
      </div>

      {/* TCP Stack */}
      {Object.keys(template.tcp_stack).length > 0 && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            TCP Stack Characteristics
          </Title>
          <pre style={{ color: TEXT_BODY, fontSize: 11, background: '#1a1a2e', padding: 12, borderRadius: 4, overflow: 'auto' }}>
            {JSON.stringify(template.tcp_stack, null, 2)}
          </pre>
        </>
      )}

      {/* Response Timing */}
      {Object.keys(template.response_timing).length > 0 && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            Response Timing
          </Title>
          <pre style={{ color: TEXT_BODY, fontSize: 11, background: '#1a1a2e', padding: 12, borderRadius: 4, overflow: 'auto' }}>
            {JSON.stringify(template.response_timing, null, 2)}
          </pre>
        </>
      )}

      {/* Protocol Identities */}
      {template.modbus_identity && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            Modbus Identity
          </Title>
          <pre style={{ color: TEXT_BODY, fontSize: 11, background: '#1a1a2e', padding: 12, borderRadius: 4, overflow: 'auto' }}>
            {JSON.stringify(template.modbus_identity, null, 2)}
          </pre>
        </>
      )}

      {template.ethernet_ip_identity && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            EtherNet/IP Identity
          </Title>
          <pre style={{ color: TEXT_BODY, fontSize: 11, background: '#1a1a2e', padding: 12, borderRadius: 4, overflow: 'auto' }}>
            {JSON.stringify(template.ethernet_ip_identity, null, 2)}
          </pre>
        </>
      )}

      {template.profinet_identity && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            PROFINET Identity
          </Title>
          <pre style={{ color: TEXT_BODY, fontSize: 11, background: '#1a1a2e', padding: 12, borderRadius: 4, overflow: 'auto' }}>
            {JSON.stringify(template.profinet_identity, null, 2)}
          </pre>
        </>
      )}

      {template.s7_identity && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            S7 Identity
          </Title>
          <pre style={{ color: TEXT_BODY, fontSize: 11, background: '#1a1a2e', padding: 12, borderRadius: 4, overflow: 'auto' }}>
            {JSON.stringify(template.s7_identity, null, 2)}
          </pre>
        </>
      )}

      {template.bacnet_identity && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            BACnet Identity
          </Title>
          <pre style={{ color: TEXT_BODY, fontSize: 11, background: '#1a1a2e', padding: 12, borderRadius: 4, overflow: 'auto' }}>
            {JSON.stringify(template.bacnet_identity, null, 2)}
          </pre>
        </>
      )}

      {template.snmp_identity && (
        <>
          <Divider style={{ borderColor: BORDER_ELEVATED }} />
          <Title level={5} style={{ color: '#fff', marginBottom: 12 }}>
            SNMP Identity
          </Title>
          <pre style={{ color: TEXT_BODY, fontSize: 11, background: '#1a1a2e', padding: 12, borderRadius: 4, overflow: 'auto' }}>
            {JSON.stringify(template.snmp_identity, null, 2)}
          </pre>
        </>
      )}
    </div>
  );
};

export default FingerprintingLibraryPage;
