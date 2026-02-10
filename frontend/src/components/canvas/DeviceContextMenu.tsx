/**
 * Right-click context menu for device nodes on the canvas.
 * Supports duplicate, copy config to similar devices, and delete.
 */

import React, { useEffect, useCallback } from 'react';
import { Menu, Modal, Typography } from 'antd';
import { CopyOutlined, SyncOutlined, DeleteOutlined } from '@ant-design/icons';
import { useScenarioStore } from '../../stores/scenarioStore';
import { useHistoryStore } from '../../stores/historyStore';
import type { ScenarioDevice } from '../../types';
import { getDeviceTypeLabel } from '../../constants/deviceTypeRegistry';

const { Text } = Typography;

interface DeviceContextMenuProps {
  deviceId: string;
  position: { x: number; y: number };
  onClose: () => void;
}

/** Fields copied when using "Copy Config to Similar Devices" */
const CONFIG_FIELDS: (keyof ScenarioDevice)[] = [
  'vendor',
  'fingerprintModel',
  'firmwareVersion',
  'templateId',
  'timing',
  'errorConfig',
  'protocols',
  'cveIds',
  'vulnerableCve',
  'vulnerableFirmware',
  'cveIdentityOverrides',
  'vulnerabilityOverride',
];

const DeviceContextMenu: React.FC<DeviceContextMenuProps> = ({
  deviceId,
  position,
  onClose,
}) => {
  const devices = useScenarioStore((s) => s.devices);
  const addDevice = useScenarioStore((s) => s.addDevice);
  const updateDevice = useScenarioStore((s) => s.updateDevice);
  const removeDevice = useScenarioStore((s) => s.removeDevice);
  const pushHistory = useHistoryStore((s) => s.push);

  const sourceDevice = devices[deviceId];

  // Close on click outside or Escape
  const handleClickOutside = useCallback(
    (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.device-context-menu')) {
        onClose();
      }
    },
    [onClose],
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose],
  );

  useEffect(() => {
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleClickOutside, handleKeyDown]);

  if (!sourceDevice) {
    onClose();
    return null;
  }

  // Find devices of the same type (excluding the source)
  const similarDevices = Object.values(devices).filter(
    (d) => d.id !== deviceId && d.type === sourceDevice.type,
  );
  const typeLabel = getDeviceTypeLabel(sourceDevice.type);

  const handleDuplicate = () => {
    const newId = `device-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const newDevice: ScenarioDevice = {
      ...sourceDevice,
      id: newId,
      name: `${sourceDevice.name} (copy)`,
      position: {
        x: sourceDevice.position.x + 40,
        y: sourceDevice.position.y + 40,
      },
      network: {
        ...sourceDevice.network,
        ipAddress: '',
        macAddress: '',
      },
    };
    addDevice(newDevice);
    pushHistory({
      type: 'ADD_DEVICE',
      undo: () => removeDevice(newId),
      redo: () => addDevice(newDevice),
      timestamp: Date.now(),
    });
    onClose();
  };

  const handleCopyConfig = () => {
    const targetNames = similarDevices.map((d) => d.name).join(', ');

    Modal.confirm({
      title: 'Copy Config to Similar Devices',
      content: (
        <div>
          <Text style={{ display: 'block', marginBottom: 8 }}>
            Copy configuration from <strong>{sourceDevice.name}</strong> to{' '}
            {similarDevices.length} similar {typeLabel}
            {similarDevices.length !== 1 ? 's' : ''}:
          </Text>
          <Text style={{ color: '#6b6b8a', fontSize: 12 }}>{targetNames}</Text>
          <div style={{ marginTop: 12 }}>
            <Text style={{ fontSize: 12, color: '#a8a8c0' }}>
              Copies: vendor, model, firmware, timing, protocols, CVE config.
              <br />
              Preserves: name, IP, MAC, position, role.
            </Text>
          </div>
        </div>
      ),
      okText: 'Copy Config',
      onOk: () => {
        // Save originals for undo
        const originals = similarDevices.map((d) => ({ ...d }));

        // Apply config fields from source to each similar device
        similarDevices.forEach((target) => {
          const updates: Partial<ScenarioDevice> = {};
          for (const field of CONFIG_FIELDS) {
            const value = sourceDevice[field];
            if (value !== undefined) {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              (updates as any)[field] = JSON.parse(JSON.stringify(value));
            }
          }
          updateDevice(target.id, updates);
        });

        pushHistory({
          type: 'UPDATE_DEVICE',
          undo: () => {
            originals.forEach((orig) => {
              const updates: Partial<ScenarioDevice> = {};
              for (const field of CONFIG_FIELDS) {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                (updates as any)[field] = (orig as any)[field];
              }
              updateDevice(orig.id, updates);
            });
          },
          redo: () => {
            similarDevices.forEach((target) => {
              const updates: Partial<ScenarioDevice> = {};
              for (const field of CONFIG_FIELDS) {
                const value = sourceDevice[field];
                if (value !== undefined) {
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  (updates as any)[field] = JSON.parse(JSON.stringify(value));
                }
              }
              updateDevice(target.id, updates);
            });
          },
          timestamp: Date.now(),
        });
      },
    });

    onClose();
  };

  const handleDelete = () => {
    const device = { ...sourceDevice };
    removeDevice(deviceId);
    pushHistory({
      type: 'REMOVE_DEVICE',
      undo: () => addDevice(device),
      redo: () => removeDevice(deviceId),
      timestamp: Date.now(),
    });
    onClose();
  };

  const menuItems = [
    {
      key: 'duplicate',
      icon: <CopyOutlined />,
      label: 'Duplicate Device',
      onClick: handleDuplicate,
    },
    {
      key: 'copy-config',
      icon: <SyncOutlined />,
      label: similarDevices.length > 0
        ? `Copy Config to ${similarDevices.length} Similar ${typeLabel}${similarDevices.length !== 1 ? 's' : ''}`
        : `No Similar ${typeLabel}s`,
      disabled: similarDevices.length === 0,
      onClick: handleCopyConfig,
    },
    { type: 'divider' as const },
    {
      key: 'delete',
      icon: <DeleteOutlined />,
      label: 'Delete Device',
      danger: true,
      onClick: handleDelete,
    },
  ];

  return (
    <div
      className="device-context-menu"
      style={{
        position: 'fixed',
        left: position.x,
        top: position.y,
        zIndex: 1000,
      }}
    >
      <Menu
        items={menuItems}
        style={{
          background: '#1a1a2e',
          border: '1px solid #2d2d52',
          borderRadius: 8,
          boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
          minWidth: 220,
        }}
        selectable={false}
      />
    </div>
  );
};

export default DeviceContextMenu;
