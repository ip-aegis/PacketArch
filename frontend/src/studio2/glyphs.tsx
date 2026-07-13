/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 OT glyph set — purpose-built equipment silhouettes replacing
 * the generic Ant Design icons. Drawn on a 24px grid, uniform 1.6 stroke,
 * several straight from ISA-5.1 / P&ID convention (instrument bubble,
 * bowtie valve). Colored via `currentColor` — pass the category accent.
 *
 * Resolution mirrors deviceTypeRegistry: specific type overrides first,
 * then the type's category default.
 */

import React from 'react';
import { accentForType, glyphNameForType, type GlyphName } from './glyphMeta';

// Type-only re-export for back-compat (safe for react-refresh). Value helpers
// (glyphNameForType/accentForType) moved to ./glyphMeta — import from there.
export type { GlyphName } from './glyphMeta';

const svgProps = (size: number): React.SVGProps<SVGSVGElement> => ({
  viewBox: '0 0 24 24',
  width: size,
  height: size,
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.6,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
});

const GLYPH_PATHS: Record<GlyphName, React.ReactNode> = {
  plc: (
    <>
      <rect x="3.5" y="4.5" width="17" height="15" rx="1.5" />
      <line x1="9.5" y1="4.5" x2="9.5" y2="19.5" />
      <circle cx="6.5" cy="8.5" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="6.5" cy="12" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="6.5" cy="15.5" r="0.9" fill="currentColor" stroke="none" />
      <line x1="12" y1="8.5" x2="18" y2="8.5" />
      <line x1="12" y1="12" x2="18" y2="12" />
      <line x1="12" y1="15.5" x2="18" y2="15.5" />
    </>
  ),
  rtu: (
    <>
      <rect x="3.5" y="9" width="17" height="10.5" rx="1.5" />
      <line x1="12" y1="9" x2="12" y2="5" />
      <path d="M8.5,4.5 a5,5 0 0 1 7,0" />
      <circle cx="7" cy="14.25" r="0.9" fill="currentColor" stroke="none" />
      <line x1="10.5" y1="14.25" x2="17.5" y2="14.25" />
    </>
  ),
  hmi: (
    <>
      <rect x="3" y="4" width="18" height="12.5" rx="1.5" />
      <polyline points="5.5,13 8.5,9.5 11.5,11.5 15,7.5 18.5,9" />
      <line x1="12" y1="16.5" x2="12" y2="19.5" />
      <line x1="8" y1="20" x2="16" y2="20" />
    </>
  ),
  instrument: (
    <>
      <circle cx="12" cy="9.5" r="6" />
      <line x1="6" y1="9.5" x2="18" y2="9.5" />
      <line x1="12" y1="15.5" x2="12" y2="20.5" />
    </>
  ),
  valve: (
    <>
      <path d="M4,8 v9 l8,-4.5 8,4.5 v-9 l-8,4.5 Z" />
      <line x1="12" y1="12.5" x2="12" y2="6.5" />
      <line x1="8.5" y1="6.5" x2="15.5" y2="6.5" />
    </>
  ),
  vfd: (
    <>
      <rect x="3" y="5.5" width="18" height="13" rx="1.8" />
      <path d="M6,12 q1.5,-4.5 3,0 t3,0 t3,0 t3,0" />
    </>
  ),
  motor: (
    <>
      <circle cx="11" cy="12" r="7" />
      <path d="M8,15 v-6 l3,4 3,-4 v6" />
      <line x1="18" y1="9.5" x2="21" y2="9.5" />
      <line x1="18" y1="14.5" x2="21" y2="14.5" />
    </>
  ),
  io: (
    <>
      <rect x="5" y="3.5" width="14" height="17" rx="1.5" />
      <line x1="12" y1="3.5" x2="12" y2="20.5" />
      <circle cx="8.5" cy="7" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="8.5" cy="12" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="8.5" cy="17" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="15.5" cy="7" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="15.5" cy="12" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="15.5" cy="17" r="0.9" fill="currentColor" stroke="none" />
    </>
  ),
  safety: (
    <>
      <path d="M12,3 l7,2.8 v5.4 c0,4.6 -3,7.6 -7,9.8 c-4,-2.2 -7,-5.2 -7,-9.8 V5.8 Z" />
      <polyline points="8.8,11.8 11.2,14.2 15.4,9.6" />
    </>
  ),
  switch: (
    <>
      <rect x="3" y="7" width="18" height="10" rx="1.5" />
      <line x1="7" y1="10.4" x2="15.5" y2="10.4" />
      <polyline points="13.5,8.7 16,10.4 13.5,12.1" />
      <line x1="8.5" y1="13.8" x2="17" y2="13.8" />
      <polyline points="11,12.1 8.5,13.8 11,15.5" />
    </>
  ),
  router: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <line x1="8" y1="9" x2="14.5" y2="9" />
      <polyline points="12.8,7.2 14.8,9 12.8,10.8" />
      <line x1="16" y1="15" x2="9.5" y2="15" />
      <polyline points="11.2,13.2 9.2,15 11.2,16.8" />
    </>
  ),
  firewall: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="1" />
      <line x1="3" y1="9.7" x2="21" y2="9.7" />
      <line x1="3" y1="14.3" x2="21" y2="14.3" />
      <line x1="9" y1="5" x2="9" y2="9.7" />
      <line x1="15" y1="5" x2="15" y2="9.7" />
      <line x1="6" y1="9.7" x2="6" y2="14.3" />
      <line x1="12" y1="9.7" x2="12" y2="14.3" />
      <line x1="18" y1="9.7" x2="18" y2="14.3" />
      <line x1="9" y1="14.3" x2="9" y2="19" />
      <line x1="15" y1="14.3" x2="15" y2="19" />
    </>
  ),
  gateway: (
    <>
      <rect x="3" y="3" width="11" height="11" rx="1.5" />
      <rect x="10" y="10" width="11" height="11" rx="1.5" />
      <line x1="8.5" y1="8.5" x2="15.5" y2="15.5" />
    </>
  ),
  server: (
    <>
      <rect x="4" y="3.5" width="16" height="6.5" rx="1.2" />
      <rect x="4" y="14" width="16" height="6.5" rx="1.2" />
      <circle cx="7" cy="6.75" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="7" cy="17.25" r="0.9" fill="currentColor" stroke="none" />
      <line x1="10.5" y1="6.75" x2="17" y2="6.75" />
      <line x1="10.5" y1="17.25" x2="17" y2="17.25" />
    </>
  ),
  historian: (
    <>
      <ellipse cx="12" cy="5.5" rx="7" ry="2.5" />
      <path d="M5,5.5 v13 a7,2.5 0 0 0 14,0 v-13" />
      <path d="M5,12 a7,2.5 0 0 0 14,0" />
    </>
  ),
  ahu: (
    <>
      <rect x="3.5" y="3.5" width="17" height="17" rx="2" />
      <circle cx="12" cy="12" r="5.5" />
      <circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none" />
      <line x1="12" y1="12" x2="12" y2="7.4" />
      <line x1="12" y1="12" x2="16" y2="14.3" />
      <line x1="12" y1="12" x2="8" y2="14.3" />
    </>
  ),
  thermostat: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="4" />
      <line x1="12" y1="8" x2="12" y2="12" />
    </>
  ),
  camera: (
    <>
      <rect x="3" y="8" width="12" height="8.5" rx="1.5" />
      <path d="M15,10.5 l6,-2.8 v9.1 l-6,-2.8 Z" />
      <circle cx="9" cy="12.25" r="2" />
    </>
  ),
  robot: (
    <>
      <line x1="5" y1="20.5" x2="15" y2="20.5" />
      <rect x="7.5" y="16.5" width="5" height="4" rx="1" />
      <line x1="10" y1="16.5" x2="14" y2="9" />
      <line x1="14" y1="9" x2="19" y2="12" />
      <circle cx="14" cy="9" r="1.4" />
      <circle cx="19.2" cy="12.2" r="1.4" />
    </>
  ),
  meter: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <line x1="12" y1="12" x2="16.5" y2="8.5" />
      <circle cx="12" cy="12" r="1.1" fill="currentColor" stroke="none" />
      <line x1="6" y1="15.5" x2="7.5" y2="14.7" />
      <line x1="18" y1="15.5" x2="16.5" y2="14.7" />
    </>
  ),
  sign: (
    <>
      <rect x="3" y="4.5" width="18" height="10" rx="1.2" />
      <line x1="6" y1="8" x2="10" y2="8" />
      <line x1="13" y1="8" x2="18" y2="8" />
      <line x1="6" y1="11" x2="12" y2="11" />
      <line x1="9" y1="14.5" x2="9" y2="20" />
      <line x1="15" y1="14.5" x2="15" y2="20" />
    </>
  ),
  generic: (
    <>
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <circle cx="12" cy="12" r="2" fill="currentColor" stroke="none" />
    </>
  ),
};

// ---------------------------------------------------------------------------
// Resolution: specific type → glyph overrides, else category default
// ---------------------------------------------------------------------------

export interface DeviceGlyphProps {
  deviceType: string;
  size?: number;
  /** Override stroke color; defaults to the category accent. */
  color?: string;
}

export const DeviceGlyph: React.FC<DeviceGlyphProps> = ({ deviceType, size = 22, color }) => (
  <svg {...svgProps(size)} style={{ color: color ?? accentForType(deviceType), display: 'block' }}>
    {GLYPH_PATHS[glyphNameForType(deviceType)]}
  </svg>
);
