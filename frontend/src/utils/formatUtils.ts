/**
 * Formatting utilities for the live traffic dashboard.
 */

export function formatPacketRate(pps: number): string {
  if (pps >= 1_000_000) return `${(pps / 1_000_000).toFixed(1)}M`;
  if (pps >= 1_000) return `${(pps / 1_000).toFixed(1)}K`;
  return `${Math.round(pps)}`;
}

export function formatBandwidth(bytesPerSec: number): string {
  const bits = bytesPerSec * 8;
  if (bits >= 1_000_000_000) return `${(bits / 1_000_000_000).toFixed(2)} Gbps`;
  if (bits >= 1_000_000) return `${(bits / 1_000_000).toFixed(1)} Mbps`;
  if (bits >= 1_000) return `${(bits / 1_000).toFixed(1)} Kbps`;
  return `${Math.round(bits)} bps`;
}

export function formatBytes(bytes: number): string {
  if (bytes >= 1_073_741_824) return `${(bytes / 1_073_741_824).toFixed(2)} GB`;
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

export function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${secs}s`;
  return `${secs}s`;
}

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return `${n}`;
}

/** Protocol display name and color mapping */
export const PROTOCOL_COLORS: Record<string, { color: string; label: string }> = {
  modbus_tcp: { color: '#1890ff', label: 'Modbus TCP' },
  modbus_rtu: { color: '#1890ff', label: 'Modbus RTU' },
  ethernet_ip: { color: '#52c41a', label: 'EtherNet/IP' },
  profinet: { color: '#722ed1', label: 'PROFINET' },
  s7comm: { color: '#fa8c16', label: 'S7comm' },
  s7comm_plus: { color: '#fa8c16', label: 'S7comm+' },
  bacnet_ip: { color: '#13c2c2', label: 'BACnet/IP' },
  bacnet: { color: '#13c2c2', label: 'BACnet' },
  snmp: { color: '#eb2f96', label: 'SNMP' },
  cloud_service: { color: '#faad14', label: 'Cloud/TLS' },
  https: { color: '#faad14', label: 'HTTPS' },
  lldp: { color: '#8c8c8c', label: 'LLDP' },
  cdp: { color: '#8c8c8c', label: 'CDP' },
};

export function getProtocolColor(protocol: string): string {
  return PROTOCOL_COLORS[protocol]?.color ?? '#8c8c8c';
}

export function getProtocolLabel(protocol: string): string {
  return PROTOCOL_COLORS[protocol]?.label ?? protocol.replace(/_/g, ' ').toUpperCase();
}
