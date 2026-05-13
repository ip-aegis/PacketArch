/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Top-level gate that decides between rendering the first-run setup wizard
 * and the normal app shell. Mounted in App.tsx to wrap the route tree.
 *
 * Loads /api/v1/setup/status once on app boot. While loading, renders a
 * spinner. Once loaded:
 *   - setup_complete=false  → render <SetupWizardPage /> regardless of route
 *   - setup_complete=true   → render the children (the normal <Routes/>)
 *
 * The setup wizard URL itself is not route-driven — any path browses to the
 * wizard while incomplete. This keeps the public surface minimal.
 */

import React, { useEffect } from 'react';
import { Spin } from 'antd';
import { useSetupStatusStore } from '../stores/setupStatusStore';
import { useSetupStatus } from '../hooks/useSetupStatus';
import SetupWizardPage from '../pages/SetupWizardPage';

interface Props {
  children: React.ReactNode;
}

const SetupGate: React.FC<Props> = ({ children }) => {
  const load = useSetupStatusStore((s) => s.load);
  const { setupComplete, loaded } = useSetupStatus();

  useEffect(() => {
    load();
  }, [load]);

  if (!loaded) {
    return (
      <div
        style={{
          display: 'flex',
          minHeight: '100vh',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#0d0d1f',
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (!setupComplete) {
    return <SetupWizardPage />;
  }

  return <>{children}</>;
};

export default SetupGate;
