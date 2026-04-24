/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Convenience hook for consuming feature flags in components.
 *
 * Usage:
 *   const { aiEnabled } = useFeatures();
 *   if (!aiEnabled) return null;
 */

import { useFeaturesStore } from '../stores/featuresStore';

export function useFeatures() {
  const features = useFeaturesStore((s) => s.features);
  return {
    aiEnabled: features === null ? true : features.ai_enabled,
    loaded: useFeaturesStore((s) => s.loaded),
  };
}

export default useFeatures;
