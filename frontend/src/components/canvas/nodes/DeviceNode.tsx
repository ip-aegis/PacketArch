/**
 * Custom React Flow node for OT devices
 * Enhanced visual design with color-coded device type icons
 */

import React from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import {
  ControlOutlined,
  DesktopOutlined,
  CloudServerOutlined,
  ThunderboltOutlined,
  DashboardOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { Tag, Tooltip } from 'antd';
import type { DeviceType, ProtocolType } from '../../../types';

export interface DeviceNodeData extends Record<string, unknown> {
  id: string;
  name: string;
  type: DeviceType;
  role?: string;
  protocols: ProtocolType[];
  isConfigured: boolean;
  ipAddress?: string;
}

// Device type configuration with colors matching Device Library
const DEVICE_TYPE_CONFIG: Record<DeviceType, { icon: React.ReactNode; color: string; label: string }> = {
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

const DeviceNode: React.FC<NodeProps<DeviceNodeData>> = (props) => {
  const { data, selected } = props;
  if (!data) return null;

  const nodeData = data as unknown as DeviceNodeData;
  const deviceConfig = DEVICE_TYPE_CONFIG[nodeData.type] || DEVICE_TYPE_CONFIG.plc;
  const deviceColor = deviceConfig.color;

  return (
    <div
      style={{
        padding: '12px 16px',
        borderRadius: '12px',
        background: '#1e2a3a',
        border: `2px solid ${selected ? deviceColor : 'rgba(255,255,255,0.08)'}`,
        boxShadow: selected
          ? `0 4px 20px ${deviceColor}40, 0 0 0 1px ${deviceColor}60`
          : '0 2px 8px rgba(0,0,0,0.3)',
        minWidth: '140px',
        maxWidth: '180px',
        transition: 'all 0.2s ease',
        cursor: 'pointer',
        position: 'relative',
      }}
    >
      {/* Connection handles */}
      <Handle
        type="target"
        position={Position.Top}
        style={{
          background: deviceColor,
          width: 10,
          height: 10,
          border: '2px solid #1e2a3a',
          top: -5,
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        style={{
          background: deviceColor,
          width: 10,
          height: 10,
          border: '2px solid #1e2a3a',
          bottom: -5,
        }}
      />
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: deviceColor,
          width: 10,
          height: 10,
          border: '2px solid #1e2a3a',
          left: -5,
        }}
      />
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: deviceColor,
          width: 10,
          height: 10,
          border: '2px solid #1e2a3a',
          right: -5,
        }}
      />

      {/* Configuration status indicator */}
      <div
        style={{
          position: 'absolute',
          top: 8,
          right: 8,
          fontSize: '14px',
        }}
      >
        {nodeData.isConfigured ? (
          <Tooltip title="Fully configured">
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
          </Tooltip>
        ) : (
          <Tooltip title="Incomplete configuration">
            <ExclamationCircleOutlined style={{ color: '#faad14' }} />
          </Tooltip>
        )}
      </div>

      {/* Large centered icon with colored background */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          marginBottom: '10px',
        }}
      >
        <div
          style={{
            width: '56px',
            height: '56px',
            borderRadius: '14px',
            background: `linear-gradient(135deg, ${deviceColor}30, ${deviceColor}15)`,
            border: `1px solid ${deviceColor}50`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '28px',
            color: deviceColor,
            boxShadow: `0 2px 8px ${deviceColor}20`,
          }}
        >
          {deviceConfig.icon}
        </div>
      </div>

      {/* Device name - centered */}
      <div
        style={{
          textAlign: 'center',
          marginBottom: '4px',
        }}
      >
        <div
          style={{
            fontWeight: 600,
            fontSize: '13px',
            color: '#ffffff',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            lineHeight: '1.3',
          }}
        >
          {nodeData.name}
        </div>
        {nodeData.role && (
          <div
            style={{
              fontSize: '11px',
              color: 'rgba(255,255,255,0.5)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              marginTop: '2px',
            }}
          >
            {nodeData.role}
          </div>
        )}
      </div>

      {/* IP Address display */}
      {nodeData.ipAddress && (
        <div
          style={{
            textAlign: 'center',
            marginBottom: '6px',
          }}
        >
          <span
            style={{
              fontSize: '10px',
              color: 'rgba(255,255,255,0.4)',
              fontFamily: 'monospace',
              background: 'rgba(255,255,255,0.05)',
              padding: '2px 6px',
              borderRadius: '4px',
            }}
          >
            {nodeData.ipAddress}
          </span>
        </div>
      )}

      {/* Protocol badges - compact */}
      {nodeData.protocols.length > 0 && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            flexWrap: 'wrap',
            gap: '4px',
            marginTop: '6px',
          }}
        >
          {nodeData.protocols.slice(0, 4).map((protocol: ProtocolType) => (
            <Tooltip key={protocol} title={protocol.replace('_', ' ').toUpperCase()}>
              <Tag
                color={PROTOCOL_COLORS[protocol]}
                style={{
                  fontSize: '9px',
                  margin: 0,
                  lineHeight: '16px',
                  padding: '0 5px',
                  borderRadius: '3px',
                  fontWeight: 600,
                }}
              >
                {PROTOCOL_SHORT_NAMES[protocol] || protocol.slice(0, 3).toUpperCase()}
              </Tag>
            </Tooltip>
          ))}
          {nodeData.protocols.length > 4 && (
            <Tooltip title={nodeData.protocols.slice(4).map(p => p.replace('_', ' ')).join(', ')}>
              <Tag
                style={{
                  fontSize: '9px',
                  margin: 0,
                  lineHeight: '16px',
                  padding: '0 5px',
                  borderRadius: '3px',
                  background: 'rgba(255,255,255,0.1)',
                  border: 'none',
                  color: 'rgba(255,255,255,0.6)',
                }}
              >
                +{nodeData.protocols.length - 4}
              </Tag>
            </Tooltip>
          )}
        </div>
      )}
    </div>
  );
};

export default DeviceNode;
