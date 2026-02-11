/**
 * Color constants for spatial clustering views.
 */

/** Curated colors for common OT/ICS vendors. */
export const VENDOR_COLORS: Record<string, string> = {
  siemens: '#009999',
  rockwell: '#CC3333',
  'allen-bradley': '#CC3333',
  schneider: '#3DCD58',
  'schneider electric': '#3DCD58',
  abb: '#FF000F',
  honeywell: '#E31937',
  emerson: '#00629B',
  'ge vernova': '#3B7DDD',
  'ge digital': '#3B7DDD',
  yokogawa: '#00A0E9',
  phoenix: '#00843D',
  'phoenix contact': '#00843D',
  beckhoff: '#E2001A',
  wago: '#F39C12',
  moxa: '#E74C3C',
  cisco: '#049FD9',
};

/** Fallback color derived from a string hash. */
export function vendorColor(vendor: string): string {
  if (!vendor) return '#6a9fd4';
  const key = vendor.toLowerCase().trim();
  if (VENDOR_COLORS[key]) return VENDOR_COLORS[key];

  // Simple DJB2-style hash → hue
  let hash = 5381;
  for (let i = 0; i < key.length; i++) {
    hash = ((hash << 5) + hash + key.charCodeAt(i)) & 0xffffffff;
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 65%, 55%)`;
}

/** Colors for Purdue model levels (Level 0 at bottom = green, Level 5 at top = blue). */
export const PURDUE_LEVEL_COLORS: Record<number, string> = {
  0: '#4CAF50',   // Process / Field Devices
  1: '#8BC34A',   // Basic Control
  2: '#CDDC39',   // Area Supervisory
  3: '#FFC107',   // Site Operations
  3.5: '#FF9800', // Industrial DMZ
  4: '#2196F3',   // Site Business
  5: '#3F51B5',   // Enterprise Network
};

/** Human-readable labels for Purdue levels. */
export const PURDUE_LEVEL_LABELS: Record<number, string> = {
  0: 'Level 0: Process',
  1: 'Level 1: Basic Control',
  2: 'Level 2: Supervisory',
  3: 'Level 3: Operations',
  3.5: 'Level 3.5: DMZ',
  4: 'Level 4: Business',
  5: 'Level 5: Enterprise',
};

/** Zone type → border color (mirrors ZoneNode.tsx constants). */
export const ZONE_BORDER_COLORS: Record<string, string> = {
  vertical: '#049FD9',
  network: '#6CC04A',
  vlan: '#9C27B0',
  logical: '#FBAB18',
};
