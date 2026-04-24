/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React from 'react';

export interface PanelContainerProps {
  children: React.ReactNode;
  /** Gap between child elements in px. Default: 16 */
  gap?: number;
  /** Padding in px. Default: 16 */
  padding?: number;
  /** Additional inline styles */
  style?: React.CSSProperties;
}

const PanelContainer: React.FC<PanelContainerProps> = ({
  children,
  gap = 16,
  padding = 16,
  style,
}) => (
  <div
    style={{
      padding,
      height: '100%',
      overflowY: 'auto',
      display: 'flex',
      flexDirection: 'column',
      gap,
      ...style,
    }}
  >
    {children}
  </div>
);

export default PanelContainer;
