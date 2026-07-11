/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Convenience hook for consuming feature flags in components.
 *
 * Usage:
 *   const { aiEnabled, liveTrafficEnabled } = useFeatures();
 *   if (!aiEnabled) return null;
 *
 * Defaults to fail-open (true) while /about is still loading so a slow
 * response doesn't flash-redirect users away from gated pages on full builds.
 */

import { useFeaturesStore } from '../stores/featuresStore';

export function useFeatures() {
  const features = useFeaturesStore((s) => s.features);
  return {
    aiEnabled: features === null ? true : features.ai_enabled,
    liveTrafficEnabled: features === null ? true : features.live_traffic_enabled,
    // Experimental — fail CLOSED (default off) so the Advanced Deployment UI
    // stays hidden unless the backend explicitly enables it.
    multiSensorTopologyEnabled:
      features === null ? false : features.multi_sensor_topology_enabled,
    loaded: useFeaturesStore((s) => s.loaded),
  };
}

export default useFeatures;
