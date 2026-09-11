/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * The configured Cyber Vision Centers, loaded on first use (the store shares
 * one request across every component that asks at mount).
 *
 * `multiCenter` is the switch for every "which center?" UI: with a single
 * center there is nothing to choose, so pickers and center labels stay hidden.
 */

import { useEffect } from 'react';
import { useCyberVisionStore } from '../stores/cyberVisionStore';

export function useCyberVisionCenters() {
  const centers = useCyberVisionStore((s) => s.centers);
  const centersLoaded = useCyberVisionStore((s) => s.centersLoaded);
  const fetchCenters = useCyberVisionStore((s) => s.fetchCenters);

  useEffect(() => {
    if (!centersLoaded) fetchCenters();
  }, [centersLoaded, fetchCenters]);

  return {
    centers,
    centersLoaded,
    multiCenter: centers.length > 1,
    configured: centers.some((c) => c.api_token_set),
  };
}

export default useCyberVisionCenters;
