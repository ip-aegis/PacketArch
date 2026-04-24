/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Traffic profile presets per protocol.
 * Values sourced from LEARNED_DEFAULTS in backend/app/scenario_templates/base.py.
 */

export interface TrafficPreset {
  key: string;
  label: string;
  description: string;
  timing: {
    intervalMs: number;
    jitterMs: number;
    burstSize?: number;
    burstIntervalMs?: number;
  };
}

export type PresetKey = 'normal' | 'high_speed' | 'maintenance' | 'degraded';

const PRESETS: Record<string, Record<PresetKey, TrafficPreset>> = {
  modbus_tcp: {
    normal: {
      key: 'normal',
      label: 'Normal',
      description: 'Standard Modbus polling (~100ms)',
      timing: { intervalMs: 100, jitterMs: 10 },
    },
    high_speed: {
      key: 'high_speed',
      label: 'High-Speed',
      description: 'Fast Modbus polling (~50ms)',
      timing: { intervalMs: 50, jitterMs: 5 },
    },
    maintenance: {
      key: 'maintenance',
      label: 'Maintenance',
      description: 'Slow polling during maintenance (~500ms)',
      timing: { intervalMs: 500, jitterMs: 50 },
    },
    degraded: {
      key: 'degraded',
      label: 'Degraded',
      description: 'Degraded network conditions (~200ms, high jitter)',
      timing: { intervalMs: 200, jitterMs: 80 },
    },
  },
  ethernet_ip: {
    normal: {
      key: 'normal',
      label: 'Normal',
      description: 'Standard EtherNet/IP I/O (~20ms)',
      timing: { intervalMs: 20, jitterMs: 5 },
    },
    high_speed: {
      key: 'high_speed',
      label: 'High-Speed',
      description: 'High-speed I/O (~10ms)',
      timing: { intervalMs: 10, jitterMs: 2 },
    },
    maintenance: {
      key: 'maintenance',
      label: 'Maintenance',
      description: 'Slow polling during maintenance (~100ms)',
      timing: { intervalMs: 100, jitterMs: 20 },
    },
    degraded: {
      key: 'degraded',
      label: 'Degraded',
      description: 'Degraded conditions (~50ms, high jitter)',
      timing: { intervalMs: 50, jitterMs: 25 },
    },
  },
  profinet: {
    normal: {
      key: 'normal',
      label: 'Normal',
      description: 'Standard PROFINET RT (~4ms)',
      timing: { intervalMs: 4, jitterMs: 1 },
    },
    high_speed: {
      key: 'high_speed',
      label: 'High-Speed',
      description: 'Fast PROFINET IRT (~2ms)',
      timing: { intervalMs: 2, jitterMs: 1 },
    },
    maintenance: {
      key: 'maintenance',
      label: 'Maintenance',
      description: 'Reduced rate during maintenance (~16ms)',
      timing: { intervalMs: 16, jitterMs: 4 },
    },
    degraded: {
      key: 'degraded',
      label: 'Degraded',
      description: 'Degraded PROFINET (~8ms, high jitter)',
      timing: { intervalMs: 8, jitterMs: 4 },
    },
  },
  bacnet: {
    normal: {
      key: 'normal',
      label: 'Normal',
      description: 'Standard BACnet polling (~5s)',
      timing: { intervalMs: 5000, jitterMs: 500 },
    },
    high_speed: {
      key: 'high_speed',
      label: 'High-Speed',
      description: 'Fast BACnet polling (~2s)',
      timing: { intervalMs: 2000, jitterMs: 200 },
    },
    maintenance: {
      key: 'maintenance',
      label: 'Maintenance',
      description: 'Slow BACnet polling (~10s)',
      timing: { intervalMs: 10000, jitterMs: 1000 },
    },
    degraded: {
      key: 'degraded',
      label: 'Degraded',
      description: 'Degraded BACnet (~5s, high jitter)',
      timing: { intervalMs: 5000, jitterMs: 2000 },
    },
  },
  _default: {
    normal: {
      key: 'normal',
      label: 'Normal',
      description: 'Standard polling interval (~1s)',
      timing: { intervalMs: 1000, jitterMs: 100 },
    },
    high_speed: {
      key: 'high_speed',
      label: 'High-Speed',
      description: 'Fast polling (~500ms)',
      timing: { intervalMs: 500, jitterMs: 50 },
    },
    maintenance: {
      key: 'maintenance',
      label: 'Maintenance',
      description: 'Slow polling during maintenance (~3s)',
      timing: { intervalMs: 3000, jitterMs: 300 },
    },
    degraded: {
      key: 'degraded',
      label: 'Degraded',
      description: 'Degraded network conditions (~1s, high jitter)',
      timing: { intervalMs: 1000, jitterMs: 500 },
    },
  },
};

/** Get presets for a given protocol, falling back to _default. */
export function getPresetsForProtocol(protocol: string): Record<PresetKey, TrafficPreset> {
  return PRESETS[protocol] || PRESETS._default;
}

/** Detect which preset matches the current timing, or return null for custom. */
export function detectPreset(
  protocol: string,
  timing: { intervalMs: number; jitterMs: number },
): PresetKey | null {
  const presets = getPresetsForProtocol(protocol);
  for (const [key, preset] of Object.entries(presets)) {
    if (
      preset.timing.intervalMs === timing.intervalMs &&
      preset.timing.jitterMs === timing.jitterMs
    ) {
      return key as PresetKey;
    }
  }
  return null;
}
