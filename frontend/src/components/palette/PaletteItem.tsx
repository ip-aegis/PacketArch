/**
 * Draggable device template item for palette
 * Enhanced visual design matching DeviceNode style
 */

import React from 'react';
import { Card, Tag, Typography, Tooltip } from 'antd';
import type { DeviceProfile } from '../../types';
import {
  PROTOCOL_COLORS,
  PROTOCOL_SHORT_NAMES,
} from '../../constants/protocols';
import { getDeviceTypeMeta, getDeviceTypeIcon } from '../../constants/deviceTypeRegistry';

const { Text } = Typography;

interface PaletteItemProps {
  device: DeviceProfile;
}

const PaletteItem: React.FC<PaletteItemProps> = ({ device }) => {
  const handleDragStart = (e: React.DragEvent<HTMLDivElement>) => {
    e.dataTransfer.effectAllowed = 'copy';
    e.dataTransfer.setData('application/json', JSON.stringify(device));
  };

  const meta = getDeviceTypeMeta(device.device_type);
  const deviceColor = meta.color;
  const deviceIcon = getDeviceTypeIcon(device.device_type);

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      style={{
        cursor: 'grab',
        marginBottom: '8px',
      }}
    >
      <Card
        size="small"
        hoverable
        style={{
          borderRadius: '10px',
          transition: 'all 0.2s ease',
          background: '#1e2a3a',
          borderColor: 'rgba(255,255,255,0.08)',
        }}
        styles={{ body: { padding: '10px 12px' } }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Color-coded icon badge */}
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: `linear-gradient(135deg, ${deviceColor}30, ${deviceColor}15)`,
              border: `1px solid ${deviceColor}50`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '18px',
              color: deviceColor,
              flexShrink: 0,
            }}
          >
            {deviceIcon}
          </div>

          {/* Device info */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <Text
              strong
              style={{
                fontSize: '12px',
                display: 'block',
                marginBottom: '2px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                color: '#ffffff',
              }}
            >
              {device.name}
            </Text>
            {device.role && (
              <Text
                style={{
                  fontSize: '10px',
                  display: 'block',
                  marginBottom: '4px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  color: 'rgba(255,255,255,0.5)',
                }}
              >
                {device.role}
              </Text>
            )}
            {device.supported_protocols && device.supported_protocols.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '3px' }}>
                {device.supported_protocols.slice(0, 3).map((protocol) => (
                  <Tooltip key={protocol} title={protocol.replace('_', ' ').toUpperCase()}>
                    <Tag
                      color={PROTOCOL_COLORS[protocol]}
                      style={{
                        fontSize: '8px',
                        margin: 0,
                        lineHeight: '14px',
                        padding: '0 4px',
                        borderRadius: '3px',
                        fontWeight: 600,
                      }}
                    >
                      {PROTOCOL_SHORT_NAMES[protocol] || protocol.slice(0, 3).toUpperCase()}
                    </Tag>
                  </Tooltip>
                ))}
                {device.supported_protocols.length > 3 && (
                  <Tooltip title={device.supported_protocols.slice(3).map(p => p.replace('_', ' ')).join(', ')}>
                    <Tag
                      style={{
                        fontSize: '8px',
                        margin: 0,
                        lineHeight: '14px',
                        padding: '0 4px',
                        borderRadius: '3px',
                        background: 'rgba(255,255,255,0.1)',
                        border: 'none',
                        color: 'rgba(255,255,255,0.6)',
                      }}
                    >
                      +{device.supported_protocols.length - 3}
                    </Tag>
                  </Tooltip>
                )}
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
};

export default PaletteItem;
