/**
 * Zone property form for right sidebar
 */

import React, { useEffect } from 'react';
import { Form, Input, Select, InputNumber, Divider, Typography, Tag } from 'antd';
import { useScenarioStore } from '../../stores/scenarioStore';
import type { ScenarioZone } from '../../types';

const { Text } = Typography;
const { Option } = Select;

const ZONE_TYPE_OPTIONS = [
  { value: 'vertical', label: 'Vertical' },
  { value: 'network', label: 'Network' },
  { value: 'vlan', label: 'VLAN' },
  { value: 'logical', label: 'Logical' },
];

const PURDUE_LEVEL_OPTIONS = [
  { value: 0, label: 'Level 0 — Physical Process' },
  { value: 1, label: 'Level 1 — Basic Control' },
  { value: 2, label: 'Level 2 — Area Control' },
  { value: 3, label: 'Level 3 — Site Operations' },
  { value: 3.5, label: 'Level 3.5 — DMZ' },
  { value: 4, label: 'Level 4 — Enterprise' },
];

const ZONE_COLOR_PRESETS = [
  { value: '#1668dc', label: 'Blue' },
  { value: '#49aa19', label: 'Green' },
  { value: '#d89614', label: 'Gold' },
  { value: '#dc4446', label: 'Red' },
  { value: '#9254de', label: 'Purple' },
  { value: '#13a8a8', label: 'Cyan' },
  { value: '#8c8c8c', label: 'Gray' },
];

interface ZonePropertyFormProps {
  zoneId: string;
}

const ZonePropertyForm: React.FC<ZonePropertyFormProps> = ({ zoneId }) => {
  const [form] = Form.useForm();
  const zone = useScenarioStore((state) => state.zones[zoneId]);
  const updateZone = useScenarioStore((state) => state.updateZone);

  // Sync form from zone state
  useEffect(() => {
    if (zone) {
      form.setFieldsValue({
        name: zone.name,
        type: zone.type,
        level: zone.level,
        color: zone.color,
        subnet: zone.network?.subnet,
        vlanId: zone.network?.vlanId,
        gateway: zone.network?.gateway,
      });
    }
  }, [zone, form]);

  if (!zone) return null;

  const handleValuesChange = (changedValues: Partial<Record<string, unknown>>) => {
    const updates: Partial<ScenarioZone> = {};

    if ('name' in changedValues) updates.name = changedValues.name as string;
    if ('type' in changedValues) updates.type = changedValues.type as ScenarioZone['type'];
    if ('level' in changedValues) updates.level = changedValues.level as number;
    if ('color' in changedValues) updates.color = changedValues.color as string;

    // Network fields
    const networkUpdates: Partial<NonNullable<ScenarioZone['network']>> = {};
    if ('subnet' in changedValues) networkUpdates.subnet = changedValues.subnet as string;
    if ('vlanId' in changedValues) networkUpdates.vlanId = changedValues.vlanId as number;
    if ('gateway' in changedValues) networkUpdates.gateway = changedValues.gateway as string;

    if (Object.keys(networkUpdates).length > 0) {
      updates.network = { ...(zone.network || { subnet: '' }), ...networkUpdates };
    }

    if (Object.keys(updates).length > 0) {
      updateZone(zoneId, updates);
    }
  };

  return (
    <Form
      form={form}
      layout="vertical"
      onValuesChange={handleValuesChange}
      size="small"
    >
      {/* General */}
      <Text
        strong
        style={{ fontSize: '13px', display: 'block', marginBottom: '12px' }}
      >
        Zone Properties
      </Text>

      <Form.Item label="Zone Name" name="name" rules={[{ required: true }]}>
        <Input placeholder="Enter zone name" />
      </Form.Item>

      <Form.Item label="Zone Type" name="type" rules={[{ required: true }]}>
        <Select>
          {ZONE_TYPE_OPTIONS.map((opt) => (
            <Option key={opt.value} value={opt.value}>
              {opt.label}
            </Option>
          ))}
        </Select>
      </Form.Item>

      <Form.Item label="Purdue Level" name="level">
        <Select allowClear placeholder="Select Purdue level">
          {PURDUE_LEVEL_OPTIONS.map((opt) => (
            <Option key={opt.value} value={opt.value}>
              {opt.label}
            </Option>
          ))}
        </Select>
      </Form.Item>

      <Divider style={{ margin: '16px 0' }} />

      {/* Network */}
      <Text
        strong
        style={{ fontSize: '13px', display: 'block', marginBottom: '12px' }}
      >
        Network
      </Text>

      <Form.Item label="Subnet" name="subnet">
        <Input placeholder="e.g., 10.1.0.0/24" />
      </Form.Item>

      <Form.Item label="VLAN ID" name="vlanId">
        <InputNumber min={1} max={4094} placeholder="1-4094" style={{ width: '100%' }} />
      </Form.Item>

      <Form.Item label="Gateway" name="gateway">
        <Input placeholder="e.g., 10.1.0.1" />
      </Form.Item>

      <Divider style={{ margin: '16px 0' }} />

      {/* Display */}
      <Text
        strong
        style={{ fontSize: '13px', display: 'block', marginBottom: '12px' }}
      >
        Display
      </Text>

      <Form.Item label="Color" name="color">
        <Select allowClear placeholder="Default">
          {ZONE_COLOR_PRESETS.map((opt) => (
            <Option key={opt.value} value={opt.value}>
              <span
                style={{
                  display: 'inline-block',
                  width: 12,
                  height: 12,
                  borderRadius: 2,
                  backgroundColor: opt.value,
                  marginRight: 8,
                  verticalAlign: 'middle',
                }}
              />
              {opt.label}
            </Option>
          ))}
        </Select>
      </Form.Item>

      <Divider style={{ margin: '16px 0' }} />

      {/* Info */}
      <Text
        strong
        style={{ fontSize: '13px', display: 'block', marginBottom: '12px' }}
      >
        Info
      </Text>

      <div style={{ color: '#8899aa', fontSize: '12px' }}>
        <div style={{ marginBottom: 4 }}>
          Devices: <Tag>{zone.deviceIds.length}</Tag>
        </div>
        <div>
          ID: <Text copyable style={{ fontSize: '11px', color: '#667788' }}>{zone.id}</Text>
        </div>
      </div>
    </Form>
  );
};

export default ZonePropertyForm;
