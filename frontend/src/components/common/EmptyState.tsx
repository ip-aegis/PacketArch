/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React from 'react';
import { Empty, Typography } from 'antd';
import { TEXT_PARAGRAPH, TEXT_MUTED } from '../../constants/theme';

const { Text } = Typography;

export interface EmptyStateProps {
  /** Icon rendered at 48px. Pass a bare icon element (e.g. <ExperimentOutlined />) */
  icon?: React.ReactNode;
  /** Primary message (13px, TEXT_PARAGRAPH color) */
  message: string;
  /** Optional secondary hint (11px, TEXT_MUTED color) */
  hint?: string;
  /** Top margin in px. Default: 60 */
  marginTop?: number;
}

const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  message,
  hint,
  marginTop = 60,
}) => (
  <Empty
    image={
      icon ? (
        <span style={{ fontSize: 48, color: '#4a6a8a' }}>{icon}</span>
      ) : (
        Empty.PRESENTED_IMAGE_SIMPLE
      )
    }
    description={
      <div>
        <Text style={{ fontSize: 13, color: TEXT_PARAGRAPH }}>
          {message}
        </Text>
        {hint && (
          <div style={{ marginTop: 8 }}>
            <Text style={{ fontSize: 11, color: TEXT_MUTED }}>
              {hint}
            </Text>
          </div>
        )}
      </div>
    }
    style={{ marginTop }}
  />
);

export default EmptyState;
