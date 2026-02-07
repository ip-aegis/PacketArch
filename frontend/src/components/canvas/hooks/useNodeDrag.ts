/**
 * Hook to handle drag-and-drop from palette to canvas
 * Converts screen coordinates to canvas coordinates
 * Auto-assigns IP addresses from scenario's IP range
 */

import { useCallback } from 'react';
import { useReactFlow } from '@xyflow/react';
import { useScenarioStore } from '../../../stores/scenarioStore';
import { useHistoryStore } from '../../../stores/historyStore';
import { ipManagementApi } from '../../../api/ipManagement';
import type { DeviceProfile, ScenarioDevice, DeviceType } from '../../../types';

export const useNodeDrag = () => {
  const { screenToFlowPosition } = useReactFlow();
  const addDevice = useScenarioStore((state) => state.addDevice);
  const updateDevice = useScenarioStore((state) => state.updateDevice);
  const removeDevice = useScenarioStore((state) => state.removeDevice);
  const scenarioId = useScenarioStore((state) => state.id);
  const ipRange = useScenarioStore((state) => state.ipRange);
  const pushHistory = useHistoryStore((state) => state.push);

  const handleDrop = useCallback(
    async (event: React.DragEvent<HTMLDivElement>, deviceProfile: DeviceProfile) => {
      event.preventDefault();

      // Get the position on the canvas
      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      // Generate unique ID
      const deviceId = `device-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

      // Create device from profile with default empty network config
      const newDevice: ScenarioDevice = {
        id: deviceId,
        profileId: deviceProfile.id,
        name: deviceProfile.name,
        type: deviceProfile.device_type as DeviceType,
        role: deviceProfile.role || undefined,
        position,
        network: {
          macAddress: '',
          ipAddress: '',
          subnetMask: '255.255.255.0',
          gateway: undefined,
          vlanId: undefined,
          hostname: undefined,
        },
        protocols: deviceProfile.supported_protocols || [],
        timing: deviceProfile.timing_model
          ? {
              intervalMs: deviceProfile.timing_model.polling_interval_ms,
              jitterMs: deviceProfile.timing_model.jitter_max_ms,
              burstSize: deviceProfile.timing_model.burst_size,
              burstIntervalMs: deviceProfile.timing_model.burst_interval_ms,
            }
          : undefined,
      };

      // Add device to store first (so it appears on canvas immediately)
      addDevice(newDevice);

      // Try to auto-assign IP if scenario is saved and has auto-assign enabled
      if (scenarioId && ipRange?.autoAssignEnabled) {
        try {
          const nextIP = await ipManagementApi.getNextIP(scenarioId);
          // Update device with the assigned IP
          updateDevice(deviceId, {
            network: {
              ...newDevice.network,
              ipAddress: nextIP.ip_address,
              subnetMask: nextIP.subnet_mask,
              gateway: nextIP.gateway,
            },
          });
        } catch (error) {
          // Silently fail - device was already added without IP
          console.warn('Failed to auto-assign IP:', error);
        }
      }

      // Add to history for undo
      pushHistory({
        type: 'ADD_DEVICE',
        undo: () => removeDevice(deviceId),
        redo: () => addDevice(newDevice),
        timestamp: Date.now(),
      });
    },
    [screenToFlowPosition, addDevice, updateDevice, removeDevice, scenarioId, ipRange, pushHistory]
  );

  return { handleDrop };
};

export default useNodeDrag;
