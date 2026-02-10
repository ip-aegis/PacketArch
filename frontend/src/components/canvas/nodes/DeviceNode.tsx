/**
 * Custom React Flow node for OT devices
 * Enhanced visual design with color-coded device type icons
 */

import React, { useState } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { useCompactMode } from '../hooks/useCompactMode';
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  BugOutlined,
} from '@ant-design/icons';
import { Tag, Tooltip } from 'antd';
import type { ProtocolType } from '../../../types';
import {
  PROTOCOL_COLORS,
  PROTOCOL_SHORT_NAMES,
} from '../../../constants/protocols';
import { getDeviceTypeMeta, getDeviceTypeIcon } from '../../../constants/deviceTypeRegistry';

export interface DeviceNodeData extends Record<string, unknown> {
  id: string;
  name: string;
  type: string;
  role?: string;
  protocols: ProtocolType[];
  isConfigured: boolean;
  ipAddress?: string;
  cveIds?: string[];
  vendor?: string;
}

const DeviceNode: React.FC<NodeProps<DeviceNodeData>> = React.memo((props) => {
  const { data, selected } = props;
  const [hovered, setHovered] = useState(false);
  const rawCompact = useCompactMode();
  // Selected nodes always show full detail
  const isCompact = rawCompact && !selected;
  if (!data) return null;

  const nodeData = data as DeviceNodeData;
  const deviceMeta = getDeviceTypeMeta(nodeData.type);
  const deviceColor = deviceMeta.color;
  const deviceIcon = getDeviceTypeIcon(nodeData.type);
  const showDetails = selected || hovered;

  const handleStyle = (pos: 'top' | 'bottom' | 'left' | 'right') => {
    const size = isCompact ? 8 : 10;
    const offset = isCompact ? -4 : -5;
    return {
      background: deviceColor,
      width: size,
      height: size,
      border: '2px solid #1e2a3a',
      [pos]: offset,
    };
  };

  if (isCompact) {
    return (
      <div
        role="treeitem"
        aria-label={`${deviceMeta.label}: ${nodeData.name}`}
        aria-selected={selected}
        tabIndex={0}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onContextMenu={(e) => {
          e.preventDefault();
          e.stopPropagation();
          window.dispatchEvent(
            new CustomEvent('device-context-menu', {
              detail: { deviceId: nodeData.id, x: e.clientX, y: e.clientY },
            }),
          );
        }}
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '4px',
          cursor: 'pointer',
          position: 'relative',
        }}
      >
        <Handle type="target" position={Position.Top} style={handleStyle('top')} />
        <Handle type="source" position={Position.Bottom} style={handleStyle('bottom')} />
        <Handle type="target" position={Position.Left} style={handleStyle('left')} />
        <Handle type="source" position={Position.Right} style={handleStyle('right')} />

        {/* Colored circle with icon */}
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: `linear-gradient(135deg, ${deviceColor}40, ${deviceColor}20)`,
            border: `2px solid ${hovered ? deviceColor : `${deviceColor}60`}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 16,
            color: deviceColor,
            boxShadow: hovered
              ? `0 0 12px ${deviceColor}50`
              : '0 1px 4px rgba(0,0,0,0.3)',
            transition: 'all 0.2s ease',
          }}
        >
          {deviceIcon}
        </div>

        {/* Name label */}
        <div
          style={{
            fontSize: 10,
            color: '#ffffff',
            fontWeight: 600,
            maxWidth: 70,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            textAlign: 'center',
            textShadow: '0 1px 3px rgba(0,0,0,0.8)',
          }}
        >
          {nodeData.name}
        </div>
      </div>
    );
  }

  return (
    <div
      role="treeitem"
      aria-label={`${deviceMeta.label} device: ${nodeData.name}${nodeData.vendor ? `, vendor ${nodeData.vendor}` : ''}${nodeData.ipAddress ? `, IP ${nodeData.ipAddress}` : ''}`}
      aria-selected={selected}
      tabIndex={0}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onContextMenu={(e) => {
        e.preventDefault();
        e.stopPropagation();
        window.dispatchEvent(
          new CustomEvent('device-context-menu', {
            detail: { deviceId: nodeData.id, x: e.clientX, y: e.clientY },
          }),
        );
      }}
      style={{
        padding: '10px 12px',
        borderRadius: '12px',
        background: '#1e2a3a',
        border: `2px solid ${selected ? deviceColor : 'rgba(255,255,255,0.08)'}`,
        boxShadow: selected
          ? `0 4px 20px ${deviceColor}40, 0 0 0 1px ${deviceColor}60`
          : '0 2px 8px rgba(0,0,0,0.3)',
        minWidth: '130px',
        maxWidth: '160px',
        transition: 'all 0.2s ease',
        cursor: 'pointer',
        position: 'relative',
      }}
    >
      {/* Connection handles */}
      <Handle type="target" position={Position.Top} style={handleStyle('top')} />
      <Handle type="source" position={Position.Bottom} style={handleStyle('bottom')} />
      <Handle type="target" position={Position.Left} style={handleStyle('left')} />
      <Handle type="source" position={Position.Right} style={handleStyle('right')} />

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

      {/* CVE indicator */}
      {nodeData.cveIds && nodeData.cveIds.length > 0 && (
        <div
          style={{
            position: 'absolute',
            top: 8,
            left: 8,
          }}
        >
          <Tooltip title={`Vulnerable: ${nodeData.cveIds.join(', ')}`}>
            <Tag
              color="error"
              icon={<BugOutlined />}
              style={{
                fontSize: '9px',
                margin: 0,
                lineHeight: '16px',
                padding: '0 4px',
                borderRadius: '3px',
              }}
            >
              {nodeData.cveIds.length}
            </Tag>
          </Tooltip>
        </div>
      )}

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
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            background: `linear-gradient(135deg, ${deviceColor}30, ${deviceColor}15)`,
            border: `1px solid ${deviceColor}50`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px',
            color: deviceColor,
            boxShadow: `0 2px 8px ${deviceColor}20`,
          }}
        >
          {deviceIcon}
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
        {nodeData.vendor && showDetails && (
          <div
            style={{
              fontSize: '10px',
              color: 'rgba(255,255,255,0.6)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              marginTop: '2px',
            }}
          >
            {nodeData.vendor}
          </div>
        )}
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
});

DeviceNode.displayName = 'DeviceNode';

export default DeviceNode;
