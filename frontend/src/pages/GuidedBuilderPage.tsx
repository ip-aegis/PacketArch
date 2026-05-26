/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Guided Scenario Builder — full-page 6-step wizard.
 *
 * Flow: vertical → template → review devices → customize → review flows → finalize.
 */

import React, { useEffect } from 'react';
import { Card, Steps, Button, Space, Typography, App } from 'antd';
import {
  CompassOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
  CheckOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import { useGuidedBuilderStore, WIZARD_STEPS } from '../stores/guidedBuilderStore';

import VerticalSelectStep from '../components/guided-builder/VerticalSelectStep';
import TemplateSelectStep from '../components/guided-builder/TemplateSelectStep';
import DeviceReviewStep from '../components/guided-builder/DeviceReviewStep';
import DeviceCustomizeStep from '../components/guided-builder/DeviceCustomizeStep';
import FlowReviewStep from '../components/guided-builder/FlowReviewStep';
import FinalizeStep from '../components/guided-builder/FinalizeStep';
import ContextualHelpIcon from '../components/help/ContextualHelpIcon';

const { Title, Text } = Typography;

const GuidedBuilderPage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();

  const {
    currentStep,
    isCreating,
    createError,
    nextStep,
    prevStep,
    canProceed,
    createScenario,
    reset,
  } = useGuidedBuilderStore();

  // Reset on mount
  useEffect(() => {
    reset();
  }, [reset]);

  const currentStepIndex = WIZARD_STEPS.findIndex((s) => s.key === currentStep);

  const handleCancel = () => {
    reset();
    navigate('/scenarios');
  };

  const handleCreate = async () => {
    const scenarioId = await createScenario();
    if (scenarioId) {
      message.success('Scenario created successfully');
      reset();
      navigate(`/studio?scenario=${scenarioId}`);
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 'vertical':
        return <VerticalSelectStep />;
      case 'template':
        return <TemplateSelectStep />;
      case 'review-devices':
        return <DeviceReviewStep />;
      case 'customize':
        return <DeviceCustomizeStep />;
      case 'review-flows':
        return <FlowReviewStep />;
      case 'finalize':
        return <FinalizeStep />;
      default:
        return null;
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', alignItems: 'center', gap: 12 }}>
        <CompassOutlined style={{ fontSize: 32, color: '#049FD9' }} />
        <div>
          <Title level={3} style={{ margin: 0, color: '#e0e8f0' }}>
            Guided Scenario Builder
            <ContextualHelpIcon articleId="guided-builder" tooltip="Guided builder help" />
          </Title>
          <Text style={{ color: '#8aa4bc' }}>
            Build a scenario step-by-step from industry templates
          </Text>
        </div>
      </div>

      {/* Progress Steps */}
      <Steps
        current={currentStepIndex}
        items={WIZARD_STEPS.map((step) => ({ title: step.title }))}
        style={{ marginBottom: 24 }}
      />

      {/* Step Content */}
      <Card
        style={{
          backgroundColor: '#1a2734',
          border: '1px solid #2a3f54',
          minHeight: 400,
        }}
        styles={{ body: { padding: 24 } }}
      >
        {renderStepContent()}
      </Card>

      {/* Error display */}
      {createError && (
        <div style={{ marginTop: 12, color: '#ff4d4f', fontSize: 13 }}>
          {createError}
        </div>
      )}

      {/* Navigation */}
      <div
        style={{
          marginTop: 24,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Button icon={<CloseOutlined />} onClick={handleCancel} style={{ color: '#8aa4bc' }}>
          Cancel
        </Button>

        <Space>
          {currentStep !== 'vertical' && (
            <Button icon={<ArrowLeftOutlined />} onClick={prevStep} disabled={isCreating}>
              Back
            </Button>
          )}

          {currentStep !== 'finalize' ? (
            <Button
              type="primary"
              icon={<ArrowRightOutlined />}
              onClick={nextStep}
              disabled={!canProceed()}
            >
              Next
            </Button>
          ) : (
            <Button
              type="primary"
              icon={<CheckOutlined />}
              onClick={handleCreate}
              loading={isCreating}
              disabled={!canProceed()}
            >
              Create &amp; Open in Studio
            </Button>
          )}
        </Space>
      </div>
    </div>
  );
};

export default GuidedBuilderPage;
