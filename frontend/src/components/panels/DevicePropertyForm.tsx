/**
 * Device property form for right sidebar
 */

import React, { useEffect, useState } from 'react';
import { Form, Input, Select, InputNumber, Divider, Typography, Tag, Space, Tooltip, Alert } from 'antd';
import { SafetyCertificateOutlined, InfoCircleOutlined, BugOutlined, WarningOutlined, CodeOutlined } from '@ant-design/icons';
import { useScenarioStore } from '../../stores/scenarioStore';
import type { DeviceType, ProtocolType, CVEVulnerability, VulnerableFingerprintVariant } from '../../types';
import {
  listVendors,
  getVendorModels,
  listDeviceTemplates,
  listTemplateFirmwares,
  type VendorSummary,
  type DeviceTemplateSummary,
  type FirmwareVariant,
} from '../../api/fingerprints';
import { listCVEs, listVulnerableVariants, getSeverityColor } from '../../api/cve';

const { Text } = Typography;
const { Option } = Select;

interface DevicePropertyFormProps {
  deviceId: string;
}

const DEVICE_TYPES: { value: DeviceType; label: string }[] = [
  { value: 'plc', label: 'PLC' },
  { value: 'hmi', label: 'HMI' },
  { value: 'rtu', label: 'RTU' },
  { value: 'drive', label: 'Drive' },
  { value: 'sensor', label: 'Sensor' },
  { value: 'relay', label: 'Relay' },
  { value: 'ews', label: 'Engineering Workstation' },
  { value: 'historian', label: 'Historian' },
];

const PROTOCOLS: { value: ProtocolType; label: string }[] = [
  { value: 'modbus_tcp', label: 'Modbus TCP' },
  { value: 'ethernet_ip', label: 'EtherNet/IP' },
  { value: 'profinet', label: 'PROFINET' },
  { value: 'opc_ua', label: 'OPC UA' },
  { value: 'dnp3', label: 'DNP3' },
  { value: 'iec104', label: 'IEC 60870-5-104' },
  { value: 'bacnet', label: 'BACnet' },
];

const DevicePropertyForm: React.FC<DevicePropertyFormProps> = ({ deviceId }) => {
  const [form] = Form.useForm();
  const device = useScenarioStore((state) => state.devices[deviceId]);
  const updateDevice = useScenarioStore((state) => state.updateDevice);

  // Vendor/fingerprint state
  const [vendors, setVendors] = useState<VendorSummary[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);

  // Device template state
  const [deviceTemplates, setDeviceTemplates] = useState<DeviceTemplateSummary[]>([]);
  const [firmwareVariants, setFirmwareVariants] = useState<FirmwareVariant[]>([]);
  const [loadingFirmwares, setLoadingFirmwares] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);

  // CVE vulnerability state
  const [cves, setCves] = useState<CVEVulnerability[]>([]);
  const [vulnerableVariants, setVulnerableVariants] = useState<VulnerableFingerprintVariant[]>([]);
  const [loadingCves, setLoadingCves] = useState(false);
  const [selectedCve, setSelectedCve] = useState<CVEVulnerability | null>(null);

  // Fetch vendors and CVEs on mount
  useEffect(() => {
    const fetchVendors = async () => {
      try {
        const data = await listVendors();
        setVendors(data);
      } catch (err) {
        console.error('Failed to fetch vendors:', err);
      }
    };
    fetchVendors();
  }, []);

  // Fetch CVEs when vendor changes
  useEffect(() => {
    const fetchCves = async () => {
      if (!device?.vendor) {
        setCves([]);
        setVulnerableVariants([]);
        return;
      }

      setLoadingCves(true);
      try {
        const [cveData, variantData] = await Promise.all([
          listCVEs({ vendor: device.vendor }),
          listVulnerableVariants({ vendor: device.vendor }),
        ]);
        setCves(cveData.cves);
        setVulnerableVariants(variantData.variants);
      } catch (err) {
        console.error('Failed to fetch CVEs:', err);
        setCves([]);
        setVulnerableVariants([]);
      } finally {
        setLoadingCves(false);
      }
    };
    fetchCves();
  }, [device?.vendor]);

  // Fetch models and templates when vendor changes
  const handleVendorChange = async (vendor: string) => {
    if (!vendor) {
      setModels([]);
      setDeviceTemplates([]);
      setFirmwareVariants([]);
      setSelectedTemplateId(null);
      form.setFieldValue('fingerprintModel', undefined);
      form.setFieldValue('firmwareVersion', undefined);
      return;
    }

    setLoadingModels(true);
    try {
      const [modelList, templates] = await Promise.all([
        getVendorModels(vendor),
        listDeviceTemplates({ vendor }),
      ]);
      setModels(modelList);
      setDeviceTemplates(templates);
    } catch (err) {
      console.error('Failed to fetch models:', err);
      setModels([]);
      setDeviceTemplates([]);
    } finally {
      setLoadingModels(false);
    }
  };

  // Fetch firmware variants when model changes
  const handleModelChange = async (model: string) => {
    if (!model || !device?.vendor) {
      setFirmwareVariants([]);
      setSelectedTemplateId(null);
      form.setFieldValue('firmwareVersion', undefined);
      return;
    }

    // Find matching template
    const matchedTemplate = deviceTemplates.find(
      (t) =>
        t.model.toLowerCase() === model.toLowerCase() ||
        t.model_name.toLowerCase() === model.toLowerCase() ||
        t.model.toLowerCase().includes(model.toLowerCase()) ||
        t.model_name.toLowerCase().includes(model.toLowerCase())
    );

    if (matchedTemplate) {
      setSelectedTemplateId(matchedTemplate.id);
      setLoadingFirmwares(true);
      try {
        const firmwares = await listTemplateFirmwares(matchedTemplate.id);
        setFirmwareVariants(firmwares);
        // Auto-select default firmware if available
        const defaultFw = firmwares.find((fw) => fw.is_default);
        if (defaultFw && !device.firmwareVersion) {
          form.setFieldValue('firmwareVersion', defaultFw.version);
          updateDevice(deviceId, {
            templateId: matchedTemplate.id,
            firmwareVersion: defaultFw.version,
          });
        }
      } catch (err) {
        console.error('Failed to fetch firmware variants:', err);
        setFirmwareVariants([]);
      } finally {
        setLoadingFirmwares(false);
      }
    } else {
      setFirmwareVariants([]);
      setSelectedTemplateId(null);
    }
  };

  useEffect(() => {
    if (device) {
      form.setFieldsValue({
        name: device.name,
        type: device.type,
        role: device.role,
        vendor: device.vendor,
        fingerprintModel: device.fingerprintModel,
        firmwareVersion: device.firmwareVersion,
        vulnerableCve: device.vulnerableCve,
        macAddress: device.network.macAddress,
        ipAddress: device.network.ipAddress,
        subnetMask: device.network.subnetMask,
        gateway: device.network.gateway,
        vlanId: device.network.vlanId,
        hostname: device.network.hostname,
        protocols: device.protocols,
        intervalMs: device.timing?.intervalMs,
        jitterMs: device.timing?.jitterMs,
        burstSize: device.timing?.burstSize,
        burstIntervalMs: device.timing?.burstIntervalMs,
      });

      // Load models and templates if vendor is set
      if (device.vendor) {
        handleVendorChange(device.vendor).then(() => {
          // Load firmware variants if model is set
          if (device.fingerprintModel) {
            handleModelChange(device.fingerprintModel);
          }
        });
      }

      // Set selected CVE if device has one
      if (device.vulnerableCve && cves.length > 0) {
        const cve = cves.find((c) => c.cve_id === device.vulnerableCve);
        setSelectedCve(cve || null);
      }
    }
  }, [device, form, cves]);

  if (!device) {
    return null;
  }

  const handleValuesChange = (changedValues: any) => {
    const updates: any = {};

    // Basic fields
    if ('name' in changedValues) updates.name = changedValues.name;
    if ('type' in changedValues) updates.type = changedValues.type;
    if ('role' in changedValues) updates.role = changedValues.role;
    if ('protocols' in changedValues) updates.protocols = changedValues.protocols;

    // Vendor/fingerprint fields
    if ('vendor' in changedValues) {
      updates.vendor = changedValues.vendor;
      handleVendorChange(changedValues.vendor);
      // Clear CVE and firmware when vendor changes
      form.setFieldValue('vulnerableCve', undefined);
      form.setFieldValue('firmwareVersion', undefined);
      setSelectedCve(null);
    }
    if ('fingerprintModel' in changedValues) {
      updates.fingerprintModel = changedValues.fingerprintModel;
      handleModelChange(changedValues.fingerprintModel);
    }
    if ('firmwareVersion' in changedValues) {
      updates.firmwareVersion = changedValues.firmwareVersion;
      updates.templateId = selectedTemplateId;
    }

    // CVE vulnerability fields
    if ('vulnerableCve' in changedValues) {
      const cveId = changedValues.vulnerableCve;
      if (cveId) {
        const cve = cves.find((c) => c.cve_id === cveId);
        setSelectedCve(cve || null);
        // Find matching variant for protocol overrides
        const variant = vulnerableVariants.find((v) => v.cve_id === cveId);
        updates.vulnerableCve = cveId;
        updates.vulnerabilityOverride = variant
          ? {
              modbus_identity_override: variant.modbus_identity_override,
              ethernet_ip_identity_override: variant.ethernet_ip_identity_override,
              profinet_identity_override: variant.profinet_identity_override,
              s7_identity_override: variant.s7_identity_override,
            }
          : undefined;
      } else {
        setSelectedCve(null);
        updates.vulnerableCve = undefined;
        updates.vulnerabilityOverride = undefined;
      }
    }

    // Network fields
    const networkUpdates: any = {};
    if ('macAddress' in changedValues) networkUpdates.macAddress = changedValues.macAddress;
    if ('ipAddress' in changedValues) networkUpdates.ipAddress = changedValues.ipAddress;
    if ('subnetMask' in changedValues) networkUpdates.subnetMask = changedValues.subnetMask;
    if ('gateway' in changedValues) networkUpdates.gateway = changedValues.gateway;
    if ('vlanId' in changedValues) networkUpdates.vlanId = changedValues.vlanId;
    if ('hostname' in changedValues) networkUpdates.hostname = changedValues.hostname;

    if (Object.keys(networkUpdates).length > 0) {
      updates.network = { ...device.network, ...networkUpdates };
    }

    // Timing fields
    const timingUpdates: any = {};
    if ('intervalMs' in changedValues) timingUpdates.intervalMs = changedValues.intervalMs;
    if ('jitterMs' in changedValues) timingUpdates.jitterMs = changedValues.jitterMs;
    if ('burstSize' in changedValues) timingUpdates.burstSize = changedValues.burstSize;
    if ('burstIntervalMs' in changedValues) timingUpdates.burstIntervalMs = changedValues.burstIntervalMs;

    if (Object.keys(timingUpdates).length > 0) {
      updates.timing = { ...(device.timing || {}), ...timingUpdates };
    }

    if (Object.keys(updates).length > 0) {
      updateDevice(deviceId, updates);
    }
  };

  return (
    <Form
      form={form}
      layout="vertical"
      onValuesChange={handleValuesChange}
      size="small"
    >
      {/* Basic Information */}
      <Text strong style={{ fontSize: '13px', display: 'block', marginBottom: '12px' }}>
        Basic Information
      </Text>

      <Form.Item label="Device Name" name="name" rules={[{ required: true }]}>
        <Input placeholder="Enter device name" />
      </Form.Item>

      <Form.Item label="Device Type" name="type" rules={[{ required: true }]}>
        <Select>
          {DEVICE_TYPES.map((type) => (
            <Option key={type.value} value={type.value}>
              {type.label}
            </Option>
          ))}
        </Select>
      </Form.Item>

      <Form.Item label="Role" name="role">
        <Input placeholder="e.g., Main Controller" />
      </Form.Item>

      <Divider style={{ margin: '16px 0' }} />

      {/* Vendor Fingerprint */}
      <Space style={{ marginBottom: '12px' }}>
        <SafetyCertificateOutlined style={{ color: '#5a9fd4' }} />
        <Text strong style={{ fontSize: '13px' }}>
          Vendor Fingerprint
        </Text>
        <Tooltip title="Apply authentic vendor identity for hyper-realistic traffic">
          <InfoCircleOutlined style={{ color: '#6a8caf', fontSize: 12 }} />
        </Tooltip>
      </Space>

      <Form.Item label="Vendor" name="vendor">
        <Select
          placeholder="Select vendor"
          allowClear
          showSearch
          optionFilterProp="label"
          options={vendors.map((v) => ({
            value: v.vendor,
            label: v.display_name,
          }))}
        />
      </Form.Item>

      <Form.Item label="Fingerprint Model" name="fingerprintModel">
        <Select
          placeholder={loadingModels ? 'Loading models...' : 'Select model'}
          allowClear
          disabled={models.length === 0}
          loading={loadingModels}
          options={models.map((m) => ({
            value: m,
            label: m,
          }))}
        />
      </Form.Item>

      {firmwareVariants.length > 0 && (
        <Form.Item
          label={
            <Space>
              <span>Firmware Version</span>
              <Tooltip title="Select firmware version for accurate device fingerprinting. Vulnerable versions show associated CVEs.">
                <InfoCircleOutlined style={{ color: '#6a8caf', fontSize: 12 }} />
              </Tooltip>
            </Space>
          }
          name="firmwareVersion"
        >
          <Select
            placeholder={loadingFirmwares ? 'Loading firmwares...' : 'Select firmware version'}
            allowClear
            loading={loadingFirmwares}
            showSearch
            optionFilterProp="label"
          >
            {firmwareVariants.map((fw) => (
              <Option key={fw.version} value={fw.version} label={fw.version}>
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Space>
                    <CodeOutlined style={{ color: fw.is_latest ? '#52c41a' : '#8c8c8c' }} />
                    <span>{fw.version}</span>
                    {fw.is_latest && (
                      <Tag color="green" style={{ fontSize: 10, marginRight: 0 }}>
                        Latest
                      </Tag>
                    )}
                    {fw.is_default && !fw.is_latest && (
                      <Tag color="blue" style={{ fontSize: 10, marginRight: 0 }}>
                        Default
                      </Tag>
                    )}
                  </Space>
                  {fw.cves.length > 0 && (
                    <Tag color="red" style={{ fontSize: 10 }}>
                      {fw.cves.length} CVE{fw.cves.length > 1 ? 's' : ''}
                    </Tag>
                  )}
                </Space>
              </Option>
            ))}
          </Select>
        </Form.Item>
      )}

      {device.firmwareVersion && firmwareVariants.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          {(() => {
            const selectedFw = firmwareVariants.find((fw) => fw.version === device.firmwareVersion);
            return (
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Tag color="green" icon={<SafetyCertificateOutlined />}>
                  {device.vendor} {device.fingerprintModel} v{device.firmwareVersion}
                </Tag>
                {selectedFw?.cves && selectedFw.cves.length > 0 && (
                  <Space wrap size={4}>
                    {selectedFw.cves.map((cve) => (
                      <Tag key={cve} color="red" icon={<BugOutlined />} style={{ fontSize: 10 }}>
                        {cve}
                      </Tag>
                    ))}
                  </Space>
                )}
              </Space>
            );
          })()}
        </div>
      )}

      {device.fingerprintModel && firmwareVariants.length === 0 && !loadingFirmwares && (
        <div style={{ marginBottom: 16 }}>
          <Tag color="green" icon={<SafetyCertificateOutlined />}>
            Fingerprint: {device.vendor} {device.fingerprintModel}
          </Tag>
        </div>
      )}

      <Divider style={{ margin: '16px 0' }} />

      {/* CVE Vulnerability Simulation */}
      {device.vendor && (
        <>
          <Space style={{ marginBottom: '12px' }}>
            <BugOutlined style={{ color: '#ff4d4f' }} />
            <Text strong style={{ fontSize: '13px' }}>
              CVE Vulnerability
            </Text>
            <Tooltip title="Simulate a vulnerable firmware version that Cisco Cyber Vision will detect">
              <InfoCircleOutlined style={{ color: '#6a8caf', fontSize: 12 }} />
            </Tooltip>
          </Space>

          <Form.Item label="Vulnerable CVE" name="vulnerableCve">
            <Select
              placeholder={loadingCves ? 'Loading CVEs...' : 'Select CVE to simulate'}
              allowClear
              loading={loadingCves}
              disabled={cves.length === 0}
              showSearch
              optionFilterProp="label"
            >
              {cves.map((cve) => (
                <Option key={cve.cve_id} value={cve.cve_id} label={`${cve.cve_id} - ${cve.title}`}>
                  <Space>
                    <Tag color={getSeverityColor(cve.severity)} style={{ marginRight: 0 }}>
                      {cve.severity.toUpperCase()}
                    </Tag>
                    <span>{cve.cve_id}</span>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      CVSS {cve.cvss_score.toFixed(1)}
                    </Text>
                  </Space>
                </Option>
              ))}
            </Select>
          </Form.Item>

          {selectedCve && (
            <Alert
              type="warning"
              showIcon
              icon={<WarningOutlined />}
              style={{ marginBottom: 16 }}
              message={
                <Space direction="vertical" size={2} style={{ width: '100%' }}>
                  <Text strong style={{ fontSize: 12 }}>{selectedCve.title}</Text>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    Affected: {selectedCve.product_family} &lt; {selectedCve.affected_firmware_max}
                  </Text>
                  {selectedCve.cyber_vision_detectable && (
                    <Tag color="blue" style={{ fontSize: 10 }}>Cyber Vision Detectable</Tag>
                  )}
                </Space>
              }
            />
          )}

          {cves.length === 0 && !loadingCves && (
            <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 16 }}>
              No CVEs available for {device.vendor}. Select a supported vendor to enable vulnerability simulation.
            </Text>
          )}

          <Divider style={{ margin: '16px 0' }} />
        </>
      )}

      {/* Network Configuration */}
      <Text strong style={{ fontSize: '13px', display: 'block', marginBottom: '12px' }}>
        Network Configuration
      </Text>

      <Form.Item
        label="MAC Address"
        name="macAddress"
        rules={[
          { required: true },
          { pattern: /^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/, message: 'Invalid MAC address' },
        ]}
      >
        <Input placeholder="00:00:00:00:00:00" />
      </Form.Item>

      <Form.Item
        label="IP Address"
        name="ipAddress"
        rules={[
          { required: true },
          { pattern: /^(\d{1,3}\.){3}\d{1,3}$/, message: 'Invalid IP address' },
        ]}
      >
        <Input placeholder="192.168.1.10" />
      </Form.Item>

      <Form.Item label="Subnet Mask" name="subnetMask">
        <Input placeholder="255.255.255.0" />
      </Form.Item>

      <Form.Item label="Gateway" name="gateway">
        <Input placeholder="192.168.1.1" />
      </Form.Item>

      <Form.Item label="VLAN ID" name="vlanId">
        <InputNumber min={1} max={4094} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item label="Hostname" name="hostname">
        <Input placeholder="plc-001" />
      </Form.Item>

      <Divider style={{ margin: '16px 0' }} />

      {/* Protocols */}
      <Text strong style={{ fontSize: '13px', display: 'block', marginBottom: '12px' }}>
        Protocols
      </Text>

      <Form.Item label="Supported Protocols" name="protocols">
        <Select mode="multiple" placeholder="Select protocols">
          {PROTOCOLS.map((protocol) => (
            <Option key={protocol.value} value={protocol.value}>
              {protocol.label}
            </Option>
          ))}
        </Select>
      </Form.Item>

      <Divider style={{ margin: '16px 0' }} />

      {/* Timing Configuration */}
      <Text strong style={{ fontSize: '13px', display: 'block', marginBottom: '12px' }}>
        Timing Configuration
      </Text>

      <Form.Item label="Interval (ms)" name="intervalMs">
        <InputNumber min={1} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item label="Jitter (ms)" name="jitterMs">
        <InputNumber min={0} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item label="Burst Size" name="burstSize">
        <InputNumber min={1} style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item label="Burst Interval (ms)" name="burstIntervalMs">
        <InputNumber min={1} style={{ width: '100%' }} />
      </Form.Item>
    </Form>
  );
};

export default DevicePropertyForm;
