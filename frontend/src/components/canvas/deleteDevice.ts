/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import { useScenarioStore } from '../../stores/scenarioStore';
import { useHistoryStore } from '../../stores/historyStore';

/**
 * Delete a device with full-cascade undo.
 *
 * `removeDevice` cascades: it drops every flow connected to the device and
 * strips it from `zone.deviceIds`. The undo closure must restore that whole
 * cascade — restoring only the device silently loses its flows.
 *
 * All device-delete paths (Delete key, context menu, toolbar button,
 * command palette) must go through this helper so they share one history
 * behavior.
 */
export function deleteDeviceWithHistory(deviceId: string): boolean {
  const state = useScenarioStore.getState();
  const device = state.devices[deviceId];
  if (!device) return false;

  const connectedFlows = Object.values(state.flows).filter(
    (f) => f.sourceDeviceId === deviceId || f.targetDeviceId === deviceId,
  );
  const memberZoneIds = Object.values(state.zones)
    .filter((z) => z.deviceIds?.includes(deviceId))
    .map((z) => z.id);

  state.removeDevice(deviceId);
  useHistoryStore.getState().push({
    type: 'REMOVE_DEVICE',
    undo: () => {
      const s = useScenarioStore.getState();
      s.addDevice(device);
      connectedFlows.forEach((flow) => s.addFlow(flow));
      memberZoneIds.forEach((zoneId) => {
        const zone = s.zones[zoneId];
        if (zone && !zone.deviceIds.includes(deviceId)) {
          s.updateZone(zoneId, { deviceIds: [...zone.deviceIds, deviceId] });
        }
      });
    },
    redo: () => useScenarioStore.getState().removeDevice(deviceId),
    timestamp: Date.now(),
  });
  return true;
}
