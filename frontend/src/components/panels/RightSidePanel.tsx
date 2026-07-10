/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Right Side Panel - AI Assistant, Properties, Deploy, and Attack tabs.
 * Uses icon-only tabs with tooltips and status indicator dots.
 */

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Tabs, Tooltip, Typography, Badge, Input, Button, Divider } from 'antd';
import { ControlOutlined, RobotOutlined, CloudUploadOutlined, ThunderboltOutlined, DoubleRightOutlined } from '@ant-design/icons';
import { TEXT_BODY, TEXT_MUTED, BG_CARD, BG_PANEL, BG_CODE, BORDER_DEFAULT } from '../../constants/theme';
import { PanelContainer, EmptyState, ScenarioModeBadges } from '../common';
import { useUIStore } from '../../stores/uiStore';
import { useAIAssistantStore } from '../../stores/aiAssistantStore';
import { useFeatures } from '../../hooks/useFeatures';
import { useScenarioStore } from '../../stores/scenarioStore';
import { useDeploymentsStore } from '../../stores/deploymentsStore';
import { useAttackStore } from '../../stores/attackStore';
import { scenariosApi } from '../../api/scenarios';
import DevicePropertyForm from './DevicePropertyForm';
import FlowPropertyForm from './FlowPropertyForm';
import ConduitPropertyForm from './ConduitPropertyForm';
import ZonePropertyForm from './ZonePropertyForm';
import ClusterEdgePropertyForm from './ClusterEdgePropertyForm';
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

/** Mode badge row that pulls live state from the scenario store. Reads the
 *  exact same flags the badges in list views read, so the Studio always
 *  matches what other surfaces will show after the next save. */
const StudioModeBadges: React.FC = () => {
  const cleanDemoMode = useScenarioStore((s) => s.cleanDemoMode);
  const broadcastTrafficEnabled = useScenarioStore((s) => s.broadcastTrafficEnabled);
  const cellIsolationMode = useScenarioStore((s) => s.cellIsolation?.mode ?? 'off');
  return (
    <ScenarioModeBadges
      modes={{ cleanDemoMode, broadcastTrafficEnabled, cellIsolationMode }}
      showAll
    />
  );
};

const RightSidePanel: React.FC<RightSidePanelProps> = ({ scenarioId }) => {
  const { aiEnabled } = useFeatures();
  const [activeTab, setActiveTab] = useState(aiEnabled ? 'ai' : 'properties');
  const [generateDescModalOpen, setGenerateDescModalOpen] = useState(false);
  const activePropertyContext = useUIStore((state) => state.activePropertyContext);
  const selectedAggregateEdge = useUIStore((state) => state.selectedAggregateEdge);
  const toggleRightSidebar = useUIStore((s) => s.toggleRightSidebar);

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
  const zonesRecord = useScenarioStore((state) => state.zones);
  const devicesRecord = useScenarioStore((state) => state.devices);

  const zoneSummaries = useMemo(() => {
    const typeLabels: Record<string, string> = {
      vertical: 'Vertical',
      network: 'Network',
      vlan: 'VLAN',
      logical: 'Logical',
    };
    // Devices are the source of truth for zone membership via `zoneId`.
    // The legacy `zone.deviceIds` array is empty on AI/template scenarios,
    // so derive counts by grouping devices.
    const countByZone: Record<string, number> = {};
    for (const id in devicesRecord) {
      const zid = devicesRecord[id].zoneId;
      if (zid) countByZone[zid] = (countByZone[zid] ?? 0) + 1;
    }
    return Object.values(zonesRecord)
      .slice()
      .sort((a, b) => {
        const la = a.level ?? 99;
        const lb = b.level ?? 99;
        if (la !== lb) return la - lb;
        return (a.name ?? '').localeCompare(b.name ?? '');
      })
      .map((zone) => {
        const raw = zone as Record<string, unknown> & typeof zone;
        const network = (raw.network ?? {}) as { subnet?: string; vlanId?: number };
        const subnet = network.subnet ?? (raw.subnet as string | undefined) ?? null;
        const vlanId =
          network.vlanId ?? (raw.vlan as number | undefined) ?? (raw.vlanId as number | undefined);
        const legacyIds = Array.isArray(zone.deviceIds) ? zone.deviceIds : [];
        const deviceCount = countByZone[zone.id] ?? legacyIds.length;
        const parts: string[] = [];
        if (typeof zone.level === 'number') parts.push(`Purdue L${zone.level}`);
        if (zone.type) parts.push(typeLabels[zone.type] ?? zone.type);
        if (vlanId !== undefined) parts.push(`VLAN ${vlanId}`);
        parts.push(`${deviceCount} device${deviceCount === 1 ? '' : 's'}`);
        return {
          id: zone.id,
          name: zone.name ?? zone.id,
          subnet,
          description: parts.join(' · '),
        };
      });
  }, [zonesRecord, devicesRecord]);

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
  const injectionStatusMap = useAttackStore((s) => s.injectionStatus);
  const scenarioInjectionStatus = scenarioId ? (injectionStatusMap[scenarioId] ?? 'idle') : 'idle';
  const hasActiveAttack = deploymentAttackState?.is_active === true;
  const hasConfiguredPlaybook = deploymentAttackState?.playbook_name !== null && !hasActiveAttack;

  // Poll deployments to keep attack state fresh
  useEffect(() => {
    if (!scenarioId) return;

    // Fetch immediately
    fetchDeployments({ scenario_id: scenarioId });

    // Then poll every 3s to update attack state
    const interval = setInterval(() => {
      fetchDeployments({ scenario_id: scenarioId });
    }, 3000);

    return () => clearInterval(interval);
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

  // Ensure the AI session is opened whenever the AI tab is the active tab
  // and a scenario is loaded. Covers the initial-mount case where the AI
  // tab is the default but the tab-change handler never fires — without
  // this the chat input stays disabled (isConnected: false) until the
  // user clicks away from the AI tab and back.
  useEffect(() => {
    if (activeTab === 'ai' && scenarioId && !isAIOpen) {
      openPanel(scenarioId);
    }
  }, [activeTab, scenarioId, isAIOpen, openPanel]);

  // Handle tab change
  const handleTabChange = (activeKey: string) => {
    setActiveTab(activeKey);
    if (activeKey === 'ai' && !isAIOpen && scenarioId) {
      openPanel(scenarioId);
    }
  };

  const handleSaveDescription = async (description: string) => {
    if (!scenarioId) {
      // No scenario yet (shouldn't reach here from the modal). Just
      // update the local store; the create flow will pick it up.
      setMetadata({ description });
      return;
    }

    // Persist immediately instead of waiting on the 2-second auto-save
    // debounce — the AI-description modal closes right away and the
    // user may navigate before the debounce fires, losing the change.
    await scenariosApi.update(scenarioId, { description });
    setMetadata({ description });
    // The change is already on the server; don't leave the studio in a
    // dirty state or the auto-save will re-send the whole definition.
    useScenarioStore.getState().setDirty(false);
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
        <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block', marginBottom: 6 }}>
          Modes
        </Text>
        <StudioModeBadges />
      </div>

      <div style={{ marginBottom: 16 }}>
        <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block', marginBottom: 4 }}>
          Description
        </Text>
        <TextArea
          value={scenarioDescription}
          onChange={(e) => setMetadata({ description: e.target.value })}
          placeholder="Add a description for this scenario..."
          autoSize={{ minRows: 6, maxRows: 14 }}
          style={{
            background: BG_CODE,
            border: `1px solid ${BORDER_DEFAULT}`,
            color: TEXT_BODY,
            resize: 'vertical',
          }}
        />
      </div>

      {zoneSummaries.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <Text style={{ fontSize: 11, color: TEXT_MUTED, display: 'block', marginBottom: 6 }}>
            Zones ({zoneSummaries.length})
          </Text>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {zoneSummaries.map((zone) => (
              <div
                key={zone.id}
                style={{
                  background: BG_CODE,
                  border: `1px solid ${BORDER_DEFAULT}`,
                  borderRadius: 4,
                  padding: '6px 8px',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'baseline',
                    gap: 8,
                  }}
                >
                  <Text style={{ color: TEXT_BODY, fontSize: 12, fontWeight: 500 }}>
                    {zone.name}
                  </Text>
                  <Text
                    style={{
                      color: TEXT_MUTED,
                      fontSize: 11,
                      fontFamily: 'monospace',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {zone.subnet ?? '—'}
                  </Text>
                </div>
                <Text style={{ color: TEXT_MUTED, fontSize: 11, display: 'block' }}>
                  {zone.description}
                </Text>
              </div>
            ))}
          </div>
        </div>
      )}

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
      ) : activePropertyContext.type === 'zone' ? (
        <ZonePropertyForm zoneId={activePropertyContext.ids[0]} />
      ) : activePropertyContext.type === 'conduit' ? (
        <ConduitPropertyForm conduitId={activePropertyContext.ids[0]} />
      ) : activePropertyContext.type === 'clusterEdge' ? (
        selectedAggregateEdge ? (
          <ClusterEdgePropertyForm aggregateInfo={selectedAggregateEdge} />
        ) : (
          scenarioMetadataPanel
        )
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
    <DeploymentPanel scenarioId={scenarioId} scenarioName={scenarioName} />
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
    ...(aiEnabled
      ? [{
          key: 'ai',
          label: tabIcon(
            <RobotOutlined />,
            'AI Assistant',
            isConnected ? '#52c41a' : undefined,
            false,
            pendingActions.length > 0 ? pendingActions.length : undefined,
          ),
          children: aiContent,
        }]
      : []),
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
          position: 'relative',
        }}
      >
        <Tooltip title="Hide panel" placement="left">
          <Button
            type="text"
            size="small"
            icon={<DoubleRightOutlined />}
            onClick={toggleRightSidebar}
            style={{
              position: 'absolute',
              top: 6,
              right: 6,
              zIndex: 2,
              color: TEXT_MUTED,
            }}
          />
        </Tooltip>
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
