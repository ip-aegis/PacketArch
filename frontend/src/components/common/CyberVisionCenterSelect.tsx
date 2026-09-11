/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Picker for one of the configured Cyber Vision Centers.
 *
 * `value` null/undefined means "the default center" — the placeholder says
 * which one that is, so leaving the picker alone is always a meaningful
 * choice, and single-center installs have nothing to decide.
 */

import React from 'react';
import { Select, Space, Tag, Tooltip, Typography } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import { useCyberVisionCenters } from '../../hooks/useCyberVisionCenters';

const { Text } = Typography;

export interface CyberVisionCenterSelectProps {
  value?: string | null;
  onChange?: (centerId: string | null) => void;
  disabled?: boolean;
  /** Why the picker is locked (e.g. a local-lab agent is tied to its lab's center). */
  lockedReason?: string;
  style?: React.CSSProperties;
  size?: 'small' | 'middle' | 'large';
}

const CyberVisionCenterSelect: React.FC<CyberVisionCenterSelectProps> = ({
  value,
  onChange,
  disabled,
  lockedReason,
  style,
  size,
}) => {
  const { centers, centersLoaded } = useCyberVisionCenters();

  const defaultCenter = centers.find((c) => c.is_default);
  const locked = Boolean(lockedReason);

  const select = (
    <Select
      size={size}
      style={{ minWidth: 220, ...style }}
      value={value ?? undefined}
      allowClear={!locked}
      disabled={disabled || locked}
      loading={!centersLoaded}
      placeholder={defaultCenter ? `${defaultCenter.name} (default)` : 'No Cyber Vision Center configured'}
      onChange={(v) => onChange?.((v as string | undefined) ?? null)}
      suffixIcon={locked ? <LockOutlined /> : undefined}
      optionLabelProp="label"
      options={centers.map((c) => ({
        value: c.id,
        label: c.is_default ? `${c.name} (default)` : c.name,
        title: c.url,
      }))}
      optionRender={(option) => {
        const c = centers.find((x) => x.id === option.value);
        if (!c) return option.label;
        return (
          <Space size={6}>
            <span>{c.name}</span>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {c.url}
            </Text>
            {c.is_default && <Tag color="blue">Default</Tag>}
          </Space>
        );
      }}
    />
  );

  return locked ? <Tooltip title={lockedReason}>{select}</Tooltip> : select;
};

export default CyberVisionCenterSelect;
