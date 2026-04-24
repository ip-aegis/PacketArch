/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Flow property form for right sidebar
 */

import React, { useEffect, useState, useRef, useMemo } from 'react';
import { Form, Input, Select, InputNumber, Checkbox, Divider, Typography, Card, Segmented, Tooltip } from 'antd';
import { DownOutlined, UpOutlined } from '@ant-design/icons';
import { useScenarioStore } from '../../stores/scenarioStore';
import type { ProtocolType, ScenarioFlow } from '../../types';
import { PROTOCOL_OPTIONS } from '../../constants/protocols';
import { getPresetsForProtocol, detectPreset, type PresetKey } from '../../constants/trafficPresets';

const { Text } = Typography;
const { Option } = Select;

interface FlowPropertyFormProps {
  flowId: string;
}

const FlowPropertyForm: React.FC<FlowPropertyFormProps> = ({ flowId }) => {
  const [form] = Form.useForm();
  const flow = useScenarioStore((state) => state.flows[flowId]);
  const devices = useScenarioStore((state) => state.devices);
  const updateFlow = useScenarioStore((state) => state.updateFlow);
  const [manualPreset, setManualPreset] = useState<PresetKey | 'custom' | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [trackedFlowId, setTrackedFlowId] = useState(flowId);
  const isApplyingPreset = useRef(false);

  // Reset manual override when flow changes
  if (trackedFlowId !== flowId) {
    setTrackedFlowId(flowId);
    if (manualPreset !== null) {
      setManualPreset(null);
    }
  }

  // Derive active preset from flow timing (unless manually overridden)
  const activePreset: PresetKey | 'custom' = useMemo(() => {
    if (manualPreset !== null) return manualPreset;
    if (!flow) return 'custom';
    const timing = flow.timing || { intervalMs: 1000, jitterMs: 100 };
    return detectPreset(flow.protocol, timing) || 'custom';
  }, [flow, manualPreset]);

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

  const handlePresetChange = (value: string | number) => {
    const key = value as PresetKey | 'custom';
    setManualPreset(key);
    if (key === 'custom') return;

    const presets = getPresetsForProtocol(flow.protocol);
    const preset = presets[key as PresetKey];
    if (!preset) return;

    isApplyingPreset.current = true;
    form.setFieldsValue({
      intervalMs: preset.timing.intervalMs,
      jitterMs: preset.timing.jitterMs,
    });

    const currentTiming = flow.timing || { intervalMs: 1000, jitterMs: 100 };
    updateFlow(flowId, {
      timing: {
        ...currentTiming,
        intervalMs: preset.timing.intervalMs,
        jitterMs: preset.timing.jitterMs,
      },
    });
    isApplyingPreset.current = false;
  };

  const handleValuesChange = (changedValues: Partial<Record<string, unknown>>) => {
    const updates: Partial<ScenarioFlow> = {};

    if ('name' in changedValues) updates.name = changedValues.name as string;
    if ('protocol' in changedValues) {
      updates.protocol = changedValues.protocol as ProtocolType;
    }

    // Timing updates
    const timingUpdates: Partial<ScenarioFlow['timing']> = {};
    if ('intervalMs' in changedValues) timingUpdates.intervalMs = changedValues.intervalMs as number;
    if ('jitterMs' in changedValues) timingUpdates.jitterMs = changedValues.jitterMs as number;
    if ('burstSize' in changedValues) timingUpdates.burstSize = changedValues.burstSize as number;
    if ('burstIntervalMs' in changedValues) timingUpdates.burstIntervalMs = changedValues.burstIntervalMs as number;

    if (Object.keys(timingUpdates).length > 0) {
      const currentTiming = flow.timing || {
        intervalMs: 1000,
        jitterMs: 100,
      };
      updates.timing = { ...currentTiming, ...timingUpdates };

      // If user manually changed a timing field, mark as custom
      if (!isApplyingPreset.current) {
        setManualPreset('custom');
      }
    }

    // When protocol changes, re-detect preset
    if ('protocol' in changedValues && !isApplyingPreset.current) {
      setManualPreset(null);
    }

    // Phase updates
    const phaseUpdates: Partial<ScenarioFlow['phases']> = {};
    if ('phaseStartup' in changedValues) phaseUpdates.startup = changedValues.phaseStartup as boolean;
    if ('phaseSteadyState' in changedValues) phaseUpdates.steadyState = changedValues.phaseSteadyState as boolean;
    if ('phaseMaintenance' in changedValues) phaseUpdates.maintenance = changedValues.phaseMaintenance as boolean;
    if ('phaseShutdown' in changedValues) phaseUpdates.shutdown = changedValues.phaseShutdown as boolean;

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

  // Build preset options for the segmented control
  const presets = getPresetsForProtocol(flow.protocol);
  const presetOptions = (Object.keys(presets) as PresetKey[]).map((key) => ({
    value: key,
    label: (
      <Tooltip title={presets[key].description}>
        <span>{presets[key].label}</span>
      </Tooltip>
    ),
  }));
  // Add custom option
  presetOptions.push({
    value: 'custom' as PresetKey,
    label: (
      <Tooltip title="Custom timing values">
        <span>Custom</span>
      </Tooltip>
    ),
  });

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
          {PROTOCOL_OPTIONS.map((protocol) => (
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

      {/* Traffic Profile Preset Selector */}
      <div style={{ marginBottom: 16 }}>
        <Text style={{ fontSize: 12, color: '#6b6b8a', display: 'block', marginBottom: 6 }}>
          Traffic Profile
        </Text>
        <Segmented
          value={activePreset}
          options={presetOptions}
          onChange={handlePresetChange}
          block
          size="small"
        />
      </div>

      {/* Advanced Timing Toggle */}
      <div
        style={{ marginBottom: 8, cursor: 'pointer', userSelect: 'none', display: 'flex', alignItems: 'center', gap: 4 }}
        onClick={() => setAdvancedOpen(!advancedOpen)}
      >
        {advancedOpen ? <UpOutlined style={{ fontSize: 10, color: '#6b6b8a' }} /> : <DownOutlined style={{ fontSize: 10, color: '#6b6b8a' }} />}
        <Text style={{ fontSize: 11, color: '#6b6b8a' }}>
          Advanced Timing
        </Text>
      </div>

      {advancedOpen && (
        <>
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
        </>
      )}

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
