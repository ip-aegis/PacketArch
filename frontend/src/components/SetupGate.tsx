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
 *
 * When /setup/status cannot be read at all, the gate keeps failing open so a
 * transient blip never bricks an existing install — but it now SAYS SO. Silent
 * fail-open is what turned a network fault into a two-week hunt: nginx could
 * not reach the backend, /setup/status errored, the store swallowed it, the
 * fallback rendered a normal login page, and every login attempt reported
 * "Server error". Nothing on screen pointed at the network.
 */

import React, { useEffect } from 'react';
import { Alert, Spin } from 'antd';
import { useSetupStatusStore } from '../stores/setupStatusStore';
import { useSetupStatus } from '../hooks/useSetupStatus';
import SetupWizardPage from '../pages/SetupWizardPage';

interface Props {
  children: React.ReactNode;
}

/**
 * Persistent, non-dismissable notice that what is on screen is a fallback.
 * Non-dismissable on purpose: the condition it reports does not go away by
 * being acknowledged, and the login below it cannot succeed while it is true.
 */
const BackendUnreachableBanner: React.FC<{ code: number | null }> = ({ code }) => (
  <Alert
    type="error"
    showIcon
    banner
    style={{ position: 'sticky', top: 0, zIndex: 1000 }}
    message={
      code
        ? `Backend unreachable (HTTP ${code})`
        : 'Backend unreachable (no response)'
    }
    description={
      <>
        The web server is running but could not read{' '}
        <code>/api/v1/setup/status</code> from the application, so this page is
        a fallback — logging in will not work until it is fixed.{' '}
        {code === 502 || code === 504 ? (
          <>
            nginx usually reports this when it cannot resolve or reach the{' '}
            <code>backend</code> service.{' '}
          </>
        ) : null}
        On the server, run{' '}
        <code>./scripts/collect-diagnostics.sh</code> and send the file it
        writes. See &ldquo;When the host&rsquo;s network overlaps
        Docker&rsquo;s&rdquo; in DEPLOY.md for the cause behind most of these.
      </>
    }
  />
);

const SetupGate: React.FC<Props> = ({ children }) => {
  const load = useSetupStatusStore((s) => s.load);
  const { setupComplete, loaded, statusUnavailable, statusErrorCode } = useSetupStatus();

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

  // setupComplete here may be the fail-open default rather than a real answer.
  if (statusUnavailable) {
    return (
      <>
        <BackendUnreachableBanner code={statusErrorCode} />
        {children}
      </>
    );
  }

  return <>{children}</>;
};

export default SetupGate;
