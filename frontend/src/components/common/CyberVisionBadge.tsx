/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * CyberVisionBadge - compact tag showing a deployment's Cyber Vision
 * provisioning state (preset created / discovering / groups created / error).
 * Rendered in both the deployment area and the live-traffic dashboard.
 */

import React from 'react';
import { Tag, Tooltip } from 'antd';
import { ApiOutlined } from '@ant-design/icons';

export interface CyberVisionSummary {
  status: 'not_started' | 'preset_created' | 'polling' | 'groups_created' | 'error';
  preset_label?: string | null;
  subnet?: string | null;
  group_count?: number;
  device_count?: number;
}

const STATUS_CONFIG: Record<
  string,
  { color: string; label: string }
> = {
  preset_created: { color: 'blue', label: 'CV: Preset' },
  polling: { color: 'processing', label: 'CV: Discovering' },
  groups_created: { color: 'success', label: 'CV: Integrated' },
  error: { color: 'error', label: 'CV: Error' },
};

const CyberVisionBadge: React.FC<{
  cv?: CyberVisionSummary | null;
  style?: React.CSSProperties;
}> = ({ cv, style }) => {
  if (!cv || !cv.status || cv.status === 'not_started') return null;
  const cfg = STATUS_CONFIG[cv.status];
  if (!cfg) return null;

  const tooltipParts: string[] = [];
  if (cv.preset_label) tooltipParts.push(`Preset: ${cv.preset_label}`);
  if (cv.subnet) tooltipParts.push(`Subnet: ${cv.subnet}`);
  if (cv.status === 'groups_created') {
    tooltipParts.push(`${cv.group_count ?? 0} group(s), ${cv.device_count ?? 0} device(s)`);
  }

  return (
    <Tooltip title={tooltipParts.join(' · ') || 'Cyber Vision provisioning'}>
      <Tag color={cfg.color} icon={<ApiOutlined />} style={{ margin: 0, ...style }}>
        {cfg.label}
      </Tag>
    </Tooltip>
  );
};

export default CyberVisionBadge;
