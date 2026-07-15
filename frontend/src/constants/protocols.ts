/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Consolidated protocol and device type constants.
 *
 * All protocol colors, short names, device type colors, and select-option
 * lists live here so every component draws from a single source of truth.
 */

import type { ProtocolType } from '../types';

// ---------------------------------------------------------------------------
// Protocol colors - used for edge labels, tags, badges, and charts
// ---------------------------------------------------------------------------

export const PROTOCOL_COLORS: Record<ProtocolType, string> = {
  modbus_tcp: '#049FD9',
  ethernet_ip: '#6CC04A',
  profinet: '#FBAB18',
  s7comm: '#52c41a',
  bacnet: '#00BCD4',
  snmp: '#E91E63',
  opc_ua: '#9C27B0',
  dnp3: '#FF5722',
  iec_104: '#E91E63',
  emp: '#3F51B5',   // rail: PTC / Interoperable Train Control
  atcs: '#795548',  // rail: legacy ATCS codeline
};

/**
 * Extended protocol color map that includes alternate key variants
 * (e.g. "modbus", "s7", "s7comm") found in PCAP-learning data.
 * Use this when the protocol key may come from backend analysis
 * rather than from the canonical ProtocolType union.
 */
export const PROTOCOL_COLORS_EXTENDED: Record<string, string> = {
  ...PROTOCOL_COLORS,
  modbus: '#049FD9',
  modbus_rtu: '#049FD9',
  s7: '#52c41a',
  s7comm: '#52c41a',
  s7comm_plus: '#52c41a',
  bacnet_ip: '#00BCD4',
  snmp: '#E91E63',
  cloud_service: '#FBAB18',
  https: '#FBAB18',
  lldp: '#607D8B',
  cdp: '#607D8B',
  ambient: '#78909C',
  attack: '#F44336',
};

// ---------------------------------------------------------------------------
// Protocol labels - human-readable display names (extended key set)
// ---------------------------------------------------------------------------

export const PROTOCOL_LABELS: Record<string, string> = {
  modbus_tcp: 'Modbus TCP',
  modbus_rtu: 'Modbus RTU',
  modbus: 'Modbus',
  ethernet_ip: 'EtherNet/IP',
  profinet: 'PROFINET',
  s7: 'S7comm',
  s7comm: 'S7comm',
  s7comm_plus: 'S7comm+',
  bacnet: 'BACnet',
  bacnet_ip: 'BACnet/IP',
  snmp: 'SNMP',
  opc_ua: 'OPC UA',
  dnp3: 'DNP3',
  iec104: 'IEC 60870-5-104',
  iec_104: 'IEC 60870-5-104',
  emp: 'EMP (Train Control)',
  atcs: 'ATCS Codeline',
  cloud_service: 'Cloud/TLS',
  https: 'HTTPS',
  lldp: 'LLDP',
  cdp: 'CDP',
  ambient: 'Ambient',
  attack: 'Attack',
};

/** Get color for any protocol key (canonical or extended). */
export function getProtocolColor(protocol: string): string {
  return PROTOCOL_COLORS_EXTENDED[protocol] ?? '#8c8c8c';
}

/** Get human-readable label for any protocol key. */
export function getProtocolLabel(protocol: string): string {
  return PROTOCOL_LABELS[protocol] ?? protocol.replace(/_/g, ' ').toUpperCase();
}

// ---------------------------------------------------------------------------
// Protocol short names - compact labels for canvas nodes and edges
// ---------------------------------------------------------------------------

/** Compact 2-4 char labels used on DeviceNode and PaletteItem badges. */
export const PROTOCOL_SHORT_NAMES: Record<ProtocolType, string> = {
  modbus_tcp: 'MB',
  ethernet_ip: 'EIP',
  profinet: 'PN',
  s7comm: 'S7',
  bacnet: 'BAC',
  snmp: 'SNMP',
  opc_ua: 'OPC',
  dnp3: 'DNP3',
  iec_104: '104',
  emp: 'EMP',
  atcs: 'ATCS',
};

/** Slightly longer names used for FlowEdge labels. */
export const PROTOCOL_EDGE_LABELS: Record<ProtocolType, string> = {
  modbus_tcp: 'MODBUS',
  ethernet_ip: 'EIP',
  profinet: 'PROFINET',
  s7comm: 'S7',
  bacnet: 'BACnet',
  snmp: 'SNMP',
  opc_ua: 'OPC UA',
  dnp3: 'DNP3',
  iec_104: 'IEC 104',
  emp: 'EMP',
  atcs: 'ATCS',
};

// ---------------------------------------------------------------------------
// Protocol select options - for Select/dropdown components
// ---------------------------------------------------------------------------

export const PROTOCOL_OPTIONS: { value: ProtocolType; label: string }[] = [
  { value: 'modbus_tcp', label: 'Modbus TCP' },
  { value: 'ethernet_ip', label: 'EtherNet/IP' },
  { value: 'profinet', label: 'PROFINET' },
  { value: 'opc_ua', label: 'OPC UA' },
  { value: 'dnp3', label: 'DNP3' },
  { value: 'iec_104', label: 'IEC 60870-5-104' },
  { value: 'bacnet', label: 'BACnet' },
  { value: 'emp', label: 'EMP (Train Control)' },
  { value: 'atcs', label: 'ATCS Codeline' },
];

// ---------------------------------------------------------------------------
// Device type colors, labels, options — backed by deviceTypeRegistry
// ---------------------------------------------------------------------------

import {
  DEVICE_TYPE_REGISTRY,
  getDeviceTypeColor,
  getDeviceTypeLabel,
  getDeviceTypeOptions as _getDeviceTypeOptions,
} from './deviceTypeRegistry';

/** Color map for all known device types (backwards-compatible Record<string, string>). */
export const DEVICE_TYPE_COLORS: Record<string, string> = Object.fromEntries(
  Object.values(DEVICE_TYPE_REGISTRY).map((m) => [m.key, m.color]),
);

/** Extended color map — same as DEVICE_TYPE_COLORS (registry covers all types). */
export const DEVICE_TYPE_COLORS_EXTENDED: Record<string, string> = {
  ...DEVICE_TYPE_COLORS,
};

/** Label map for all known device types. */
export const DEVICE_TYPE_LABELS: Record<string, string> = Object.fromEntries(
  Object.values(DEVICE_TYPE_REGISTRY).map((m) => [m.key, m.label]),
);

/** Select options for device type dropdowns. */
export const DEVICE_TYPE_OPTIONS: { value: string; label: string }[] =
  _getDeviceTypeOptions().map(({ value, label }) => ({ value, label }));

// Re-export registry functions for direct use
export { getDeviceTypeColor, getDeviceTypeLabel };
