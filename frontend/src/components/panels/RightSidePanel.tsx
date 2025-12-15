/**
 * Right Side Panel - Combined Properties, Realism, Deploy, and AI Assistant tabs
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Tabs, Typography, Empty, Badge } from 'antd';
import { ControlOutlined, RobotOutlined, CloudUploadOutlined, ExperimentOutlined } from '@ant-design/icons';
import { useUIStore } from '../../stores/uiStore';
import { useAIAssistantStore } from '../../stores/aiAssistantStore';
import DevicePropertyForm from './DevicePropertyForm';
import FlowPropertyForm from './FlowPropertyForm';
import ChatInterface from '../ai/ChatInterface';
import ChatInput from '../ai/ChatInput';
import DeploymentPanel from '../deployment/DeploymentPanel';
import RealisticSettingsPanel from '../realism/RealisticSettingsPanel';

const { Text } = Typography;

interface RightSidePanelProps {
  scenarioId: string | null;
}

const RightSidePanel: React.FC<RightSidePanelProps> = ({ scenarioId }) => {
  const [activeTab, setActiveTab] = useState('properties');
  const navigate = useNavigate();
  const activePropertyContext = useUIStore((state) => state.activePropertyContext);

  const {
    isOpen: isAIOpen,
    isConnected,
    isProcessing,
    pendingActions,
    openPanel,
  } = useAIAssistantStore();

  // Handle tab change - open AI session when switching to AI tab
  const handleTabChange = (activeKey: string) => {
    setActiveTab(activeKey);
    if (activeKey === 'ai' && !isAIOpen && scenarioId) {
      openPanel(scenarioId);
    }
  };

  const propertiesContent = (
    <div style={{ padding: '16px', height: '100%', overflowY: 'auto' }}>
      {!activePropertyContext.type || activePropertyContext.ids.length === 0 ? (
        <Empty
          image={<ControlOutlined style={{ fontSize: 48, color: '#4a6a8a' }} />}
          description={
            <div>
              <Text style={{ fontSize: '13px', color: '#8aa4bc' }}>
                No selection
              </Text>
              <div style={{ marginTop: '8px' }}>
                <Text style={{ fontSize: '11px', color: '#6a8caf' }}>
                  Click on a device or flow to view and edit its properties
                </Text>
              </div>
            </div>
          }
          style={{ marginTop: '60px' }}
        />
      ) : activePropertyContext.type === 'device' ? (
        <DevicePropertyForm deviceId={activePropertyContext.ids[0]} />
      ) : activePropertyContext.type === 'flow' ? (
        <FlowPropertyForm flowId={activePropertyContext.ids[0]} />
      ) : activePropertyContext.type === 'multi' ? (
        <Empty
          description={
            <div>
              <Text style={{ fontSize: '13px', color: '#8aa4bc' }}>
                Multiple items selected
              </Text>
              <div style={{ marginTop: '8px' }}>
                <Text style={{ fontSize: '11px', color: '#6a8caf' }}>
                  Bulk editing is not yet supported
                </Text>
              </div>
            </div>
          }
          style={{ marginTop: '60px' }}
        />
      ) : null}
    </div>
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
          backgroundColor: '#1e2d3d',
        }}
      >
        <ChatInterface />
      </div>

      {/* Input area - fixed at bottom */}
      <div
        style={{
          padding: '12px',
          backgroundColor: '#1a2734',
          borderTop: '1px solid #2a3f54',
        }}
      >
        <ChatInput disabled={!isConnected || isProcessing} />
      </div>
    </div>
  );

  const deployContent = (
    <DeploymentPanel scenarioId={scenarioId} />
  );

  const realismContent = (
    <RealisticSettingsPanel
      scenarioId={scenarioId}
      onOpenPcapLearning={() => navigate('/learning')}
    />
  );

  const items = [
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
      key: 'realism',
      label: (
        <span>
          <ExperimentOutlined /> Realism
        </span>
      ),
      children: realismContent,
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
      key: 'ai',
      label: (
        <span style={{ color: isConnected ? '#52c41a' : undefined }}>
          <RobotOutlined /> AI
          {pendingActions.length > 0 && (
            <Badge dot style={{ marginLeft: 4 }} />
          )}
        </span>
      ),
      children: aiContent,
    },
  ];

  return (
    <div
      style={{
        width: '360px',
        height: '100%',
        background: '#1e2d3d',
        borderLeft: '1px solid #2a3f54',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Tabs
        activeKey={activeTab}
        onChange={handleTabChange}
        items={items}
        destroyInactiveTabPane
        style={{ height: '100%' }}
        tabBarStyle={{
          margin: 0,
          padding: '0 12px',
          background: '#1a2734',
          borderBottom: '1px solid #2a3f54',
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
  );
};

export default RightSidePanel;
