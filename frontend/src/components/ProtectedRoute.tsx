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

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireAdmin = false,
}) => {
  const location = useLocation();
  const { user, isAuthenticated, isLoading, fetchCurrentUser } = useAuthStore();
  const [checking, setChecking] = useState(true);

  // On every mount (cold reload, tab restore, route nav), ALWAYS round-trip
  // to the server before rendering. The old behavior trusted the
  // `isAuthenticated` flag persisted in localStorage and painted the app
  // shell before the server confirmed the session — which let an
  // overnight-idle tab bypass the login page. We now treat the cached
  // user as decorative (for username/avatar only) and require a fresh
  // /auth/me before this route is considered authenticated.
  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setChecking(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        await fetchCurrentUser();
      } finally {
        if (!cancelled) setChecking(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // We want this to run once per mount. fetchCurrentUser is stable.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Show loading while checking authentication (either our gate or the
  // store's). Keeps the app shell hidden until the server has spoken.
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
  // (server-confirmed) rather than just the token's presence — a stale
  // token with a deactivated user gets bounced to /login.
  if (!token || !isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If admin required but user is not admin, redirect to home
  if (requireAdmin && user && !user.is_admin) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
