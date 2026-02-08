/**
 * Step 6 — Finalize: name, description, options, and create.
 */

import React from 'react';
import {
  Input,
  Select,
  Checkbox,
  Collapse,
  Card,
  Tag,
  Typography,
  Space,
  Spin,
} from 'antd';
import { useQuery } from '@tanstack/react-query';
import { templatesApi } from '../../api/templates';
import { useGuidedBuilderStore } from '../../stores/guidedBuilderStore';
import { verticalConfig } from '../scenarios/scenarioConstants';
import { getProtocolColor, getProtocolLabel } from '../../constants/protocols';

const { Title, Text } = Typography;
const { TextArea } = Input;

const FinalizeStep: React.FC = () => {
  const {
    selectedVertical,
    selectedTemplate,
    expandedDevices,
    templateDetail,
    scenarioName,
    description,
    phasePreset,
    useAINaming,
    processContext,
    isCreating,
    setScenarioName,
    setDescription,
    setPhasePreset,
    setUseAINaming,
    setProcessContext,
  } = useGuidedBuilderStore();

  const { data: phasePresets } = useQuery({
    queryKey: ['phase-presets'],
    queryFn: () => templatesApi.getPhasePresets(),
  });

  const vConfig = selectedVertical ? verticalConfig[selectedVertical] : null;
  const protocols = [...new Set(expandedDevices.flatMap((d) => d.protocols))];
  const zoneCount = new Set(expandedDevices.map((d) => d.zone).filter(Boolean)).size;

  if (isCreating) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" />
        <div style={{ marginTop: 16, color: '#8aa4bc' }}>
          Creating scenario and applying customizations...
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 600 }}>
      <Title level={5} style={{ color: '#e0e8f0', marginBottom: 16 }}>
        Finalize Your Scenario
      </Title>

      {/* Scenario Name */}
      <div style={{ marginBottom: 16 }}>
        <Text strong style={{ color: '#c9d1d9', display: 'block', marginBottom: 4 }}>
          Scenario Name *
        </Text>
        <Input
          value={scenarioName}
          onChange={(e) => setScenarioName(e.target.value)}
          placeholder="Enter scenario name"
          maxLength={255}
        />
      </div>

      {/* Description */}
      <div style={{ marginBottom: 16 }}>
        <Text strong style={{ color: '#c9d1d9', display: 'block', marginBottom: 4 }}>
          Description
        </Text>
        <TextArea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          placeholder="Optional description"
        />
      </div>

      {/* Phase Preset */}
      <div style={{ marginBottom: 16 }}>
        <Text strong style={{ color: '#c9d1d9', display: 'block', marginBottom: 4 }}>
          Phase Preset
        </Text>
        <Select
          value={phasePreset}
          onChange={setPhasePreset}
          style={{ width: '100%' }}
          options={(phasePresets ?? []).map((p) => ({
            value: p.name,
            label: `${p.display_name} (${p.phase_count} phases)`,
          }))}
        />
      </div>

      {/* Options */}
      <Collapse
        ghost
        items={[
          {
            key: 'options',
            label: <Text style={{ color: '#8aa4bc' }}>Advanced Options</Text>,
            children: (
              <Space direction="vertical" style={{ width: '100%' }}>
                <Checkbox
                  checked={useAINaming}
                  onChange={(e) => setUseAINaming(e.target.checked)}
                >
                  <Text style={{ color: '#c9d1d9' }}>Customize device names with AI</Text>
                </Checkbox>
                {useAINaming && (
                  <div style={{ marginLeft: 24 }}>
                    <Text style={{ color: '#8aa4bc', fontSize: 12, display: 'block', marginBottom: 4 }}>
                      Describe your facility or process (e.g. &quot;candy factory&quot;, &quot;water treatment plant&quot;)
                    </Text>
                    <TextArea
                      value={processContext}
                      onChange={(e) => setProcessContext(e.target.value)}
                      rows={2}
                      maxLength={500}
                      placeholder="Optional facility description for AI naming"
                    />
                  </div>
                )}
              </Space>
            ),
          },
        ]}
        style={{ marginBottom: 16 }}
      />

      {/* Summary card */}
      <Card
        size="small"
        style={{ backgroundColor: '#141428', border: '1px solid #2a3f54' }}
        styles={{ body: { padding: 12 } }}
      >
        <Text style={{ color: '#8aa4bc', fontSize: 12, display: 'block', marginBottom: 8 }}>
          Summary
        </Text>
        <Space wrap size={8}>
          {vConfig && (
            <Tag color={vConfig.color}>{vConfig.label}</Tag>
          )}
          {selectedTemplate && (
            <Tag>{selectedTemplate.display_name}</Tag>
          )}
          <Tag>{expandedDevices.length} devices</Tag>
          <Tag>{zoneCount} zones</Tag>
          {protocols.map((p) => (
            <Tag key={p} color={getProtocolColor(p)} style={{ fontSize: 11 }}>
              {getProtocolLabel(p)}
            </Tag>
          ))}
        </Space>
      </Card>
    </div>
  );
};

export default FinalizeStep;
