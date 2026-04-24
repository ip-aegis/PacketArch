/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * CVESection - CVE vulnerability selection and display.
 */

import React from 'react';
import {
  Alert,
  Divider,
  Form,
  Select,
  Space,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  BugOutlined,
  InfoCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import type { CVEVulnerability } from '../../../types';
import { getSeverityColor } from '../../../api/cve';

const { Text } = Typography;
const { Option } = Select;

export interface CVESectionProps {
  deviceVendor: string;
  cves: CVEVulnerability[];
  loadingCves: boolean;
  selectedCve: CVEVulnerability | null;
}

const CVESection: React.FC<CVESectionProps> = React.memo(({
  deviceVendor,
  cves,
  loadingCves,
  selectedCve,
}) => {
  return (
    <>
      <Space style={{ marginBottom: '12px' }}>
        <BugOutlined style={{ color: '#ff4d4f' }} />
        <Text strong style={{ fontSize: '13px' }}>
          CVE Vulnerability
        </Text>
        <Tooltip title="Simulate a vulnerable firmware version that Cisco Cyber Vision will detect">
          <InfoCircleOutlined
            style={{ color: '#6a8caf', fontSize: 12 }}
          />
        </Tooltip>
      </Space>

      <Form.Item label="Vulnerable CVE" name="vulnerableCve">
        <Select
          placeholder={
            loadingCves
              ? 'Loading CVEs...'
              : 'Select CVE to simulate'
          }
          allowClear
          loading={loadingCves}
          disabled={cves.length === 0}
          showSearch
          optionFilterProp="label"
        >
          {cves.map((cve) => (
            <Option
              key={cve.cve_id}
              value={cve.cve_id}
              label={`${cve.cve_id} - ${cve.title}`}
            >
              <Space>
                <Tag
                  color={getSeverityColor(cve.severity)}
                  style={{ marginRight: 0 }}
                >
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
            <Space
              direction="vertical"
              size={2}
              style={{ width: '100%' }}
            >
              <Text strong style={{ fontSize: 12 }}>
                {selectedCve.title}
              </Text>
              <Text type="secondary" style={{ fontSize: 11 }}>
                Affected: {selectedCve.product_family} &lt;{' '}
                {selectedCve.affected_firmware_max}
              </Text>
              {selectedCve.cyber_vision_detectable && (
                <Tag color="blue" style={{ fontSize: 10 }}>
                  Cyber Vision Detectable
                </Tag>
              )}
            </Space>
          }
        />
      )}

      {cves.length === 0 && !loadingCves && (
        <Text
          type="secondary"
          style={{
            fontSize: 11,
            display: 'block',
            marginBottom: 16,
          }}
        >
          No CVEs available for {deviceVendor}. Select a supported
          vendor to enable vulnerability simulation.
        </Text>
      )}

      <Divider style={{ margin: '16px 0' }} />
    </>
  );
});

CVESection.displayName = 'CVESection';

export default CVESection;
