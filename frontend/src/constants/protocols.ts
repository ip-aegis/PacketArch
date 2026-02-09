/**
 * Consolidated protocol and device type constants.
 *
 * All protocol colors, short names, device type colors, and select-option
 * lists live here so every component draws from a single source of truth.
 */

import type { DeviceType, ProtocolType } from '../types';

// ---------------------------------------------------------------------------
// Protocol colors - used for edge labels, tags, badges, and charts
// ---------------------------------------------------------------------------

export const PROTOCOL_COLORS: Record<ProtocolType, string> = {
  modbus_tcp: '#049FD9',
  ethernet_ip: '#6CC04A',
  profinet: '#FBAB18',
  opc_ua: '#9C27B0',
  dnp3: '#FF5722',
  iec104: '#E91E63',
  bacnet: '#00BCD4',
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
  opc_ua: 'OPC',
  dnp3: 'DNP3',
  iec104: '104',
  bacnet: 'BAC',
};

/** Slightly longer names used for FlowEdge labels. */
export const PROTOCOL_EDGE_LABELS: Record<ProtocolType, string> = {
  modbus_tcp: 'MODBUS',
  ethernet_ip: 'EIP',
  profinet: 'PROFINET',
  opc_ua: 'OPC UA',
  dnp3: 'DNP3',
  iec104: 'IEC 104',
  bacnet: 'BACnet',
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
  { value: 'iec104', label: 'IEC 60870-5-104' },
  { value: 'bacnet', label: 'BACnet' },
];

// ---------------------------------------------------------------------------
// Device type colors - used for minimap, node backgrounds, badges
// ---------------------------------------------------------------------------

export const DEVICE_TYPE_COLORS: Record<DeviceType, string> = {
  plc: '#049FD9',
  hmi: '#6CC04A',
  rtu: '#FBAB18',
  drive: '#FF7043',
  sensor: '#00BCEB',
  relay: '#E53935',
  ews: '#9C27B0',
  historian: '#607D8B',
};

/**
 * Extended device type color map that includes types beyond the core
 * DeviceType union (e.g. "network", "gateway") used in the Device Library.
 */
export const DEVICE_TYPE_COLORS_EXTENDED: Record<string, string> = {
  ...DEVICE_TYPE_COLORS,
  network: '#00BCD4',
  gateway: '#795548',
};

// ---------------------------------------------------------------------------
// Device type labels - human-readable display names
// ---------------------------------------------------------------------------

export const DEVICE_TYPE_LABELS: Record<DeviceType, string> = {
  plc: 'PLC',
  hmi: 'HMI',
  rtu: 'RTU',
  drive: 'Drive',
  sensor: 'Sensor',
  relay: 'Relay',
  ews: 'EWS',
  historian: 'Historian',
};

// ---------------------------------------------------------------------------
// Device type select options - for Select/dropdown components
// ---------------------------------------------------------------------------

export const DEVICE_TYPE_OPTIONS: { value: DeviceType; label: string }[] = [
  { value: 'plc', label: 'PLC' },
  { value: 'hmi', label: 'HMI' },
  { value: 'rtu', label: 'RTU' },
  { value: 'drive', label: 'Drive' },
  { value: 'sensor', label: 'Sensor' },
  { value: 'relay', label: 'Relay' },
  { value: 'ews', label: 'Engineering Workstation' },
  { value: 'historian', label: 'Historian' },
];
