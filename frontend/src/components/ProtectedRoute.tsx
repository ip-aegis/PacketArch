/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Protected route component for authentication
 */

import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuthStore } from '../stores/authStore';
import { getAccessToken } from '../api/client';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

// Module-level flag: have we round-tripped to the server during this app
// load to confirm the persisted session is still valid? We need to do
// that exactly ONCE per app load — not on every nested ProtectedRoute
// mount, otherwise navigating to /admin/settings (which has a nested
// `<ProtectedRoute requireAdmin>` inside the outer one) shows a spinner
// flash on every click. The shared `bootPromise` deduplicates concurrent
// callers (e.g. outer + inner mounting in the same tick).
let initialAuthCheckDone = false;
let bootPromise: Promise<void> | null = null;

function runInitialAuthCheck(fetchCurrentUser: () => Promise<void>): Promise<void> {
  if (initialAuthCheckDone) return Promise.resolve();
  if (bootPromise) return bootPromise;
  const token = getAccessToken();
  if (!token) {
    initialAuthCheckDone = true;
    return Promise.resolve();
  }
  bootPromise = fetchCurrentUser()
    .catch(() => {
      // fetchCurrentUser already handles its own error state (clears
      // tokens + sets isAuthenticated=false). We just need to swallow
      // so the boot promise resolves.
    })
    .finally(() => {
      initialAuthCheckDone = true;
      bootPromise = null;
    });
  return bootPromise;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireAdmin = false,
}) => {
  const location = useLocation();
  const { user, isAuthenticated, isLoading, fetchCurrentUser } = useAuthStore();
  const [checking, setChecking] = useState(!initialAuthCheckDone);

  // Run the server-side auth check exactly once per app load. Subsequent
  // ProtectedRoute mounts (e.g. clicking a sidebar link) skip the check
  // and trust the in-memory auth state — the axios interceptor in
  // api/client.ts handles silent refresh on the next 401, and a
  // refresh-failure there hard-redirects to /login. The OLD pre-1.4
  // behavior trusted a persisted `isAuthenticated=true` flag across
  // reloads and painted the app shell before the server had spoken,
  // which is what let an overnight-idle tab bypass /login.
  useEffect(() => {
    if (initialAuthCheckDone) {
      setChecking(false);
      return;
    }
    let cancelled = false;
    runInitialAuthCheck(fetchCurrentUser).finally(() => {
      if (!cancelled) setChecking(false);
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Spinner only while the FIRST check is in flight. Subsequent mounts
  // never see `checking=true` because initialAuthCheckDone is already
  // set, so nested ProtectedRoutes (e.g. /admin/settings) render
  // instantly off the in-memory store.
  if (checking || isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  const token = getAccessToken();

  // If not authenticated, redirect to login. We check `isAuthenticated`
  // (server-confirmed during boot) rather than just the token's presence —
  // a stale token whose /auth/me 401'd lands here and gets bounced.
  if (!token || !isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Admin gate: require an explicit is_admin=true. We DON'T render any
  // admin page if `user` isn't loaded yet (the gate must fail closed,
  // not pass through a brief !user window).
  if (requireAdmin && (!user || !user.is_admin)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
