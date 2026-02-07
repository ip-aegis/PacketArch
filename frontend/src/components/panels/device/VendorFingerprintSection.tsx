/**
 * VendorFingerprintSection - Vendor, model, and firmware selection fields.
 */

import React from 'react';
import {
  Divider,
  Form,
  Select,
  Space,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  CodeOutlined,
  BugOutlined,
  InfoCircleOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import type { VendorSummary, FirmwareVariant } from '../../../api/fingerprints';

const { Text } = Typography;
const { Option } = Select;

export interface VendorFingerprintSectionProps {
  vendors: VendorSummary[];
  models: string[];
  loadingModels: boolean;
  firmwareVariants: FirmwareVariant[];
  loadingFirmwares: boolean;

  /** Current device values for conditional display */
  deviceVendor?: string;
  deviceFingerprintModel?: string;
  deviceFirmwareVersion?: string;
}

const VendorFingerprintSection: React.FC<VendorFingerprintSectionProps> = React.memo(({
  vendors,
  models,
  loadingModels,
  firmwareVariants,
  loadingFirmwares,
  deviceVendor,
  deviceFingerprintModel,
  deviceFirmwareVersion,
}) => {
  return (
    <>
      <Space style={{ marginBottom: '12px' }}>
        <SafetyCertificateOutlined style={{ color: '#5a9fd4' }} />
        <Text strong style={{ fontSize: '13px' }}>
          Vendor Fingerprint
        </Text>
        <Tooltip title="Apply authentic vendor identity for hyper-realistic traffic">
          <InfoCircleOutlined
            style={{ color: '#6a8caf', fontSize: 12 }}
          />
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
          placeholder={
            loadingModels ? 'Loading models...' : 'Select model'
          }
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
                <InfoCircleOutlined
                  style={{ color: '#6a8caf', fontSize: 12 }}
                />
              </Tooltip>
            </Space>
          }
          name="firmwareVersion"
        >
          <Select
            placeholder={
              loadingFirmwares
                ? 'Loading firmwares...'
                : 'Select firmware version'
            }
            allowClear
            loading={loadingFirmwares}
            showSearch
            optionFilterProp="label"
          >
            {firmwareVariants.map((fw) => (
              <Option
                key={fw.version}
                value={fw.version}
                label={fw.version}
              >
                <Space
                  style={{
                    width: '100%',
                    justifyContent: 'space-between',
                  }}
                >
                  <Space>
                    <CodeOutlined
                      style={{
                        color: fw.is_latest
                          ? '#52c41a'
                          : '#8c8c8c',
                      }}
                    />
                    <span>{fw.version}</span>
                    {fw.is_latest && (
                      <Tag
                        color="green"
                        style={{
                          fontSize: 10,
                          marginRight: 0,
                        }}
                      >
                        Latest
                      </Tag>
                    )}
                    {fw.is_default && !fw.is_latest && (
                      <Tag
                        color="blue"
                        style={{
                          fontSize: 10,
                          marginRight: 0,
                        }}
                      >
                        Default
                      </Tag>
                    )}
                  </Space>
                  {fw.cves.length > 0 && (
                    <Tag color="red" style={{ fontSize: 10 }}>
                      {fw.cves.length} CVE
                      {fw.cves.length > 1 ? 's' : ''}
                    </Tag>
                  )}
                </Space>
              </Option>
            ))}
          </Select>
        </Form.Item>
      )}

      {/* Firmware summary tag */}
      {deviceFirmwareVersion && firmwareVariants.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          {(() => {
            const selectedFw = firmwareVariants.find(
              (fw) => fw.version === deviceFirmwareVersion,
            );
            return (
              <Space
                direction="vertical"
                size={4}
                style={{ width: '100%' }}
              >
                <Tag
                  color="green"
                  icon={<SafetyCertificateOutlined />}
                >
                  {deviceVendor} {deviceFingerprintModel} v
                  {deviceFirmwareVersion}
                </Tag>
                {selectedFw?.cves && selectedFw.cves.length > 0 && (
                  <Space wrap size={4}>
                    {selectedFw.cves.map((cve) => (
                      <Tag
                        key={cve}
                        color="red"
                        icon={<BugOutlined />}
                        style={{ fontSize: 10 }}
                      >
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

      {deviceFingerprintModel &&
        firmwareVariants.length === 0 &&
        !loadingFirmwares && (
          <div style={{ marginBottom: 16 }}>
            <Tag color="green" icon={<SafetyCertificateOutlined />}>
              Fingerprint: {deviceVendor} {deviceFingerprintModel}
            </Tag>
          </div>
        )}

      <Divider style={{ margin: '16px 0' }} />
    </>
  );
});

VendorFingerprintSection.displayName = 'VendorFingerprintSection';

export default VendorFingerprintSection;
