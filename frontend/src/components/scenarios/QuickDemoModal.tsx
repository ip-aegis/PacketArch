/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * One-click demo modal: pick a vertical, auto-deploy to an online agent,
 * navigate to Live Traffic dashboard.
 */

import React, { useState } from 'react';
import { Modal, Typography, Button, Alert, Select, Steps, Space, Tooltip, App } from 'antd';
import {
  ThunderboltOutlined,
  RocketOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useAgentsStore } from '../../stores/agentsStore';
import { agentsApi } from '../../api/agents';
import { templatesApi } from '../../api/templates';
import { verticalConfig } from './scenarioConstants';

const { Text, Title } = Typography;

/** Default template per vertical for Quick Demo */
const DEFAULT_DEMO_TEMPLATES: Record<string, string> = {
  manufacturing: 'siemens_discrete_manufacturing',
  water_wastewater: 'municipal_water_treatment',
  transportation: 'highway_corridor_its',
  building_automation: 'commercial_office_bms',
};

/** Verticals with no templates (empty dicts on backend) */
const DISABLED_VERTICALS = new Set(['energy_power', 'oil_gas']);

type DemoStep = 'select' | 'deploying' | 'done' | 'error';

interface QuickDemoModalProps {
  open: boolean;
  onCancel: () => void;
}

const QuickDemoModal: React.FC<QuickDemoModalProps> = ({ open, onCancel }) => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  const agents = useAgentsStore((s) => s.agents);
  const fetchAgents = useAgentsStore((s) => s.fetchAgents);

  const [step, setStep] = useState<DemoStep>('select');
  const [selectedVertical, setSelectedVertical] = useState<string | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [deployStep, setDeployStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const onlineAgents = agents.filter((a) => a.status === 'online');
  const [wasOpen, setWasOpen] = useState(open);

  // Reset state when modal transitions from closed → open
  if (open && !wasOpen) {
    setWasOpen(true);
    fetchAgents().catch(() => {});
    setStep('select');
    setSelectedVertical(null);
    setSelectedAgentId(null);
    setError(null);
    setDeployStep(0);
  } else if (!open && wasOpen) {
    setWasOpen(false);
  }

  // Auto-select first online agent when agents load
  const autoSelectedAgent = onlineAgents.length > 0 ? onlineAgents[0].id : null;
  const effectiveAgentId = selectedAgentId ?? autoSelectedAgent;

  const handleLaunch = async () => {
    if (!selectedVertical || !effectiveAgentId) return;

    const templateName = DEFAULT_DEMO_TEMPLATES[selectedVertical];
    if (!templateName) return;

    setStep('deploying');
    setDeployStep(0);
    setError(null);

    try {
      // Step 1: Create scenario from template
      const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const vertLabel = verticalConfig[selectedVertical]?.label || selectedVertical;
      const result = await templatesApi.createFromTemplate({
        vertical: selectedVertical,
        template_name: templateName,
        scenario_name: `Quick Demo - ${vertLabel} - ${timestamp}`,
        auto_assign_addresses: true,

      });

      setDeployStep(1);

      // Step 2: Deploy to agent
      await agentsApi.deploy(effectiveAgentId, {
        scenario_id: result.scenario_id,
      });

      setDeployStep(2);
      setStep('done');

      // Invalidate scenarios query so the new scenario appears
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });

      message.success('Demo deployed successfully!');

      // Navigate to live traffic after a brief moment
      setTimeout(() => {
        onCancel();
        navigate('/live-traffic');
      }, 800);
    } catch (err: unknown) {
      setStep('error');
      const errMsg = err instanceof Error ? err.message : 'An unknown error occurred';
      setError(errMsg);
    }
  };

  const stepItems = [
    { title: 'Creating scenario' },
    { title: 'Deploying to agent' },
    { title: 'Done!' },
  ];

  return (
    <Modal
      open={open}
      onCancel={onCancel}
      title={
        <Space>
          <ThunderboltOutlined style={{ color: '#FBAB18' }} />
          <span>Quick Demo</span>
        </Space>
      }
      footer={
        step === 'select'
          ? [
              <Button key="cancel" onClick={onCancel}>
                Cancel
              </Button>,
              <Button
                key="launch"
                type="primary"
                icon={<RocketOutlined />}
                disabled={!selectedVertical || !effectiveAgentId}
                onClick={handleLaunch}
              >
                Launch Demo
              </Button>,
            ]
          : step === 'error'
            ? [
                <Button key="cancel" onClick={onCancel}>
                  Close
                </Button>,
                <Button key="retry" type="primary" onClick={handleLaunch}>
                  Retry
                </Button>,
              ]
            : null
      }
      width={560}
      styles={{
        header: { background: '#141428', borderBottom: '1px solid #2d2d52' },
        body: { background: '#1a1a2e', padding: 24 },
        content: { background: '#141428' },
      }}
    >
      {step === 'select' && (
        <>
          <Text style={{ color: '#a8a8c0', display: 'block', marginBottom: 16 }}>
            Select an industry vertical and agent to instantly deploy a demo scenario.
          </Text>

          {/* Vertical Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: 12,
              marginBottom: 20,
            }}
          >
            {Object.entries(verticalConfig).map(([key, config]) => {
              const isDisabled = DISABLED_VERTICALS.has(key);
              const isSelected = selectedVertical === key;

              const card = (
                <div
                  key={key}
                  onClick={() => !isDisabled && setSelectedVertical(key)}
                  style={{
                    padding: '16px 12px',
                    borderRadius: 8,
                    border: isSelected
                      ? `2px solid ${config.color}`
                      : '1px solid #2d2d52',
                    background: isSelected ? `${config.color}10` : '#141428',
                    cursor: isDisabled ? 'not-allowed' : 'pointer',
                    opacity: isDisabled ? 0.4 : 1,
                    textAlign: 'center',
                    transition: 'all 0.2s',
                  }}
                >
                  <div
                    style={{
                      fontSize: 24,
                      color: config.color,
                      marginBottom: 6,
                    }}
                  >
                    {config.icon}
                  </div>
                  <Text
                    strong
                    style={{
                      color: '#fff',
                      fontSize: 13,
                      display: 'block',
                    }}
                  >
                    {config.label}
                  </Text>
                </div>
              );

              return isDisabled ? (
                <Tooltip key={key} title="Coming soon — no templates available yet">
                  {card}
                </Tooltip>
              ) : (
                card
              );
            })}
          </div>

          {/* Agent Selector */}
          <div style={{ marginBottom: 8 }}>
            <Text style={{ color: '#a8a8c0', fontSize: 12, display: 'block', marginBottom: 6 }}>
              Deploy to Agent
            </Text>
            {onlineAgents.length === 0 ? (
              <Alert
                type="info"
                showIcon
                message={
                  <span>
                    No agents online.{' '}
                    <Button type="link" size="small" style={{ padding: 0 }} onClick={() => { onCancel(); navigate('/agents'); }}>
                      View Agents
                    </Button>
                  </span>
                }
              />
            ) : (
              <Select
                value={effectiveAgentId}
                onChange={(v) => setSelectedAgentId(v)}
                style={{ width: '100%' }}
                popupClassName="dark-dropdown"
              >
                {onlineAgents.map((agent) => (
                  <Select.Option key={agent.id} value={agent.id}>
                    {agent.name}{agent.hostname ? ` (${agent.hostname})` : ''}
                  </Select.Option>
                ))}
              </Select>
            )}
          </div>
        </>
      )}

      {(step === 'deploying' || step === 'done') && (
        <div style={{ padding: '20px 0' }}>
          <Title level={5} style={{ color: '#fff', textAlign: 'center', marginBottom: 24 }}>
            Setting up your demo...
          </Title>
          <Steps
            current={deployStep}
            items={stepItems.map((item, i) => ({
              ...item,
              icon:
                i < deployStep ? (
                  <CheckCircleOutlined style={{ color: '#52c41a' }} />
                ) : i === deployStep && step !== 'done' ? (
                  <LoadingOutlined />
                ) : undefined,
            }))}
          />
        </div>
      )}

      {step === 'error' && (
        <div style={{ padding: '20px 0' }}>
          <Alert
            type="error"
            showIcon
            message="Demo deployment failed"
            description={error}
          />
        </div>
      )}
    </Modal>
  );
};

export default QuickDemoModal;
