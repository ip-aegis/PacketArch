/**
 * Right Side Panel - AI Assistant, Properties, Deploy, and Attack tabs.
 * Uses icon-only tabs with tooltips and status indicator dots.
 */

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Tabs, Tooltip, Typography, Badge, Input, Button, Divider } from 'antd';
import { ControlOutlined, RobotOutlined, CloudUploadOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { TEXT_BODY, TEXT_MUTED, BG_CARD, BG_PANEL, BG_CODE, BORDER_DEFAULT } from '../../constants/theme';
import { PanelContainer, EmptyState } from '../common';
import { useUIStore } from '../../stores/uiStore';
import { useAIAssistantStore } from '../../stores/aiAssistantStore';
import { useScenarioStore } from '../../stores/scenarioStore';
import { useDeploymentsStore } from '../../stores/deploymentsStore';
import { useAttackStore } from '../../stores/attackStore';
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

  // Deployment state
  const deployments = useDeploymentsStore((state) => state.deployments);
  const fetchDeployments = useDeploymentsStore((state) => state.fetchDeployments);

  const activeDeployment = useMemo(
    () => deployments.find(
      (d) => d.scenario_id === scenarioId && d.status === 'running',
    ),
    [deployments, scenarioId],
  );
  const isDeployed = !!activeDeployment;

  // Attack state from deployment (not global store)
  const deploymentAttackState = activeDeployment?.attack ?? null;
  const selectedPlaybook = useAttackStore((s) => s.selectedPlaybook);
  const injectionStatusMap = useAttackStore((s) => s.injectionStatus);
  const scenarioInjectionStatus = scenarioId ? (injectionStatusMap[scenarioId] ?? 'idle') : 'idle';
  const hasActiveAttack = deploymentAttackState?.is_active === true;
  const hasConfiguredPlaybook = deploymentAttackState?.playbook_name !== null && !hasActiveAttack;

  // Ensure deployments are loaded
  useEffect(() => {
    if (scenarioId) {
      fetchDeployments({ scenario_id: scenarioId });
    }
  }, [scenarioId, fetchDeployments]);

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

  // Auto-switch to Attack tab when injection is confirmed
  useEffect(() => {
    if (scenarioInjectionStatus === 'confirmed') {
      setActiveTab('attack');
    }
  }, [scenarioInjectionStatus]);

  // Handle tab change
  const handleTabChange = (activeKey: string) => {
    setActiveTab(activeKey);
    if (activeKey === 'ai' && !isAIOpen && scenarioId) {
      openPanel(scenarioId);
    }
  };

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
    <AttackPanel
      scenarioId={scenarioId}
      deploymentId={activeDeployment?.id}
      isDeployed={isDeployed}
      deploymentAgentName={activeDeployment?.agent_name ?? undefined}
      deploymentStatus={activeDeployment?.status}
      attackState={deploymentAttackState}
    />
  );

  /** Icon-only tab label with optional status dot */
  const tabIcon = (
    icon: React.ReactNode,
    tooltip: string,
    dotColor?: string,
    pulse?: boolean,
    badgeCount?: number,
  ) => (
    <Tooltip title={tooltip} placement="bottom">
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, position: 'relative' }}>
        {icon}
        {dotColor && (
          <span
            className={pulse ? (dotColor === '#ff4d4f' ? 'status-dot-pulse-red' : 'status-dot-pulse-green') : undefined}
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: dotColor,
              display: 'inline-block',
            }}
          />
        )}
        {badgeCount != null && badgeCount > 0 && (
          <Badge count={badgeCount} size="small" style={{ fontSize: 8 }} />
        )}
      </span>
    </Tooltip>
  );

  const items = [
    {
      key: 'ai',
      label: tabIcon(
        <RobotOutlined />,
        'AI Assistant',
        isConnected ? '#52c41a' : undefined,
        false,
        pendingActions.length > 0 ? pendingActions.length : undefined,
      ),
      children: aiContent,
    },
    {
      key: 'properties',
      label: tabIcon(<ControlOutlined />, 'Properties'),
      children: propertiesContent,
    },
    {
      key: 'deploy',
      label: tabIcon(
        <CloudUploadOutlined />,
        'Deploy',
        isDeployed ? '#52c41a' : undefined,
        isDeployed,
      ),
      children: deployContent,
    },
    {
      key: 'attack',
      label: tabIcon(
        <ThunderboltOutlined />,
        'Attack',
        hasActiveAttack ? '#ff4d4f' : hasConfiguredPlaybook ? '#fa8c16' : undefined,
        hasActiveAttack,
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
            padding: '0 8px',
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
          .right-side-panel-tabs .ant-tabs-tabpane-active {
            height: 100%;
            display: flex !important;
            flex-direction: column;
          }
          .right-side-panel-tabs .ant-tabs-nav {
            margin-bottom: 0;
          }
          .right-side-panel-tabs .ant-tabs-nav-list {
            justify-content: space-around;
            width: 100%;
          }
          .right-side-panel-tabs .ant-tabs-tab {
            color: #8aa4bc;
            padding: 10px 0;
            margin: 0 !important;
            flex: 1;
            justify-content: center;
          }
          .right-side-panel-tabs .ant-tabs-tab-active .ant-tabs-tab-btn {
            color: #5a9fd4;
          }
          .right-side-panel-tabs .ant-tabs-ink-bar {
            height: 2px;
            background: #5a9fd4;
          }

          @keyframes pulse-green-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
          }
          @keyframes pulse-red-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
          }
          @keyframes pulse-green {
            0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(82, 196, 106, 0.4); }
            50% { opacity: 0.7; box-shadow: 0 0 0 3px rgba(82, 196, 106, 0); }
          }
          .status-dot-pulse-green {
            animation: pulse-green-dot 2s ease-in-out infinite;
          }
          .status-dot-pulse-red {
            animation: pulse-red-dot 1.5s ease-in-out infinite;
          }
        `}</style>
      </div>

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
