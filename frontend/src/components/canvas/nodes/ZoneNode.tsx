/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Group node for network zones
 * Dark theme styling to match canvas
 */

import React from 'react';
import { LockOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';
import type { NodeProps } from '@xyflow/react';
import { Handle, Position } from '@xyflow/react';
import { useUIStore } from '../../../stores/uiStore';
import { useScenarioStore } from '../../../stores/scenarioStore';

export interface ZoneNodeData extends Record<string, unknown> {
  id: string;
  name: string;
  type: 'vertical' | 'network' | 'vlan' | 'logical';
  level?: number;
  network?: {
    subnet: string;
    vlanId?: number;
    gateway?: string;
  };
}

// Zone colors with dark theme
const ZONE_COLORS: Record<string, string> = {
  vertical: 'rgba(4, 159, 217, 0.08)',
  network: 'rgba(108, 192, 74, 0.08)',
  vlan: 'rgba(156, 39, 176, 0.08)',
  logical: 'rgba(251, 171, 24, 0.08)',
};

const ZONE_BORDER_COLORS: Record<string, string> = {
  vertical: '#049FD9',
  network: '#6CC04A',
  vlan: '#9C27B0',
  logical: '#FBAB18',
};

const HANDLE_STYLE: React.CSSProperties = {
  width: 8,
  height: 8,
  background: '#049FD9',
  border: '2px solid #1e2a3a',
  borderRadius: '50%',
};

const HANDLE_STYLE_HIDDEN: React.CSSProperties = {
  ...HANDLE_STYLE,
  visibility: 'hidden',
  width: 1,
  height: 1,
};

const ZoneNode: React.FC<NodeProps<ZoneNodeData>> = React.memo((props) => {
  const { data, selected } = props;
  const activeTool = useUIStore((s) => s.tool.activeTool);
  const isConduitMode = activeTool === 'conduit';
  const isolationMode = useScenarioStore((s) => s.cellIsolation?.mode ?? 'off');
  const cellLevels = useScenarioStore((s) => s.cellIsolation?.applies_to_levels ?? [0, 1, 2]);

  if (!data) return null;

  const nodeData = data as ZoneNodeData;
  const backgroundColor = ZONE_COLORS[nodeData.type] || ZONE_COLORS.logical;
  const borderColor = ZONE_BORDER_COLORS[nodeData.type] || ZONE_BORDER_COLORS.logical;
  const handleStyle = isConduitMode ? HANDLE_STYLE : HANDLE_STYLE_HIDDEN;
  const zoneLevel = typeof nodeData.level === 'number' ? Math.floor(nodeData.level) : null;
  const isCellZone =
    isolationMode !== 'off' && zoneLevel !== null && cellLevels.includes(zoneLevel);
  const lockTooltip =
    isolationMode === 'strict_northbound'
      ? `Cell (L${zoneLevel}) — east/west traffic blocked. Cell may only talk northbound to L3+ zones.`
      : `Cell (L${zoneLevel}) — cross-cell flows require an explicit conduit.`;

  // Three slots per side so multiple conduits leaving / entering the same
  // edge can fan out instead of stacking. Slots are at 25% / 50% / 75%.
  const slotOffsets = [25, 50, 75] as const;
  const horizSlot = (pct: number): React.CSSProperties => ({ ...handleStyle, left: `${pct}%` });
  const vertSlot = (pct: number): React.CSSProperties => ({ ...handleStyle, top: `${pct}%` });
  const renderSlots = (
    side: 'top' | 'bottom' | 'left' | 'right',
    kind: 'source' | 'target',
  ) => {
    const isHoriz = side === 'top' || side === 'bottom';
    return slotOffsets.map((pct, i) => {
      const idBase = kind === 'source' ? 'conduit' : 'conduit-target';
      const id = `${idBase}-${side}-${i}`;
      const pos =
        side === 'top' ? Position.Top
        : side === 'bottom' ? Position.Bottom
        : side === 'left' ? Position.Left
        : Position.Right;
      const style = isHoriz ? horizSlot(pct) : vertSlot(pct);
      return <Handle key={id} type={kind} position={pos} id={id} style={style} />;
    });
  };
  // Single legacy "center" handle for backwards compatibility — older saved
  // conduits reference these IDs and we don't want to break them.
  const legacyHandle = (side: 'top' | 'bottom' | 'left' | 'right', kind: 'source' | 'target') => {
    const idBase = kind === 'source' ? 'conduit' : 'conduit-target';
    const id = `${idBase}-${side}`;
    const pos =
      side === 'top' ? Position.Top
      : side === 'bottom' ? Position.Bottom
      : side === 'left' ? Position.Left
      : Position.Right;
    return <Handle key={id} type={kind} position={pos} id={id} style={handleStyle} />;
  };

  return (
    <>
      {/* Conduit connection handles — visible only in conduit tool mode.
          Three slots per side (25/50/75%) plus a legacy center handle so
          existing edges keep working. */}
      {renderSlots('top', 'source')}
      {renderSlots('bottom', 'source')}
      {renderSlots('left', 'source')}
      {renderSlots('right', 'source')}
      {renderSlots('top', 'target')}
      {renderSlots('bottom', 'target')}
      {renderSlots('left', 'target')}
      {renderSlots('right', 'target')}
      {legacyHandle('top', 'source')}
      {legacyHandle('bottom', 'source')}
      {legacyHandle('left', 'source')}
      {legacyHandle('right', 'source')}
      {legacyHandle('top', 'target')}
      {legacyHandle('bottom', 'target')}
      {legacyHandle('left', 'target')}
      {legacyHandle('right', 'target')}
      <div
        role="group"
        aria-label={`${nodeData.type} zone: ${nodeData.name}${nodeData.network?.subnet ? `, subnet ${nodeData.network.subnet}` : ''}`}
        aria-selected={selected}
        tabIndex={0}
        style={{
          width: '100%',
          height: '100%',
          background: backgroundColor,
          border: `2px dashed ${selected ? borderColor : `${borderColor}60`}`,
          borderRadius: '12px',
          padding: '12px',
          pointerEvents: 'all',
          transition: 'all 0.2s ease',
          boxShadow: selected ? `0 0 20px ${borderColor}30` : undefined,
        }}
      >
        {/* Zone header */}
        <div
          style={{
            background: '#1e2a3a',
            border: `1px solid ${borderColor}50`,
            borderRadius: '6px',
            padding: '6px 12px',
            display: 'inline-block',
            fontWeight: 600,
            fontSize: '13px',
            color: borderColor,
            marginBottom: '8px',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
          }}
        >
          {nodeData.name}
          {isCellZone && (
            <Tooltip title={lockTooltip}>
              <LockOutlined
                style={{
                  marginLeft: 6,
                  color:
                    isolationMode === 'strict_northbound' ? '#ff4d4f' : '#faad14',
                }}
              />
            </Tooltip>
          )}
        </div>

        {/* Network info */}
        {nodeData.network && (
          <div
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: `1px solid ${borderColor}30`,
              borderRadius: '4px',
              padding: '4px 10px',
              display: 'inline-block',
              fontSize: '11px',
              color: 'rgba(255,255,255,0.6)',
              marginLeft: '8px',
              fontFamily: 'monospace',
            }}
          >
            {nodeData.network.subnet}
            {nodeData.network.vlanId && ` (VLAN ${nodeData.network.vlanId})`}
          </div>
        )}
      </div>
    </>
  );
});

ZoneNode.displayName = 'ZoneNode';

export default ZoneNode;
