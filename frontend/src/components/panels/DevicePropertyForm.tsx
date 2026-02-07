/**
 * Device property form for right sidebar
 */

import React, { useEffect, useState } from 'react';
import { Form, Input, Select, Divider, Typography } from 'antd';
import { useScenarioStore } from '../../stores/scenarioStore';
import type {
  DeviceType,
  ProtocolType,
  CVEVulnerability,
  VulnerableFingerprintVariant,
  ScenarioDevice,
} from '../../types';
import {
  listTemplateFirmwares,
  type FirmwareVariant,
} from '../../api/fingerprints';
import { listCVEs, listVulnerableVariants } from '../../api/cve';
import { DEVICE_TYPE_OPTIONS } from '../../constants/protocols';
import { useVendorData } from '../../hooks/useVendorData';

import VendorFingerprintSection from './device/VendorFingerprintSection';
import CVESection from './device/CVESection';
import NetworkSection from './device/NetworkSection';

const { Text } = Typography;
const { Option } = Select;

interface DevicePropertyFormProps {
  deviceId: string;
}

const DevicePropertyForm: React.FC<DevicePropertyFormProps> = ({
  deviceId,
}) => {
  const [form] = Form.useForm();
  const device = useScenarioStore((state) => state.devices[deviceId]);
  const updateDevice = useScenarioStore((state) => state.updateDevice);

  // Vendor/model data from shared hook
  const {
    vendors,
    models,
    loadingModels,
    deviceTemplates,
    handleVendorChange: hookVendorChange,
  } = useVendorData({ withFirmware: true });

  // Firmware state (specialized matching + form interaction)
  const [firmwareVariants, setFirmwareVariants] = useState<
    FirmwareVariant[]
  >([]);
  const [loadingFirmwares, setLoadingFirmwares] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<
    string | null
  >(null);

  // CVE vulnerability state
  const [cves, setCves] = useState<CVEVulnerability[]>([]);
  const [vulnerableVariants, setVulnerableVariants] = useState<
    VulnerableFingerprintVariant[]
  >([]);
  const [loadingCves, setLoadingCves] = useState(false);
  const [selectedCve, setSelectedCve] =
    useState<CVEVulnerability | null>(null);

  // ── Fetch CVEs when vendor changes ──────────────────────────────
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

  // ── Vendor change ───────────────────────────────────────────────
  const handleVendorChange = async (vendor: string) => {
    if (!vendor) {
      setFirmwareVariants([]);
      setSelectedTemplateId(null);
      form.setFieldValue('fingerprintModel', undefined);
      form.setFieldValue('firmwareVersion', undefined);
    }
    await hookVendorChange(vendor);
  };

  // ── Model change ────────────────────────────────────────────────
  const handleModelChange = async (model: string) => {
    if (!model || !device?.vendor) {
      setFirmwareVariants([]);
      setSelectedTemplateId(null);
      form.setFieldValue('firmwareVersion', undefined);
      return;
    }

    const matchedTemplate = deviceTemplates.find(
      (t) =>
        t.model.toLowerCase() === model.toLowerCase() ||
        t.model_name.toLowerCase() === model.toLowerCase() ||
        t.model.toLowerCase().includes(model.toLowerCase()) ||
        t.model_name.toLowerCase().includes(model.toLowerCase()),
    );

    if (matchedTemplate) {
      setSelectedTemplateId(matchedTemplate.id);
      setLoadingFirmwares(true);
      try {
        const firmwares = await listTemplateFirmwares(
          matchedTemplate.id,
        );
        setFirmwareVariants(firmwares);
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

  // ── Sync form from device ───────────────────────────────────────
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

      if (device.vendor) {
        handleVendorChange(device.vendor).then(() => {
          if (device.fingerprintModel) {
            handleModelChange(device.fingerprintModel);
          }
        });
      }

      if (device.vulnerableCve && cves.length > 0) {
        const cve = cves.find(
          (c) => c.cve_id === device.vulnerableCve,
        );
        setSelectedCve(cve || null);
      }
    }
  }, [device, form, cves]);

  if (!device) return null;

  // ── Values change handler ───────────────────────────────────────
  const handleValuesChange = (
    changedValues: Partial<Record<string, unknown>>,
  ) => {
    const updates: Partial<ScenarioDevice> = {};

    // Basic fields
    if ('name' in changedValues)
      updates.name = changedValues.name as string;
    if ('type' in changedValues)
      updates.type = changedValues.type as DeviceType;
    if ('role' in changedValues)
      updates.role = changedValues.role as string;
    if ('protocols' in changedValues)
      updates.protocols = changedValues.protocols as ProtocolType[];

    // Vendor/fingerprint fields
    if ('vendor' in changedValues) {
      updates.vendor = changedValues.vendor as string;
      handleVendorChange(changedValues.vendor as string);
      form.setFieldValue('vulnerableCve', undefined);
      form.setFieldValue('firmwareVersion', undefined);
      setSelectedCve(null);
    }
    if ('fingerprintModel' in changedValues) {
      updates.fingerprintModel =
        changedValues.fingerprintModel as string;
      handleModelChange(changedValues.fingerprintModel as string);
    }
    if ('firmwareVersion' in changedValues) {
      updates.firmwareVersion =
        changedValues.firmwareVersion as string;
      updates.templateId = selectedTemplateId;
    }

    // CVE vulnerability fields
    if ('vulnerableCve' in changedValues) {
      const cveId = changedValues.vulnerableCve as string | undefined;
      if (cveId) {
        const cve = cves.find((c) => c.cve_id === cveId);
        setSelectedCve(cve || null);
        const variant = vulnerableVariants.find(
          (v) => v.cve_id === cveId,
        );
        updates.vulnerableCve = cveId;
        updates.vulnerabilityOverride = variant
          ? {
              modbus_identity_override:
                variant.modbus_identity_override,
              ethernet_ip_identity_override:
                variant.ethernet_ip_identity_override,
              profinet_identity_override:
                variant.profinet_identity_override,
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
    const networkUpdates: Partial<ScenarioDevice['network']> = {};
    if ('macAddress' in changedValues)
      networkUpdates.macAddress = changedValues.macAddress as string;
    if ('ipAddress' in changedValues)
      networkUpdates.ipAddress = changedValues.ipAddress as string;
    if ('subnetMask' in changedValues)
      networkUpdates.subnetMask = changedValues.subnetMask as string;
    if ('gateway' in changedValues)
      networkUpdates.gateway = changedValues.gateway as string;
    if ('vlanId' in changedValues)
      networkUpdates.vlanId = changedValues.vlanId as number;
    if ('hostname' in changedValues)
      networkUpdates.hostname = changedValues.hostname as string;

    if (Object.keys(networkUpdates).length > 0) {
      updates.network = { ...device.network, ...networkUpdates };
    }

    // Timing fields
    const timingUpdates: Partial<
      NonNullable<ScenarioDevice['timing']>
    > = {};
    if ('intervalMs' in changedValues)
      timingUpdates.intervalMs = changedValues.intervalMs as number;
    if ('jitterMs' in changedValues)
      timingUpdates.jitterMs = changedValues.jitterMs as number;
    if ('burstSize' in changedValues)
      timingUpdates.burstSize = changedValues.burstSize as number;
    if ('burstIntervalMs' in changedValues)
      timingUpdates.burstIntervalMs =
        changedValues.burstIntervalMs as number;

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
      <Text
        strong
        style={{
          fontSize: '13px',
          display: 'block',
          marginBottom: '12px',
        }}
      >
        Basic Information
      </Text>

      <Form.Item
        label="Device Name"
        name="name"
        rules={[{ required: true }]}
      >
        <Input placeholder="Enter device name" />
      </Form.Item>

      <Form.Item
        label="Device Type"
        name="type"
        rules={[{ required: true }]}
      >
        <Select>
          {DEVICE_TYPE_OPTIONS.map((type) => (
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
      <VendorFingerprintSection
        vendors={vendors}
        models={models}
        loadingModels={loadingModels}
        firmwareVariants={firmwareVariants}
        loadingFirmwares={loadingFirmwares}
        deviceVendor={device.vendor}
        deviceFingerprintModel={device.fingerprintModel}
        deviceFirmwareVersion={device.firmwareVersion}
      />

      {/* CVE Vulnerability */}
      {device.vendor && (
        <CVESection
          deviceVendor={device.vendor}
          cves={cves}
          loadingCves={loadingCves}
          selectedCve={selectedCve}
        />
      )}

      {/* Network + Protocols + Timing */}
      <NetworkSection />
    </Form>
  );
};

export default DevicePropertyForm;
