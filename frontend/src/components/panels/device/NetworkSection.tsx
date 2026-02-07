/**
 * NetworkSection - Network settings (IP, MAC, subnet, gateway, VLAN, hostname)
 * and protocol selection for a device.
 */

import React from 'react';
import { Divider, Form, Input, InputNumber, Select, Typography } from 'antd';
import { PROTOCOL_OPTIONS } from '../../../constants/protocols';

const { Text } = Typography;
const { Option } = Select;

/**
 * This is a pure-render component: all form state is managed by the
 * parent Form via Form.Item `name` bindings.
 */
const NetworkSection: React.FC = React.memo(() => {
  return (
    <>
      {/* Network Configuration */}
      <Text
        strong
        style={{
          fontSize: '13px',
          display: 'block',
          marginBottom: '12px',
        }}
      >
        Network Configuration
      </Text>

      <Form.Item
        label="MAC Address"
        name="macAddress"
        rules={[
          { required: true },
          {
            pattern: /^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/,
            message: 'Invalid MAC address',
          },
        ]}
      >
        <Input placeholder="00:00:00:00:00:00" />
      </Form.Item>

      <Form.Item
        label="IP Address"
        name="ipAddress"
        rules={[
          { required: true },
          {
            pattern: /^(\d{1,3}\.){3}\d{1,3}$/,
            message: 'Invalid IP address',
          },
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
      <Text
        strong
        style={{
          fontSize: '13px',
          display: 'block',
          marginBottom: '12px',
        }}
      >
        Protocols
      </Text>

      <Form.Item label="Supported Protocols" name="protocols">
        <Select mode="multiple" placeholder="Select protocols">
          {PROTOCOL_OPTIONS.map((protocol) => (
            <Option key={protocol.value} value={protocol.value}>
              {protocol.label}
            </Option>
          ))}
        </Select>
      </Form.Item>

      <Divider style={{ margin: '16px 0' }} />

      {/* Timing Configuration */}
      <Text
        strong
        style={{
          fontSize: '13px',
          display: 'block',
          marginBottom: '12px',
        }}
      >
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
    </>
  );
});

NetworkSection.displayName = 'NetworkSection';

export default NetworkSection;
