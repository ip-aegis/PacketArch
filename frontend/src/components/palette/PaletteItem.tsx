/**
 * Draggable device template item for palette
 * Enhanced visual design matching DeviceNode style
 */

import React from 'react';
import { Card, Tag, Typography, Tooltip } from 'antd';
import {
  ControlOutlined,
  DesktopOutlined,
  CloudServerOutlined,
  ThunderboltOutlined,
  DashboardOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import type { DeviceProfile, ProtocolType } from '../../types';

const { Text } = Typography;

// Device type configuration with colors matching DeviceNode
const DEVICE_TYPE_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  plc: { icon: <ControlOutlined />, color: '#049FD9', label: 'PLC' },
  hmi: { icon: <DesktopOutlined />, color: '#6CC04A', label: 'HMI' },
  rtu: { icon: <CloudServerOutlined />, color: '#FBAB18', label: 'RTU' },
  drive: { icon: <ThunderboltOutlined />, color: '#FF7043', label: 'Drive' },
  sensor: { icon: <DashboardOutlined />, color: '#00BCEB', label: 'Sensor' },
  relay: { icon: <SafetyCertificateOutlined />, color: '#E53935', label: 'Relay' },
  ews: { icon: <SettingOutlined />, color: '#9C27B0', label: 'EWS' },
  historian: { icon: <DatabaseOutlined />, color: '#607D8B', label: 'Historian' },
};

const PROTOCOL_COLORS: Record<ProtocolType, string> = {
  modbus_tcp: '#049FD9',
  ethernet_ip: '#6CC04A',
  profinet: '#FBAB18',
  opc_ua: '#9C27B0',
  dnp3: '#FF5722',
  iec104: '#E91E63',
  bacnet: '#00BCD4',
};

// Protocol short names for compact display
const PROTOCOL_SHORT_NAMES: Record<ProtocolType, string> = {
  modbus_tcp: 'MB',
  ethernet_ip: 'EIP',
  profinet: 'PN',
  opc_ua: 'OPC',
  dnp3: 'DNP3',
  iec104: '104',
  bacnet: 'BAC',
};

interface PaletteItemProps {
  device: DeviceProfile;
}

const PaletteItem: React.FC<PaletteItemProps> = ({ device }) => {
  const handleDragStart = (e: React.DragEvent<HTMLDivElement>) => {
    e.dataTransfer.effectAllowed = 'copy';
    e.dataTransfer.setData('application/json', JSON.stringify(device));
  };

  const config = DEVICE_TYPE_CONFIG[device.device_type] || DEVICE_TYPE_CONFIG.plc;
  const deviceColor = config.color;

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
            {config.icon}
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
