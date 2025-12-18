/**
 * AI Scenario Creation Wizard Page
 *
 * Multi-step wizard for AI-powered scenario generation
 */

import React, { useEffect } from 'react';
import { Card, Steps, Button, Space, Typography, Result } from 'antd';
import {
  RobotOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
  CheckOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import { useAIScenarioWizardStore, VERTICALS, VENDORS, PROTOCOLS } from '../stores/aiScenarioWizardStore';
import type { WizardStep } from '../stores/aiScenarioWizardStore';

import NameVerticalStep from '../components/ai-wizard/NameVerticalStep';
import DescriptionStep from '../components/ai-wizard/DescriptionStep';
import DeviceCountStep from '../components/ai-wizard/DeviceCountStep';
import VendorSelectionStep from '../components/ai-wizard/VendorSelectionStep';
import ProtocolSelectionStep from '../components/ai-wizard/ProtocolSelectionStep';
import PreviewStep from '../components/ai-wizard/PreviewStep';

const { Title, Text } = Typography;

const STEPS: { key: WizardStep; title: string }[] = [
  { key: 'name-vertical', title: 'Name & Vertical' },
  { key: 'description', title: 'Description' },
  { key: 'device-count', title: 'Devices' },
  { key: 'vendors', title: 'Vendors' },
  { key: 'protocols', title: 'Protocols' },
  { key: 'preview', title: 'Preview' },
];

const AIScenarioWizardPage: React.FC = () => {
  const navigate = useNavigate();

  const {
    currentStep,
    isGenerating,
    isCreating,
    preview,
    nextStep,
    prevStep,
    canProceed,
    createScenario,
    reset,
  } = useAIScenarioWizardStore();

  // Reset on mount
  useEffect(() => {
    reset();
  }, [reset]);

  const currentStepIndex = STEPS.findIndex(s => s.key === currentStep);

  const handleCancel = () => {
    reset();
    navigate('/scenarios');
  };

  const handleCreate = async () => {
    const scenarioId = await createScenario();
    if (scenarioId) {
      reset();
      navigate(`/studio?scenario=${scenarioId}`);
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 'name-vertical':
        return <NameVerticalStep verticals={VERTICALS} />;
      case 'description':
        return <DescriptionStep />;
      case 'device-count':
        return <DeviceCountStep />;
      case 'vendors':
        return <VendorSelectionStep vendors={VENDORS} />;
      case 'protocols':
        return <ProtocolSelectionStep protocols={PROTOCOLS} />;
      case 'preview':
        return <PreviewStep />;
      default:
        return null;
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', alignItems: 'center', gap: 12 }}>
        <RobotOutlined style={{ fontSize: 32, color: '#5a9fd4' }} />
        <div>
          <Title level={3} style={{ margin: 0, color: '#e0e8f0' }}>
            AI Scenario Creation
          </Title>
          <Text style={{ color: '#8aa4bc' }}>
            Generate OT traffic scenarios using natural language
          </Text>
        </div>
      </div>

      {/* Progress Steps */}
      <Steps
        current={currentStepIndex}
        items={STEPS.map(step => ({ title: step.title }))}
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

      {/* Navigation */}
      <div
        style={{
          marginTop: 24,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Button
          icon={<CloseOutlined />}
          onClick={handleCancel}
          style={{ color: '#8aa4bc' }}
        >
          Cancel
        </Button>

        <Space>
          {currentStep !== 'name-vertical' && (
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={prevStep}
              disabled={isGenerating}
            >
              Back
            </Button>
          )}

          {currentStep !== 'preview' ? (
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
              disabled={!preview || isGenerating}
            >
              Open in Studio
            </Button>
          )}
        </Space>
      </div>
    </div>
  );
};

export default AIScenarioWizardPage;
