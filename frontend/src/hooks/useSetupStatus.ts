/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Convenience hook for consuming setup state. Mirrors useFeatures.
 *
 *   const { setupComplete, loaded, buildVariant } = useSetupStatus();
 *   if (loaded && !setupComplete) return <SetupWizardPage />;
 */

import { useSetupStatusStore } from '../stores/setupStatusStore';

export function useSetupStatus() {
  const status = useSetupStatusStore((s) => s.status);
  const loaded = useSetupStatusStore((s) => s.loaded);
  return {
    setupComplete: status === null ? true : status.setup_complete,
    buildVariant: status?.build_variant ?? 'full',
    aiSupported: status?.ai_supported ?? true,
    liveTrafficSupported: status?.live_traffic_supported ?? true,
    loaded,
  };
}

export default useSetupStatus;
