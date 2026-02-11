/**
 * Shared constants for scenario components.
 * Separated to satisfy react-refresh/only-export-components.
 */

import React from 'react';
import {
  ToolOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  ApiOutlined,
  CarOutlined,
  HomeOutlined,
  InboxOutlined,
} from '@ant-design/icons';

/** Vertical display metadata (icon, color, label) */
export const verticalConfig: Record<
  string,
  { icon: React.ReactNode; color: string; label: string }
> = {
  manufacturing: { icon: <ToolOutlined />, color: '#6CC04A', label: 'Manufacturing' },
  water_wastewater: { icon: <ExperimentOutlined />, color: '#00BCEB', label: 'Water/Wastewater' },
  energy_power: { icon: <ThunderboltOutlined />, color: '#FBAB18', label: 'Energy/Power' },
  oil_gas: { icon: <ApiOutlined />, color: '#FF7043', label: 'Oil & Gas' },
  transportation: { icon: <CarOutlined />, color: '#9C27B0', label: 'Transportation' },
  building_automation: { icon: <HomeOutlined />, color: '#00BCD4', label: 'Building Automation' },
  distribution_logistics: { icon: <InboxOutlined />, color: '#78909C', label: 'Distribution & Logistics' },
};

/** Human-readable duration from milliseconds */
export const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`;
  return `${(ms / 3600000).toFixed(1)}h`;
};
