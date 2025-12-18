/**
 * Flow property form for right sidebar
 */

import React, { useEffect } from 'react';
import { Form, Input, Select, InputNumber, Checkbox, Divider, Typography, Card } from 'antd';
import { useScenarioStore } from '../../stores/scenarioStore';
import type { ProtocolType } from '../../types';

const { Text } = Typography;
const { Option } = Select;

interface FlowPropertyFormProps {
  flowId: string;
}

const PROTOCOLS: { value: ProtocolType; label: string }[] = [
  { value: 'modbus_tcp', label: 'Modbus TCP' },
  { value: 'ethernet_ip', label: 'EtherNet/IP' },
  { value: 'profinet', label: 'PROFINET' },
  { value: 'opc_ua', label: 'OPC UA' },
  { value: 'dnp3', label: 'DNP3' },
  { value: 'iec104', label: 'IEC 60870-5-104' },
  { value: 'bacnet', label: 'BACnet' },
];

const FlowPropertyForm: React.FC<FlowPropertyFormProps> = ({ flowId }) => {
  const [form] = Form.useForm();
  const flow = useScenarioStore((state) => state.flows[flowId]);
  const devices = useScenarioStore((state) => state.devices);
  const updateFlow = useScenarioStore((state) => state.updateFlow);

  useEffect(() => {
    if (flow) {
      // Default phases if not present
      const phases = flow.phases || {
        startup: true,
        steadyState: true,
        maintenance: true,
        shutdown: true,
      };
      const timing = flow.timing || {
        intervalMs: 1000,
        jitterMs: 100,
      };

      form.setFieldsValue({
        name: flow.name,
        protocol: flow.protocol,
        intervalMs: timing.intervalMs,
        jitterMs: timing.jitterMs,
        burstSize: timing.burstSize,
        burstIntervalMs: timing.burstIntervalMs,
        phaseStartup: phases.startup,
        phaseSteadyState: phases.steadyState,
        phaseMaintenance: phases.maintenance,
        phaseShutdown: phases.shutdown,
      });
    }
  }, [flow, form]);

  if (!flow) {
    return null;
  }

  const sourceDevice = devices[flow.sourceDeviceId];
  const targetDevice = devices[flow.targetDeviceId];

  const handleValuesChange = (changedValues: any) => {
    const updates: any = {};

    if ('name' in changedValues) updates.name = changedValues.name;
    if ('protocol' in changedValues) updates.protocol = changedValues.protocol;

    // Timing updates
    const timingUpdates: any = {};
    if ('intervalMs' in changedValues) timingUpdates.intervalMs = changedValues.intervalMs;
    if ('jitterMs' in changedValues) timingUpdates.jitterMs = changedValues.jitterMs;
    if ('burstSize' in changedValues) timingUpdates.burstSize = changedValues.burstSize;
    if ('burstIntervalMs' in changedValues) timingUpdates.burstIntervalMs = changedValues.burstIntervalMs;

    if (Object.keys(timingUpdates).length > 0) {
      const currentTiming = flow.timing || {
        intervalMs: 1000,
        jitterMs: 100,
      };
      updates.timing = { ...currentTiming, ...timingUpdates };
    }

    // Phase updates
    const phaseUpdates: any = {};
    if ('phaseStartup' in changedValues) phaseUpdates.startup = changedValues.phaseStartup;
    if ('phaseSteadyState' in changedValues) phaseUpdates.steadyState = changedValues.phaseSteadyState;
    if ('phaseMaintenance' in changedValues) phaseUpdates.maintenance = changedValues.phaseMaintenance;
    if ('phaseShutdown' in changedValues) phaseUpdates.shutdown = changedValues.phaseShutdown;

    if (Object.keys(phaseUpdates).length > 0) {
      const currentPhases = flow.phases || {
        startup: true,
        steadyState: true,
        maintenance: true,
        shutdown: true,
      };
      updates.phases = { ...currentPhases, ...phaseUpdates };
    }

    if (Object.keys(updates).length > 0) {
      updateFlow(flowId, updates);
    }
  };

  return (
    <Form
      form={form}
      layout="vertical"
      onValuesChange={handleValuesChange}
      size="small"
    >
      {/* Flow Information */}
      <Text strong style={{ fontSize: '13px', display: 'block', marginBottom: '12px' }}>
        Flow Information
      </Text>

      <Form.Item label="Flow Name" name="name" rules={[{ required: true }]}>
        <Input placeholder="Enter flow name" />
      </Form.Item>

      {/* Connection Info */}
      <Card size="small" style={{ marginBottom: '16px', background: '#f5f5f5' }}>
        <div style={{ fontSize: '12px' }}>
          <Text strong>Source: </Text>
          <Text>{sourceDevice?.name || 'Unknown'}</Text>
        </div>
        <div style={{ fontSize: '12px', marginTop: '4px' }}>
          <Text strong>Target: </Text>
          <Text>{targetDevice?.name || 'Unknown'}</Text>
        </div>
      </Card>

      <Form.Item label="Protocol" name="protocol" rules={[{ required: true }]}>
        <Select>
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

      <Form.Item label="Interval (ms)" name="intervalMs" rules={[{ required: true }]}>
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

      <Divider style={{ margin: '16px 0' }} />

      {/* Phase Activation */}
      <Text strong style={{ fontSize: '13px', display: 'block', marginBottom: '12px' }}>
        Active in Phases
      </Text>

      <Form.Item name="phaseStartup" valuePropName="checked">
        <Checkbox>Startup</Checkbox>
      </Form.Item>

      <Form.Item name="phaseSteadyState" valuePropName="checked">
        <Checkbox>Steady State</Checkbox>
      </Form.Item>

      <Form.Item name="phaseMaintenance" valuePropName="checked">
        <Checkbox>Maintenance</Checkbox>
      </Form.Item>

      <Form.Item name="phaseShutdown" valuePropName="checked">
        <Checkbox>Shutdown</Checkbox>
      </Form.Item>
    </Form>
  );
};

export default FlowPropertyForm;
