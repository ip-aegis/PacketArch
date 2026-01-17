/**
 * Device Library Page - Browse and manage device profiles
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
  Pagination,
  Empty,
  Spin,
  Button,
  Tooltip,
  Badge,
  Drawer,
  Descriptions,
  Divider,
  message,
  Modal,
  Form,
  InputNumber,
  Collapse,
  App,
} from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  CopyOutlined,
  EyeOutlined,
  ClockCircleOutlined,
  ApiOutlined,
  ControlOutlined,
  DesktopOutlined,
  CloudServerOutlined,
  ThunderboltOutlined,
  DashboardOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  DatabaseOutlined,
  NodeIndexOutlined,
  GlobalOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { devicesApi, type DeviceProfileFilters } from '../api/devices';
import type { DeviceProfile, DeviceProfileCreate, DeviceType, ProtocolType, VerticalType } from '../types';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// Device type icons and colors
const deviceTypeConfig: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  plc: { icon: <ControlOutlined />, color: '#049FD9', label: 'PLC' },
  hmi: { icon: <DesktopOutlined />, color: '#6CC04A', label: 'HMI' },
  rtu: { icon: <CloudServerOutlined />, color: '#FBAB18', label: 'RTU' },
  drive: { icon: <ThunderboltOutlined />, color: '#FF7043', label: 'Drive' },
  sensor: { icon: <DashboardOutlined />, color: '#00BCEB', label: 'Sensor' },
  relay: { icon: <SafetyCertificateOutlined />, color: '#E53935', label: 'Relay' },
  ews: { icon: <SettingOutlined />, color: '#9C27B0', label: 'EWS' },
  historian: { icon: <DatabaseOutlined />, color: '#607D8B', label: 'Historian' },
  network: { icon: <NodeIndexOutlined />, color: '#00BCD4', label: 'Network' },
  gateway: { icon: <GlobalOutlined />, color: '#795548', label: 'Gateway' },
};

// Protocol colors
const protocolColors: Record<string, string> = {
  modbus_tcp: '#049FD9',
  ethernet_ip: '#6CC04A',
  profinet: '#FBAB18',
  opc_ua: '#9C27B0',
  dnp3: '#FF5722',
  iec104: '#E91E63',
  bacnet: '#00BCD4',
};

// Vertical colors
const verticalColors: Record<string, string> = {
  manufacturing: '#6CC04A',
  water_wastewater: '#00BCEB',
  energy_power: '#FBAB18',
  oil_gas: '#FF7043',
  transportation: '#9C27B0',
  building_automation: '#00BCD4',
};

const DeviceLibraryPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { modal, message: antMessage } = App.useApp();
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [filters, setFilters] = useState<DeviceProfileFilters>({
    page: 1,
    page_size: 12,
  });
  const [selectedDevice, setSelectedDevice] = useState<DeviceProfile | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createForm] = Form.useForm();

  // Fetch device profiles
  const { data, isLoading, error } = useQuery({
    queryKey: ['deviceProfiles', filters],
    queryFn: () => devicesApi.list(filters),
  });

  // Duplicate mutation
  const duplicateMutation = useMutation({
    mutationFn: (id: string) => devicesApi.duplicate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deviceProfiles'] });
      antMessage.success('Device profile duplicated successfully');
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail || error.message || 'Unknown error';
      antMessage.error(`Failed to duplicate device profile: ${detail}`);
    },
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: DeviceProfileCreate) => devicesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deviceProfiles'] });
      antMessage.success('Device profile created successfully');
      setCreateModalOpen(false);
      createForm.resetFields();
    },
    onError: (error: any) => {
      const detail = error.response?.data?.detail || error.message || 'Unknown error';
      antMessage.error(`Failed to create device profile: ${detail}`);
    },
  });

  const handleFilterChange = (key: keyof DeviceProfileFilters, value: string | undefined) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value || undefined,
      page: 1, // Reset to first page on filter change
    }));
  };

  const handlePageChange = (page: number, pageSize: number) => {
    setFilters((prev) => ({
      ...prev,
      page,
      page_size: pageSize,
    }));
  };

  const handleViewDevice = (device: DeviceProfile) => {
    setSelectedDevice(device);
    setDrawerOpen(true);
  };

  const handleDuplicate = (id: string) => {
    duplicateMutation.mutate(id);
  };

  const handleCreateDevice = (values: any) => {
    const data: DeviceProfileCreate = {
      name: values.name,
      device_type: values.device_type,
      role: values.role,
      description: values.description,
      supported_protocols: values.supported_protocols,
      vertical_hints: values.vertical_hints,
      timing_model: values.timing_model ? {
        polling_interval_ms: values.timing_model.polling_interval_ms || 1000,
        jitter_type: values.timing_model.jitter_type || 'uniform',
        jitter_min_ms: values.timing_model.jitter_min_ms || 0,
        jitter_max_ms: values.timing_model.jitter_max_ms || 100,
        burst_enabled: values.timing_model.burst_enabled || false,
      } : undefined,
    };
    createMutation.mutate(data);
  };

  const getDeviceTypeConfig = (type: string) => {
    return deviceTypeConfig[type] || { icon: <ControlOutlined />, color: '#6b6b8a', label: type };
  };

  const renderDeviceCard = (device: DeviceProfile) => {
    const typeConfig = getDeviceTypeConfig(device.device_type);

    return (
      <Card
        key={device.id}
        hoverable
        style={{
          background: '#141428',
          border: '1px solid #2d2d52',
          borderRadius: 12,
        }}
        bodyStyle={{ padding: 20 }}
        onClick={() => handleViewDevice(device)}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 10,
                background: `linear-gradient(135deg, ${typeConfig.color}20 0%, ${typeConfig.color}10 100%)`,
                border: `1px solid ${typeConfig.color}40`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: typeConfig.color,
                fontSize: 20,
              }}
            >
              {typeConfig.icon}
            </div>
            <div>
              <Text strong style={{ color: '#fff', fontSize: 15, display: 'block' }}>
                {device.name}
              </Text>
              <Tag
                style={{
                  background: `${typeConfig.color}20`,
                  border: `1px solid ${typeConfig.color}40`,
                  color: typeConfig.color,
                  marginTop: 4,
                  fontSize: 11,
                }}
              >
                {typeConfig.label}
              </Tag>
            </div>
          </div>
          {device.is_builtin && (
            <Tooltip title="Built-in profile">
              <Badge
                count="SYSTEM"
                style={{
                  background: '#2d2d52',
                  color: '#6b6b8a',
                  fontSize: 9,
                  fontWeight: 600,
                }}
              />
            </Tooltip>
          )}
        </div>

        {/* Description */}
        {device.description && (
          <Paragraph
            ellipsis={{ rows: 2 }}
            style={{ color: '#a8a8c0', fontSize: 13, marginBottom: 16, minHeight: 40 }}
          >
            {device.description}
          </Paragraph>
        )}

        {/* Protocols */}
        <div style={{ marginBottom: 16 }}>
          <Text style={{ color: '#6b6b8a', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Protocols
          </Text>
          <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {device.supported_protocols?.slice(0, 3).map((protocol) => (
              <Tag
                key={protocol}
                style={{
                  background: `${protocolColors[protocol] || '#6b6b8a'}15`,
                  border: `1px solid ${protocolColors[protocol] || '#6b6b8a'}30`,
                  color: protocolColors[protocol] || '#6b6b8a',
                  fontSize: 10,
                  textTransform: 'uppercase',
                }}
              >
                {protocol.replace('_', ' ')}
              </Tag>
            ))}
            {(device.supported_protocols?.length || 0) > 3 && (
              <Tag style={{ background: '#2d2d52', border: 'none', color: '#6b6b8a', fontSize: 10 }}>
                +{(device.supported_protocols?.length || 0) - 3}
              </Tag>
            )}
          </div>
        </div>

        {/* Verticals */}
        {device.vertical_hints && device.vertical_hints.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Text style={{ color: '#6b6b8a', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Verticals
            </Text>
            <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {device.vertical_hints.slice(0, 2).map((vertical) => (
                <Tag
                  key={vertical}
                  style={{
                    background: `${verticalColors[vertical] || '#6b6b8a'}15`,
                    border: `1px solid ${verticalColors[vertical] || '#6b6b8a'}30`,
                    color: verticalColors[vertical] || '#6b6b8a',
                    fontSize: 10,
                  }}
                >
                  {vertical.replace('_', ' ')}
                </Tag>
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', gap: 8, borderTop: '1px solid #2d2d52', paddingTop: 12 }}>
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            style={{ color: '#a8a8c0', flex: 1 }}
            onClick={(e) => {
              e.stopPropagation();
              handleViewDevice(device);
            }}
          >
            View
          </Button>
          <Button
            type="text"
            size="small"
            icon={<CopyOutlined />}
            style={{ color: '#a8a8c0', flex: 1 }}
            onClick={(e) => {
              e.stopPropagation();
              handleDuplicate(device.id);
            }}
            loading={duplicateMutation.isPending}
          >
            Clone
          </Button>
        </div>
      </Card>
    );
  };

  const renderDeviceDrawer = () => {
    if (!selectedDevice) return null;

    const typeConfig = getDeviceTypeConfig(selectedDevice.device_type);

    return (
      <Drawer
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 8,
                background: `linear-gradient(135deg, ${typeConfig.color}20 0%, ${typeConfig.color}10 100%)`,
                border: `1px solid ${typeConfig.color}40`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: typeConfig.color,
                fontSize: 18,
              }}
            >
              {typeConfig.icon}
            </div>
            <div>
              <Text strong style={{ color: '#fff', fontSize: 16, display: 'block' }}>
                {selectedDevice.name}
              </Text>
              <Text style={{ color: '#6b6b8a', fontSize: 12 }}>{typeConfig.label}</Text>
            </div>
          </div>
        }
        placement="right"
        width={500}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        styles={{
          header: { background: '#141428', borderBottom: '1px solid #2d2d52' },
          body: { background: '#1a1a2e', padding: 24 },
        }}
      >
        {/* Description */}
        {selectedDevice.description && (
          <div style={{ marginBottom: 24 }}>
            <Text style={{ color: '#6b6b8a', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Description
            </Text>
            <Paragraph style={{ color: '#a8a8c0', marginTop: 8 }}>{selectedDevice.description}</Paragraph>
          </div>
        )}

        {/* Role */}
        {selectedDevice.role && (
          <div style={{ marginBottom: 24 }}>
            <Text style={{ color: '#6b6b8a', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Role
            </Text>
            <Text style={{ color: '#fff', display: 'block', marginTop: 8 }}>{selectedDevice.role}</Text>
          </div>
        )}

        <Divider style={{ borderColor: '#2d2d52' }} />

        {/* Supported Protocols */}
        <div style={{ marginBottom: 24 }}>
          <Text style={{ color: '#6b6b8a', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Supported Protocols
          </Text>
          <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {selectedDevice.supported_protocols?.map((protocol) => (
              <Tag
                key={protocol}
                style={{
                  background: `${protocolColors[protocol] || '#6b6b8a'}15`,
                  border: `1px solid ${protocolColors[protocol] || '#6b6b8a'}30`,
                  color: protocolColors[protocol] || '#6b6b8a',
                  padding: '4px 12px',
                  fontSize: 12,
                  textTransform: 'uppercase',
                }}
              >
                {protocol.replace('_', ' ')}
              </Tag>
            )) || <Text style={{ color: '#6b6b8a' }}>None specified</Text>}
          </div>
        </div>

        {/* Vertical Hints */}
        {selectedDevice.vertical_hints && selectedDevice.vertical_hints.length > 0 && (
          <div style={{ marginBottom: 24 }}>
            <Text style={{ color: '#6b6b8a', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Industry Verticals
            </Text>
            <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {selectedDevice.vertical_hints.map((vertical) => (
                <Tag
                  key={vertical}
                  style={{
                    background: `${verticalColors[vertical] || '#6b6b8a'}15`,
                    border: `1px solid ${verticalColors[vertical] || '#6b6b8a'}30`,
                    color: verticalColors[vertical] || '#6b6b8a',
                    padding: '4px 12px',
                    fontSize: 12,
                  }}
                >
                  {vertical.replace('_', ' ')}
                </Tag>
              ))}
            </div>
          </div>
        )}

        <Divider style={{ borderColor: '#2d2d52' }} />

        {/* Timing Model */}
        {selectedDevice.timing_model && (
          <div style={{ marginBottom: 24 }}>
            <Text style={{ color: '#6b6b8a', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Timing Model
            </Text>
            <Card
              size="small"
              style={{
                background: '#141428',
                border: '1px solid #2d2d52',
                marginTop: 12,
              }}
            >
              <Descriptions column={2} size="small" labelStyle={{ color: '#6b6b8a' }} contentStyle={{ color: '#a8a8c0' }}>
                <Descriptions.Item label="Polling Interval">
                  {selectedDevice.timing_model.polling_interval_ms}ms
                </Descriptions.Item>
                <Descriptions.Item label="Jitter Type">{selectedDevice.timing_model.jitter_type}</Descriptions.Item>
                <Descriptions.Item label="Jitter Min">{selectedDevice.timing_model.jitter_min_ms}ms</Descriptions.Item>
                <Descriptions.Item label="Jitter Max">{selectedDevice.timing_model.jitter_max_ms}ms</Descriptions.Item>
                {selectedDevice.timing_model.burst_enabled && (
                  <>
                    <Descriptions.Item label="Burst Size">
                      {selectedDevice.timing_model.burst_size || 'N/A'}
                    </Descriptions.Item>
                    <Descriptions.Item label="Burst Interval">
                      {selectedDevice.timing_model.burst_interval_ms || 'N/A'}ms
                    </Descriptions.Item>
                  </>
                )}
              </Descriptions>
            </Card>
          </div>
        )}

        {/* Vendor Fingerprint */}
        {selectedDevice.vendor_fingerprint && (
          <div style={{ marginBottom: 24 }}>
            <Text style={{ color: '#6b6b8a', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Vendor Fingerprint
            </Text>
            <Card
              size="small"
              style={{
                background: '#141428',
                border: '1px solid #2d2d52',
                marginTop: 12,
              }}
            >
              <Descriptions column={1} size="small" labelStyle={{ color: '#6b6b8a' }} contentStyle={{ color: '#a8a8c0' }}>
                <Descriptions.Item label="Vendor Family">
                  {selectedDevice.vendor_fingerprint.vendor_family}
                </Descriptions.Item>
                <Descriptions.Item label="OUI Prefix">{selectedDevice.vendor_fingerprint.oui_prefix}</Descriptions.Item>
                <Descriptions.Item label="Response Time">
                  {selectedDevice.vendor_fingerprint.response_time_min_ms}-
                  {selectedDevice.vendor_fingerprint.response_time_max_ms}ms
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </div>
        )}

        {/* Metadata */}
        <Divider style={{ borderColor: '#2d2d52' }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#6b6b8a', fontSize: 12 }}>
          <ClockCircleOutlined />
          <span>Created {new Date(selectedDevice.created_at).toLocaleDateString()}</span>
          {selectedDevice.is_builtin && (
            <>
              <span style={{ margin: '0 8px' }}>|</span>
              <Badge count="SYSTEM" style={{ background: '#2d2d52', color: '#6b6b8a', fontSize: 9 }} />
            </>
          )}
        </div>
      </Drawer>
    );
  };

  return (
    <div>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <Title level={3} style={{ color: '#fff', margin: 0 }}>
            Device Library
          </Title>
          <Text style={{ color: '#6b6b8a' }}>
            Browse and manage device profiles for your OT traffic simulations
          </Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
          Create Device
        </Button>
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
              placeholder="Search devices..."
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
              placeholder="Device Type"
              allowClear
              value={filters.device_type}
              onChange={(value) => handleFilterChange('device_type', value)}
              style={{ width: 150 }}
              popupClassName="dark-dropdown"
            >
              {Object.entries(deviceTypeConfig).map(([key, config]) => (
                <Option key={key} value={key}>
                  <Space>
                    {config.icon}
                    {config.label}
                  </Space>
                </Option>
              ))}
            </Select>
          </Col>
          <Col>
            <Select
              placeholder="Protocol"
              allowClear
              value={filters.protocol}
              onChange={(value) => handleFilterChange('protocol', value)}
              style={{ width: 150 }}
              popupClassName="dark-dropdown"
            >
              <Option value="modbus_tcp">Modbus TCP</Option>
              <Option value="ethernet_ip">EtherNet/IP</Option>
              <Option value="profinet">PROFINET</Option>
              <Option value="opc_ua">OPC UA</Option>
              <Option value="dnp3">DNP3</Option>
            </Select>
          </Col>
          <Col>
            <Select
              placeholder="Vertical"
              allowClear
              value={filters.vertical}
              onChange={(value) => handleFilterChange('vertical', value)}
              style={{ width: 150 }}
              popupClassName="dark-dropdown"
            >
              <Option value="manufacturing">Manufacturing</Option>
              <Option value="water_wastewater">Water/Wastewater</Option>
              <Option value="energy_power">Energy/Power</Option>
              <Option value="oil_gas">Oil & Gas</Option>
            </Select>
          </Col>
          <Col>
            <Space.Compact>
              <Button
                icon={<AppstoreOutlined />}
                type={viewMode === 'grid' ? 'primary' : 'default'}
                onClick={() => setViewMode('grid')}
              />
              <Button
                icon={<UnorderedListOutlined />}
                type={viewMode === 'list' ? 'primary' : 'default'}
                onClick={() => setViewMode('list')}
              />
            </Space.Compact>
          </Col>
        </Row>
      </Card>

      {/* Results */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#6b6b8a' }}>Loading device profiles...</div>
        </div>
      ) : error ? (
        <Card style={{ background: '#141428', border: '1px solid #2d2d52' }}>
          <Empty
            description={<Text style={{ color: '#6b6b8a' }}>Failed to load device profiles</Text>}
          />
        </Card>
      ) : data?.items.length === 0 ? (
        <Card style={{ background: '#141428', border: '1px solid #2d2d52' }}>
          <Empty
            description={<Text style={{ color: '#6b6b8a' }}>No device profiles found</Text>}
          />
        </Card>
      ) : (
        <>
          {/* Stats */}
          <div style={{ marginBottom: 16, color: '#6b6b8a', fontSize: 13 }}>
            Showing {data?.items.length} of {data?.total} device profiles
          </div>

          {/* Grid View */}
          <Row gutter={[16, 16]}>
            {data?.items.map((device) => (
              <Col key={device.id} xs={24} sm={12} lg={8} xl={6}>
                {renderDeviceCard(device)}
              </Col>
            ))}
          </Row>

          {/* Pagination */}
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
        </>
      )}

      {/* Device Detail Drawer */}
      {renderDeviceDrawer()}

      {/* Create Device Modal */}
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
            <span style={{ color: '#fff', fontSize: 16 }}>Create Device Profile</span>
          </div>
        }
        open={createModalOpen}
        onCancel={() => {
          setCreateModalOpen(false);
          createForm.resetFields();
        }}
        footer={null}
        width={700}
        styles={{
          header: { background: '#141428', borderBottom: '1px solid #2d2d52' },
          body: { background: '#1a1a2e', padding: 24 },
          content: { background: '#141428' },
        }}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateDevice}
          initialValues={{
            timing_model: {
              polling_interval_ms: 1000,
              jitter_type: 'uniform',
              jitter_min_ms: 0,
              jitter_max_ms: 100,
            },
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label={<Text style={{ color: '#a8a8c0' }}>Device Name</Text>}
                rules={[{ required: true, message: 'Please enter a device name' }]}
              >
                <Input placeholder="My Custom PLC" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="device_type"
                label={<Text style={{ color: '#a8a8c0' }}>Device Type</Text>}
                rules={[{ required: true, message: 'Please select a device type' }]}
              >
                <Select placeholder="Select device type">
                  {Object.entries(deviceTypeConfig).map(([key, config]) => (
                    <Option key={key} value={key}>
                      <Space>
                        {config.icon}
                        {config.label}
                      </Space>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="role"
            label={<Text style={{ color: '#a8a8c0' }}>Role / Function</Text>}
          >
            <Input placeholder="e.g., Primary process controller" />
          </Form.Item>

          <Form.Item
            name="description"
            label={<Text style={{ color: '#a8a8c0' }}>Description</Text>}
          >
            <Input.TextArea rows={2} placeholder="Describe this device profile..." />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="supported_protocols"
                label={<Text style={{ color: '#a8a8c0' }}>Supported Protocols</Text>}
              >
                <Select mode="multiple" placeholder="Select protocols">
                  <Option value="modbus_tcp">Modbus TCP</Option>
                  <Option value="ethernet_ip">EtherNet/IP</Option>
                  <Option value="profinet">PROFINET</Option>
                  <Option value="opc_ua">OPC UA</Option>
                  <Option value="dnp3">DNP3</Option>
                  <Option value="iec104">IEC 104</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="vertical_hints"
                label={<Text style={{ color: '#a8a8c0' }}>Industry Verticals</Text>}
              >
                <Select mode="multiple" placeholder="Select verticals">
                  <Option value="manufacturing">Manufacturing</Option>
                  <Option value="water_wastewater">Water/Wastewater</Option>
                  <Option value="energy_power">Energy/Power</Option>
                  <Option value="oil_gas">Oil & Gas</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Collapse
            ghost
            items={[
              {
                key: 'timing',
                label: <Text style={{ color: '#a8a8c0' }}>Timing Model (Advanced)</Text>,
                children: (
                  <Row gutter={16}>
                    <Col span={12}>
                      <Form.Item
                        name={['timing_model', 'polling_interval_ms']}
                        label={<Text style={{ color: '#6b6b8a' }}>Polling Interval (ms)</Text>}
                      >
                        <InputNumber min={10} max={60000} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name={['timing_model', 'jitter_type']}
                        label={<Text style={{ color: '#6b6b8a' }}>Jitter Type</Text>}
                      >
                        <Select>
                          <Option value="uniform">Uniform</Option>
                          <Option value="normal">Normal</Option>
                          <Option value="none">None</Option>
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name={['timing_model', 'jitter_min_ms']}
                        label={<Text style={{ color: '#6b6b8a' }}>Jitter Min (ms)</Text>}
                      >
                        <InputNumber min={0} max={10000} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        name={['timing_model', 'jitter_max_ms']}
                        label={<Text style={{ color: '#6b6b8a' }}>Jitter Max (ms)</Text>}
                      >
                        <InputNumber min={0} max={10000} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>
                ),
              },
            ]}
          />

          <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setCreateModalOpen(false)}>Cancel</Button>
              <Button type="primary" htmlType="submit" loading={createMutation.isPending}>
                Create Device
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DeviceLibraryPage;
