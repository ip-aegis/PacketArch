/**
 * Realistic Settings Panel - Shows fingerprint and error injection options
 * for the selected device, plus links to PCAP learning
 */

import React, { useEffect, useState } from 'react';
import {
  Typography,
  Empty,
  Card,
  Select,
  Slider,
  Switch,
  Space,
  Tag,
  Button,
  Spin,
  Tooltip,
  Divider,
  Alert,
} from 'antd';
import {
  ExperimentOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
  InfoCircleOutlined,
  UploadOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useUIStore } from '../../stores/uiStore';
import { useScenarioStore } from '../../stores/scenarioStore';
import {
  getFingerprintDetail,
  getDeviceErrorConfig,
  type FingerprintDetail,
  type ErrorConfig,
} from '../../api/fingerprints';
import { useVendorData } from '../../hooks/useVendorData';

const { Text, Title } = Typography;

interface RealisticSettingsPanelProps {
  scenarioId: string | null;
  onOpenPcapLearning?: () => void;
}

const RealisticSettingsPanel: React.FC<RealisticSettingsPanelProps> = ({
  scenarioId,
  onOpenPcapLearning,
}) => {
  const activePropertyContext = useUIStore((state) => state.activePropertyContext);
  const device = useScenarioStore((state) =>
    activePropertyContext.type === 'device' && activePropertyContext.ids[0]
      ? state.devices[activePropertyContext.ids[0]]
      : null
  );
  const updateDevice = useScenarioStore((state) => state.updateDevice);

  // Vendor/model data from shared hook
  const {
    vendors,
    models,
    loadingModels,
    handleVendorChange: hookVendorChange,
  } = useVendorData();

  // Fingerprint detail and error injection (component-specific)
  const [fingerprintDetail, setFingerprintDetail] = useState<FingerprintDetail | null>(null);
  const [errorConfig, setErrorConfig] = useState<ErrorConfig | null>(null);
  const [loading, setLoading] = useState(false);

  // Local state for error injection
  const [errorInjectionEnabled, setErrorInjectionEnabled] = useState(false);
  const [exceptionRate, setExceptionRate] = useState(0.001);
  const [timeoutRate, setTimeoutRate] = useState(0.0005);

  // Load default error config when device type changes
  useEffect(() => {
    if (device?.type) {
      const fetchErrorConfig = async () => {
        try {
          const config = await getDeviceErrorConfig(device.type);
          setErrorConfig(config);
          setExceptionRate(config.exception_rate);
          setTimeoutRate(config.timeout_rate);
        } catch (err) {
          console.error('Failed to fetch error config:', err);
        }
      };
      fetchErrorConfig();
    }
  }, [device?.type]);

  // Vendor change: delegate to hook + reset fingerprint
  const handleVendorChange = async (vendor: string) => {
    setFingerprintDetail(null);
    await hookVendorChange(vendor);
  };

  // Fetch fingerprint detail when model changes
  const handleModelChange = async (model: string, vendor: string) => {
    setLoading(true);
    try {
      const detail = await getFingerprintDetail(vendor, model);
      setFingerprintDetail(detail);

      // Update device with fingerprint info
      if (device) {
        updateDevice(device.id, {
          vendor: vendor,
          fingerprintModel: model,
        });
      }
    } catch (err) {
      console.error('Failed to fetch fingerprint detail:', err);
    } finally {
      setLoading(false);
    }
  };

  // Toggle error injection
  const handleErrorInjectionToggle = (enabled: boolean) => {
    setErrorInjectionEnabled(enabled);
    if (device) {
      updateDevice(device.id, {
        errorConfig: enabled
          ? { exceptionRate, timeoutRate }
          : undefined,
      });
    }
  };

  // Update error rates
  const handleExceptionRateChange = (value: number) => {
    setExceptionRate(value);
    if (errorInjectionEnabled && device) {
      updateDevice(device.id, {
        errorConfig: { exceptionRate: value, timeoutRate },
      });
    }
  };

  const handleTimeoutRateChange = (value: number) => {
    setTimeoutRate(value);
    if (errorInjectionEnabled && device) {
      updateDevice(device.id, {
        errorConfig: { exceptionRate, timeoutRate: value },
      });
    }
  };

  // No selection state
  if (!activePropertyContext.type || activePropertyContext.ids.length === 0) {
    return (
      <div style={{ padding: '16px', height: '100%', overflowY: 'auto' }}>
        <Empty
          image={<ExperimentOutlined style={{ fontSize: 48, color: '#4a6a8a' }} />}
          description={
            <div>
              <Text style={{ fontSize: '13px', color: '#8aa4bc' }}>
                No device selected
              </Text>
              <div style={{ marginTop: '8px' }}>
                <Text style={{ fontSize: '11px', color: '#6a8caf' }}>
                  Select a device to configure realism settings like vendor
                  fingerprints and error injection
                </Text>
              </div>
            </div>
          }
          style={{ marginTop: '60px' }}
        />

        {/* Global PCAP Learning Link */}
        <Card
          size="small"
          style={{ background: '#1a2734', marginTop: 24 }}
          styles={{ body: { padding: '12px' } }}
        >
          <Space direction="vertical" style={{ width: '100%' }}>
            <Text strong style={{ fontSize: '12px', color: '#8aa4bc' }}>
              <UploadOutlined /> Learn from PCAP
            </Text>
            <Text style={{ fontSize: '11px', color: '#6a8caf' }}>
              Upload real network captures to learn timing patterns and
              apply them to your scenarios.
            </Text>
            <Button
              type="primary"
              ghost
              size="small"
              icon={<UploadOutlined />}
              onClick={onOpenPcapLearning}
              style={{ marginTop: 8 }}
            >
              Open PCAP Learning
            </Button>
          </Space>
        </Card>
      </div>
    );
  }

  // Non-device selection
  if (activePropertyContext.type !== 'device') {
    return (
      <div style={{ padding: '16px', height: '100%', overflowY: 'auto' }}>
        <Empty
          image={<ExperimentOutlined style={{ fontSize: 48, color: '#4a6a8a' }} />}
          description={
            <Text style={{ fontSize: '13px', color: '#8aa4bc' }}>
              Realism settings only apply to devices
            </Text>
          }
          style={{ marginTop: '60px' }}
        />
      </div>
    );
  }

  // Multi-selection
  if (activePropertyContext.ids.length > 1) {
    return (
      <div style={{ padding: '16px', height: '100%', overflowY: 'auto' }}>
        <Empty
          description={
            <Text style={{ fontSize: '13px', color: '#8aa4bc' }}>
              Select a single device for realism settings
            </Text>
          }
          style={{ marginTop: '60px' }}
        />
      </div>
    );
  }

  if (!device) {
    return (
      <div style={{ padding: '16px', height: '100%' }}>
        <Spin />
      </div>
    );
  }

  return (
    <div
      style={{
        padding: '16px',
        height: '100%',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}
    >
      {/* Device Header */}
      <div>
        <Title level={5} style={{ color: '#c9d1d9', marginBottom: 4, fontSize: 14 }}>
          {device.name}
        </Title>
        <Space size={4}>
          <Tag color="blue">{device.type.toUpperCase()}</Tag>
          {device.protocols?.map((p) => (
            <Tag key={p} color="cyan" style={{ fontSize: 10 }}>
              {p}
            </Tag>
          ))}
        </Space>
      </div>

      {/* Vendor Fingerprint Section */}
      <Card
        size="small"
        title={
          <Space>
            <SafetyCertificateOutlined />
            <span>Vendor Fingerprint</span>
            <Tooltip title="Apply authentic vendor identity data for hyper-realistic traffic">
              <InfoCircleOutlined style={{ color: '#6a8caf' }} />
            </Tooltip>
          </Space>
        }
        style={{ background: '#1a2734' }}
        styles={{ body: { padding: '12px' } }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          <div>
            <Text style={{ fontSize: '11px', color: '#6a8caf', display: 'block', marginBottom: 4 }}>
              Vendor
            </Text>
            <Select
              placeholder="Select vendor"
              style={{ width: '100%' }}
              size="small"
              onChange={handleVendorChange}
              options={vendors.map((v) => ({
                value: v.vendor,
                label: (
                  <Space>
                    <span>{v.display_name}</span>
                    <Tag style={{ fontSize: 9 }}>{v.fingerprint_count} models</Tag>
                  </Space>
                ),
              }))}
            />
          </div>

          <div>
            <Text style={{ fontSize: '11px', color: '#6a8caf', display: 'block', marginBottom: 4 }}>
              Model
            </Text>
            <Select
              placeholder={loadingModels ? 'Loading...' : 'Select model'}
              style={{ width: '100%' }}
              size="small"
              disabled={models.length === 0}
              loading={loadingModels}
              onChange={(model) => {
                const vendor = vendors.find((v) => models.includes(model))?.vendor;
                if (vendor) handleModelChange(model, vendor);
              }}
              options={models.map((m) => ({ value: m, label: m }))}
            />
          </div>

          {/* Fingerprint Details */}
          {loading ? (
            <div style={{ textAlign: 'center', padding: 16 }}>
              <Spin size="small" />
            </div>
          ) : fingerprintDetail ? (
            <div
              style={{
                background: '#0d1117',
                borderRadius: 4,
                padding: 8,
                marginTop: 8,
              }}
            >
              <Text style={{ fontSize: '10px', color: '#6a8caf', display: 'block' }}>
                Applied Fingerprint
              </Text>
              <Space direction="vertical" size={2} style={{ marginTop: 4 }}>
                <Text style={{ fontSize: '11px', color: '#c9d1d9' }}>
                  {fingerprintDetail.vendor} {fingerprintDetail.model}
                </Text>
                {fingerprintDetail.firmware_version && (
                  <Text style={{ fontSize: '10px', color: '#6a8caf' }}>
                    FW: {fingerprintDetail.firmware_version}
                  </Text>
                )}
                <Space size={4} wrap>
                  {fingerprintDetail.oui_prefixes.slice(0, 2).map((oui) => (
                    <Tag key={oui} style={{ fontSize: 9 }}>
                      OUI: {oui}
                    </Tag>
                  ))}
                </Space>
                <Space size={4} wrap style={{ marginTop: 4 }}>
                  {fingerprintDetail.modbus_identity && (
                    <Tag color="green" style={{ fontSize: 9 }}>Modbus</Tag>
                  )}
                  {fingerprintDetail.ethernet_ip_identity && (
                    <Tag color="purple" style={{ fontSize: 9 }}>EtherNet/IP</Tag>
                  )}
                  {fingerprintDetail.profinet_identity && (
                    <Tag color="orange" style={{ fontSize: 9 }}>PROFINET</Tag>
                  )}
                </Space>
              </Space>
            </div>
          ) : (
            <Alert
              message="No fingerprint applied"
              description="Select a vendor and model to apply realistic identity data"
              type="info"
              showIcon
              style={{ fontSize: 11 }}
            />
          )}
        </Space>
      </Card>

      {/* Error Injection Section */}
      <Card
        size="small"
        title={
          <Space>
            <ThunderboltOutlined />
            <span>Error Injection</span>
            <Tooltip title="Simulate realistic protocol exceptions and timeouts">
              <InfoCircleOutlined style={{ color: '#6a8caf' }} />
            </Tooltip>
          </Space>
        }
        style={{ background: '#1a2734' }}
        styles={{ body: { padding: '12px' } }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text style={{ fontSize: '11px', color: '#8aa4bc' }}>
              Enable Error Injection
            </Text>
            <Switch
              size="small"
              checked={errorInjectionEnabled}
              onChange={handleErrorInjectionToggle}
            />
          </div>

          {errorInjectionEnabled && (
            <>
              <Divider style={{ margin: '8px 0', borderColor: '#2a3f54' }} />

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text style={{ fontSize: '11px', color: '#6a8caf' }}>
                    Exception Rate
                  </Text>
                  <Text style={{ fontSize: '10px', color: '#8aa4bc' }}>
                    {(exceptionRate * 100).toFixed(2)}%
                  </Text>
                </div>
                <Slider
                  min={0}
                  max={0.05}
                  step={0.0001}
                  value={exceptionRate}
                  onChange={handleExceptionRateChange}
                  tooltip={{ formatter: (v) => `${((v ?? 0) * 100).toFixed(2)}%` }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Text style={{ fontSize: '11px', color: '#6a8caf' }}>
                    Timeout Rate
                  </Text>
                  <Text style={{ fontSize: '10px', color: '#8aa4bc' }}>
                    {(timeoutRate * 100).toFixed(2)}%
                  </Text>
                </div>
                <Slider
                  min={0}
                  max={0.02}
                  step={0.0001}
                  value={timeoutRate}
                  onChange={handleTimeoutRateChange}
                  tooltip={{ formatter: (v) => `${((v ?? 0) * 100).toFixed(2)}%` }}
                />
              </div>

              {errorConfig && (
                <Alert
                  message={
                    <Text style={{ fontSize: '10px' }}>
                      Default for {device.type}: {(errorConfig.exception_rate * 100).toFixed(2)}% exceptions,{' '}
                      {(errorConfig.timeout_rate * 100).toFixed(2)}% timeouts
                    </Text>
                  }
                  type="info"
                  icon={<InfoCircleOutlined />}
                  showIcon
                  style={{ padding: '4px 8px' }}
                />
              )}
            </>
          )}
        </Space>
      </Card>

      {/* PCAP Learning Link */}
      <Card
        size="small"
        title={
          <Space>
            <UploadOutlined />
            <span>Learned Patterns</span>
          </Space>
        }
        style={{ background: '#1a2734' }}
        styles={{ body: { padding: '12px' } }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text style={{ fontSize: '11px', color: '#6a8caf' }}>
            Apply timing patterns learned from real PCAP captures to make this
            device's traffic more realistic.
          </Text>
          <Button
            type="primary"
            ghost
            size="small"
            icon={<UploadOutlined />}
            onClick={onOpenPcapLearning}
            style={{ marginTop: 8 }}
          >
            Upload PCAP for {device.protocols?.[0] || 'protocol'}
          </Button>
        </Space>
      </Card>

      {/* Realism Checklist */}
      <Card
        size="small"
        title={
          <Space>
            <WarningOutlined />
            <span>Realism Checklist</span>
          </Space>
        }
        style={{ background: '#1a2734' }}
        styles={{ body: { padding: '12px' } }}
      >
        <Space direction="vertical" size={4}>
          <RealisticCheckItem
            checked={!!fingerprintDetail}
            label="Vendor fingerprint applied"
          />
          <RealisticCheckItem
            checked={errorInjectionEnabled}
            label="Error injection configured"
          />
          <RealisticCheckItem
            checked={false}
            label="Timing patterns learned"
          />
        </Space>
      </Card>
    </div>
  );
};

// Helper component for checklist items
const RealisticCheckItem: React.FC<{ checked: boolean; label: string }> = ({
  checked,
  label,
}) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
    <div
      style={{
        width: 16,
        height: 16,
        borderRadius: '50%',
        background: checked ? '#52c41a' : '#2a3f54',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 10,
        color: checked ? '#fff' : '#6a8caf',
      }}
    >
      {checked ? '✓' : '○'}
    </div>
    <Text style={{ fontSize: '11px', color: checked ? '#c9d1d9' : '#6a8caf' }}>
      {label}
    </Text>
  </div>
);

export default RealisticSettingsPanel;
