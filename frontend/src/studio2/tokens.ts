/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Studio v2 design tokens — the single source for every color, size, and
 * type rule on the canvas and its chrome.
 *
 * Color discipline (see design doc §09): each meaning system gets its own
 * channel and its own palette.
 *   - Device category  → glyph stroke ONLY (CATEGORY_ACCENTS)
 *   - Protocol         → edge strokes ONLY (PROTOCOL_EDGE_COLORS, desaturated)
 *   - Status           → the only red/amber/green anywhere (STATUS)
 * Nodes, zones, and chrome are neutral SURFACES. No component in studio2
 * may hardcode a hex value — import from here.
 */

import { DeviceCategory } from '../constants/deviceTypeRegistry';

// ---------------------------------------------------------------------------
// Surfaces & text (dark canvas)
// ---------------------------------------------------------------------------

export const SURFACE = {
  /** Canvas ground */
  ground: '#0C121B',
  /** Dot-grid on the ground */
  grid: '#223145',
  /** Node card */
  node: '#151E2A',
  /** Node icon well */
  iconWell: '#1B2735',
  /** Chrome bars (top bar, rail, bottom strip, inspector) */
  chrome: '#111925',
  /** Raised chrome (menus, popovers) */
  raised: '#1C2836',
  /** Borders */
  border: '#2C3E52',
  /** Hover lift for cards/rows */
  hover: '#1D2A3A',
} as const;

export const TEXT = {
  primary: '#EDF3F9',
  secondary: '#9FB2C6',
  muted: '#7E93A8',
  faint: '#5C7288',
} as const;

/** Single interactive accent for the whole studio (selection, focus, CTAs). */
export const ACCENT = '#43BEE8';
export const ACCENT_SOFT = 'rgba(67, 190, 232, 0.14)';

// ---------------------------------------------------------------------------
// Status — the ONLY semantic colors on the canvas
// ---------------------------------------------------------------------------

export const STATUS = {
  ok: '#5FBF7A',
  warn: '#E8B25C',
  crit: '#E06C5F',
} as const;

export type StatusLevel = keyof typeof STATUS;

// ---------------------------------------------------------------------------
// Device category accents — glyph stroke only, never fills or borders.
// 8 hues cover the 13 registry categories; the glyph shape does the
// fine-grained differentiation.
// ---------------------------------------------------------------------------

export const CATEGORY_ACCENTS: Record<DeviceCategory, string> = {
  [DeviceCategory.CONTROLLER]: '#5FA8E8',
  [DeviceCategory.HMI_WORKSTATION]: '#6FC584',
  [DeviceCategory.DRIVE_ACTUATOR]: '#E2954F',
  [DeviceCategory.SENSOR]: '#52C5BD',
  [DeviceCategory.FIELD_DEVICE]: '#52C5BD',
  [DeviceCategory.SAFETY]: '#E9C46A',
  [DeviceCategory.NETWORK]: '#A78BE0',
  [DeviceCategory.SERVER]: '#93A8BD',
  [DeviceCategory.BUILDING_HVAC]: '#D387C0',
  [DeviceCategory.TRANSPORTATION]: '#D387C0',
  [DeviceCategory.LOGISTICS]: '#D387C0',
  [DeviceCategory.CAMERA]: '#D387C0',
  [DeviceCategory.OTHER]: '#93A8BD',
};

// ---------------------------------------------------------------------------
// Protocol edge palette — edges only. Desaturated so 50 edges read as a
// fabric. Every protocol distinguishable (v1 had SNMP === IEC-104 and
// two near-identical greens).
// ---------------------------------------------------------------------------

export const PROTOCOL_EDGE_COLORS: Record<string, string> = {
  modbus_tcp: '#6E9FD1',
  modbus: '#6E9FD1',
  modbus_rtu: '#6E9FD1',
  ethernet_ip: '#86B36A',
  profinet: '#D0A755',
  s7comm: '#A9B85E',
  s7: '#A9B85E',
  s7comm_plus: '#A9B85E',
  bacnet: '#5FB6CE',
  bacnet_ip: '#5FB6CE',
  snmp: '#C97B96',
  opc_ua: '#9C86CE',
  dnp3: '#C8785A',
  iec_104: '#7B87D4',
  iec104: '#7B87D4',
  iec_61850: '#6FAFA2',
  c37_118: '#B58BB0',
  fins: '#A79A6B',
  slmp: '#8CA6C0',
};

export const PROTOCOL_EDGE_FALLBACK = '#7E93A8';

export function protocolEdgeColor(protocol: string): string {
  return PROTOCOL_EDGE_COLORS[protocol] ?? PROTOCOL_EDGE_FALLBACK;
}

// ---------------------------------------------------------------------------
// Node metrics & typography
// ---------------------------------------------------------------------------

export const NODE = {
  radius: 9,
  iconWellSize: 36,
  glyphSize: 22,
  minWidth: 172,
  nameSize: 13,
  subSize: 10,
  /** Zoom thresholds for the three level-of-detail tiers */
  lodDot: 0.45,
  lodChip: 0.9,
} as const;

export const FONT = {
  ui: `"Avenir Next", "Segoe UI", system-ui, sans-serif`,
  mono: `"JetBrains Mono", "Cascadia Code", "SF Mono", ui-monospace, Consolas, monospace`,
} as const;

// ---------------------------------------------------------------------------
// Zones — near-neutral containers (Phase 2 makes them interactive)
// ---------------------------------------------------------------------------

export const ZONE = {
  fill: 'rgba(67, 190, 232, 0.04)',
  border: 'rgba(67, 190, 232, 0.35)',
  headerBg: '#16222F',
  radius: 10,
} as const;
