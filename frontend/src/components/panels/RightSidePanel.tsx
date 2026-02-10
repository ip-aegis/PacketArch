/**
 * Right Side Panel - AI Assistant, Properties, and Deploy tabs
 */

import React, { useState, useEffect, useRef } from 'react';
import { Tabs, Typography, Badge, Input, Button, Space, Divider } from 'antd';
import { ControlOutlined, RobotOutlined, CloudUploadOutlined, EditOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { TEXT_BODY, TEXT_MUTED, BG_CARD, BG_PANEL, BG_CODE, BORDER_DEFAULT } from '../../constants/theme';
import { PanelContainer, EmptyState } from '../common';
import { useUIStore } from '../../stores/uiStore';
import { useAIAssistantStore } from '../../stores/aiAssistantStore';
import { useScenarioStore } from '../../stores/scenarioStore';
import DevicePropertyForm from './DevicePropertyForm';
import FlowPropertyForm from './FlowPropertyForm';
import ChatInterface from '../ai/ChatInterface';
import ChatInput from '../ai/ChatInput';
import DeploymentPanel from '../deployment/DeploymentPanel';
import AttackPanel from '../attack/AttackPanel';
import GenerateDescriptionModal from '../ai/GenerateDescriptionModal';

const { Text } = Typography;
const { TextArea } = Input;

interface RightSidePanelProps {
  scenarioId: string | null;
}

const RightSidePanel: React.FC<RightSidePanelProps> = ({ scenarioId }) => {
  const [activeTab, setActiveTab] = useState('ai');
  const [generateDescModalOpen, setGenerateDescModalOpen] = useState(false);
  const activePropertyContext = useUIStore((state) => state.activePropertyContext);

  const {
    isOpen: isAIOpen,
    isConnected,
    isProcessing,
    pendingActions,
    openPanel,
  } = useAIAssistantStore();

  // Scenario metadata from store
  const scenarioName = useScenarioStore((state) => state.name);
  const scenarioDescription = useScenarioStore((state) => state.description);
  const setMetadata = useScenarioStore((state) => state.setMetadata);

  // Auto-switch to Properties tab when a device or flow is selected
  const prevContextType = useRef(activePropertyContext.type);
  useEffect(() => {
    if (
      activePropertyContext.type &&
      activePropertyContext.type !== 'multi' &&
      activePropertyContext.ids.length > 0 &&
      prevContextType.current !== activePropertyContext.type
    ) {
      setActiveTab('properties');
    }
    prevContextType.current = activePropertyContext.type;
  }, [activePropertyContext.type, activePropertyContext.ids]);

  // Handle tab change - open AI session when switching to AI tab
  const handleTabChange = (activeKey: string) => {
    setActiveTab(activeKey);
    if (activeKey === 'ai' && !isAIOpen && scenarioId) {
      openPanel(scenarioId);
    }
  };

  // Handle description save from modal
  const handleSaveDescription = async (description: string) => {
    setMetadata({ description });
  };

  // Scenario metadata panel shown when nothing is selected
  const scenarioMetadataPanel = (
    <div>
      <Text strong style={{ color: TEXT_BODY, display: 'block', marginBottom: 16 }}>
        Scenario Properties
      </Text>

      <div style={{ marginBottom: 16 }}>
        <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block', marginBottom: 4 }}>
          Name
        </Text>
        <Text style={{ color: TEXT_BODY }}>{scenarioName}</Text>
      </div>

      <div style={{ marginBottom: 16 }}>
        <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block', marginBottom: 4 }}>
          Description
        </Text>
        <TextArea
          rows={3}
          value={scenarioDescription}
          onChange={(e) => setMetadata({ description: e.target.value })}
          placeholder="Add a description for this scenario..."
          style={{
            background: BG_CODE,
            border: `1px solid ${BORDER_DEFAULT}`,
            color: TEXT_BODY,
            resize: 'vertical',
          }}
        />
      </div>

      {scenarioId && (
        <Button
          type="default"
          icon={<RobotOutlined />}
          onClick={() => setGenerateDescModalOpen(true)}
          style={{
            borderColor: '#1890ff',
            color: '#1890ff',
          }}
          block
        >
          Generate with AI
        </Button>
      )}

      <Divider style={{ borderColor: BORDER_DEFAULT, margin: '20px 0' }} />

      <Text style={{ fontSize: 11, color: TEXT_MUTED }}>
        Select a device or flow to edit its properties
      </Text>
    </div>
  );

  const propertiesContent = (
    <PanelContainer>
      {!activePropertyContext.type || activePropertyContext.ids.length === 0 ? (
        scenarioMetadataPanel
      ) : activePropertyContext.type === 'device' ? (
        <DevicePropertyForm deviceId={activePropertyContext.ids[0]} />
      ) : activePropertyContext.type === 'flow' ? (
        <FlowPropertyForm flowId={activePropertyContext.ids[0]} />
      ) : activePropertyContext.type === 'multi' ? (
        <EmptyState
          message="Multiple items selected"
          hint="Bulk editing is not yet supported"
        />
      ) : null}
    </PanelContainer>
  );

  const aiContent = (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
      }}
    >
      {/* Chat messages - scrollable area */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px',
          backgroundColor: BG_CARD,
        }}
      >
        <ChatInterface />
      </div>

      {/* Input area - fixed at bottom */}
      <div
        style={{
          padding: '12px',
          backgroundColor: BG_PANEL,
          borderTop: `1px solid ${BORDER_DEFAULT}`,
        }}
      >
        <ChatInput disabled={!isConnected || isProcessing} />
      </div>
    </div>
  );

  const deployContent = (
    <DeploymentPanel scenarioId={scenarioId} />
  );

  const attackContent = (
    <AttackPanel scenarioId={scenarioId} />
  );

  const items = [
    {
      key: 'ai',
      label: (
        <span style={{ color: isConnected ? '#52c41a' : undefined }}>
          <RobotOutlined /> AI Assistant
          {pendingActions.length > 0 && (
            <Badge dot style={{ marginLeft: 4 }} />
          )}
        </span>
      ),
      children: aiContent,
    },
    {
      key: 'properties',
      label: (
        <span>
          <ControlOutlined /> Properties
        </span>
      ),
      children: propertiesContent,
    },
    {
      key: 'deploy',
      label: (
        <span>
          <CloudUploadOutlined /> Deploy
        </span>
      ),
      children: deployContent,
    },
    {
      key: 'attack',
      label: (
        <span>
          <ThunderboltOutlined /> Attack
        </span>
      ),
      children: attackContent,
    },
  ];

  return (
    <>
      <div
        style={{
          width: '360px',
          height: '100%',
          background: BG_CARD,
          borderLeft: `1px solid ${BORDER_DEFAULT}`,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Tabs
          activeKey={activeTab}
          onChange={handleTabChange}
          items={items}
          destroyInactiveTabPane={false}
          style={{ height: '100%' }}
          tabBarStyle={{
            margin: 0,
            padding: '0 12px',
            background: BG_PANEL,
            borderBottom: `1px solid ${BORDER_DEFAULT}`,
          }}
          className="right-side-panel-tabs"
        />
        <style>{`
          .right-side-panel-tabs .ant-tabs-content-holder {
            display: flex;
            flex-direction: column;
            overflow: hidden;
          }
          .right-side-panel-tabs .ant-tabs-content {
            height: 100%;
          }
          .right-side-panel-tabs .ant-tabs-tabpane {
            height: 100%;
            display: flex;
            flex-direction: column;
          }
          .right-side-panel-tabs .ant-tabs-nav {
            margin-bottom: 0;
          }
          .right-side-panel-tabs .ant-tabs-tab {
            color: #8aa4bc;
          }
          .right-side-panel-tabs .ant-tabs-tab-active .ant-tabs-tab-btn {
            color: #5a9fd4;
          }
        `}</style>
      </div>

      {/* Generate Description Modal */}
      {scenarioId && (
        <GenerateDescriptionModal
          open={generateDescModalOpen}
          onClose={() => setGenerateDescModalOpen(false)}
          onSave={handleSaveDescription}
          scenarioId={scenarioId}
          scenarioName={scenarioName}
          currentDescription={scenarioDescription || undefined}
        />
      )}
    </>
  );
};

export default RightSidePanel;
