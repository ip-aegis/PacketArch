/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Redirect away from a route when a feature is disabled.
 *
 * Used in App.tsx to prevent users from landing on AI pages in deployments
 * that have AI turned off. Fail-open while features are still loading so
 * that a slow /about response doesn't flash-redirect the user.
 */

import React from 'react';
import { Navigate } from 'react-router-dom';
import { useFeatures } from '../hooks/useFeatures';

type FeatureName = 'ai' | 'liveTraffic';

interface FeatureGateProps {
  feature: FeatureName;
  fallback?: string;
  children: React.ReactNode;
}

const FeatureGate: React.FC<FeatureGateProps> = ({
  feature,
  fallback = '/',
  children,
}) => {
  const { aiEnabled, liveTrafficEnabled, loaded } = useFeatures();

  if (!loaded) return <>{children}</>;

  const enabled =
    feature === 'ai' ? aiEnabled : feature === 'liveTraffic' ? liveTrafficEnabled : true;

  if (!enabled) {
    return <Navigate to={fallback} replace />;
  }

  return <>{children}</>;
};

export default FeatureGate;
