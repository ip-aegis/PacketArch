/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 Run workspace — deploy-to-agent and attack simulation get
 * real estate instead of a cramped tab. Re-homes the proven v1
 * DeploymentPanel / AttackPanel components inside the v2 shell.
 */

import React, { useEffect, useMemo, useState } from 'react';
import DeploymentPanel from '../../components/deployment/DeploymentPanel';
import AttackPanel from '../../components/attack/AttackPanel';
import { useDeploymentsStore } from '../../stores/deploymentsStore';
import { useDocumentStore } from '../document/documentStore';
import { useFeatures } from '../../hooks/useFeatures';
import { SURFACE, TEXT, ACCENT, ACCENT_SOFT, FONT } from '../tokens';

const PANEL_WIDTH = 400;

const RunPanel: React.FC = () => {
  const scenarioId = useDocumentStore((s) => s.doc?.meta.id ?? null);
  const docPhases = useDocumentStore((s) => s.doc?.phases);
  const [tab, setTab] = useState<'deploy' | 'attack'>('deploy');
  const { liveTrafficEnabled } = useFeatures();

  const deployments = useDeploymentsStore((s) => s.deployments);
  const fetchDeployments = useDeploymentsStore((s) => s.fetchDeployments);

  useEffect(() => {
    if (scenarioId && liveTrafficEnabled) {
      void fetchDeployments({ scenario_id: scenarioId });
    }
  }, [scenarioId, liveTrafficEnabled, fetchDeployments]);

  const activeDeployment = useMemo(
    () => deployments.find((d) => d.scenario_id === scenarioId && d.status === 'running'),
    [deployments, scenarioId],
  );

  if (!liveTrafficEnabled) {
    return (
      <div
        style={{
          width: PANEL_WIDTH,
          flex: `0 0 ${PANEL_WIDTH}px`,
          background: SURFACE.chrome,
          borderLeft: `1px solid ${SURFACE.border}`,
          padding: 20,
          fontFamily: FONT.ui,
          fontSize: 12.5,
          color: TEXT.muted,
          lineHeight: 1.6,
        }}
      >
        Live traffic is disabled in this build — the Run workspace needs the agent platform.
        PCAP generation stays available from the Scenarios page.
      </div>
    );
  }

  return (
    <div
      style={{
        width: PANEL_WIDTH,
        flex: `0 0 ${PANEL_WIDTH}px`,
        display: 'flex',
        flexDirection: 'column',
        background: SURFACE.chrome,
        borderLeft: `1px solid ${SURFACE.border}`,
        fontFamily: FONT.ui,
        minHeight: 0,
      }}
    >
      <div
        style={{
          display: 'flex',
          gap: 2,
          padding: 8,
          borderBottom: `1px solid ${SURFACE.border}`,
        }}
        role="tablist"
        aria-label="Run workspace"
      >
        {(['deploy', 'attack'] as const).map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            style={{
              flex: 1,
              background: tab === t ? ACCENT_SOFT : 'transparent',
              color: tab === t ? ACCENT : TEXT.muted,
              border: 'none',
              borderRadius: 6,
              fontFamily: FONT.ui,
              fontSize: 12,
              fontWeight: 600,
              padding: '5px 0',
              cursor: 'pointer',
              textTransform: 'capitalize',
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
        {tab === 'deploy' ? (
          <DeploymentPanel scenarioId={scenarioId} phases={docPhases} />
        ) : (
          <AttackPanel
            scenarioId={scenarioId}
            deploymentId={activeDeployment?.id}
            isDeployed={!!activeDeployment}
            deploymentAgentName={activeDeployment?.agent_name ?? undefined}
            deploymentStatus={activeDeployment?.status}
            attackState={activeDeployment?.attack ?? null}
          />
        )}
      </div>
    </div>
  );
};

export default RunPanel;
