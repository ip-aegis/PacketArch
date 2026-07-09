/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Device placement — builds a ScenarioDevice from a palette template and
 * dispatches it through the command bus. IP auto-assignment lands as a
 * follow-up command with the same coalesce key, so "add device" is ONE
 * undo step even though the IP arrives async.
 */

import { ipManagementApi } from '../../api/ipManagement';
import type { PaletteDeviceResponse } from '../../api/fingerprints';
import type { ScenarioDevice, DeviceType, ProtocolType } from '../../types';
import { useDocumentStore } from './documentStore';

function newDeviceId(): string {
  return `device-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

/** "PLC_01"-style suffix when the template name is already on the canvas. */
function uniqueName(base: string, existing: Set<string>): string {
  if (!existing.has(base)) return base;
  for (let i = 2; i < 1000; i++) {
    const candidate = `${base}_${i}`;
    if (!existing.has(candidate)) return candidate;
  }
  return `${base}_${Date.now()}`;
}

export function deviceFromTemplate(
  template: PaletteDeviceResponse,
  position: { x: number; y: number },
  existingNames: Set<string>,
): ScenarioDevice {
  const tm = template.timing_model as Record<string, number> | null;
  return {
    id: newDeviceId(),
    profileId: template.id,
    templateId: template.template_id || undefined,
    name: uniqueName(template.name, existingNames),
    type: template.device_type as DeviceType,
    role: template.role || undefined,
    vendor: template.vendor_fingerprint?.fingerprint_vendor || undefined,
    fingerprintModel: template.vendor_fingerprint?.fingerprint_model || undefined,
    position,
    network: {
      macAddress: '',
      ipAddress: '',
      subnetMask: '255.255.255.0',
      gateway: undefined,
      vlanId: undefined,
      hostname: undefined,
    },
    protocols: (template.supported_protocols ?? []) as ProtocolType[],
    timing: tm
      ? {
          intervalMs: tm.polling_interval_ms,
          jitterMs: tm.jitter_max_ms,
          burstSize: tm.burst_size,
          burstIntervalMs: tm.burst_interval_ms,
        }
      : undefined,
  };
}

export async function placeDevice(
  template: PaletteDeviceResponse,
  position: { x: number; y: number },
): Promise<void> {
  const state = useDocumentStore.getState();
  if (!state.doc) return;

  const existingNames = new Set(Object.values(state.doc.devices).map((d) => d.name));
  const device = deviceFromTemplate(template, position, existingNames);
  const coalesceKey = `add-device-${device.id}`;

  state.dispatch({
    label: `Add ${device.name}`,
    coalesceKey,
    mutations: [{ kind: 'device', id: device.id, before: undefined, after: device }],
  });

  const doc = useDocumentStore.getState().doc;
  if (!doc || !doc.addressing?.autoAssignEnabled) return;
  try {
    const nextIP = await ipManagementApi.getNextIP(doc.meta.id);
    const current = useDocumentStore.getState();
    const placed = current.doc?.devices[device.id];
    if (!placed) return; // deleted (or scenario switched) before the IP landed
    current.dispatch({
      label: `Add ${device.name}`,
      coalesceKey,
      mutations: [
        {
          kind: 'device',
          id: device.id,
          before: placed,
          after: {
            ...placed,
            network: {
              ...placed.network,
              ipAddress: nextIP.ip_address,
              subnetMask: nextIP.subnet_mask,
              gateway: nextIP.gateway,
            },
          },
        },
      ],
    });
  } catch (error) {
    console.warn('Failed to auto-assign IP:', error);
  }
}
