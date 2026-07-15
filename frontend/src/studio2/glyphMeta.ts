/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Glyph metadata: device-type -> glyph name / accent color resolution.
 * Separated from glyphs.tsx (the DeviceGlyph component + SVG paths) to
 * satisfy react-refresh/only-export-components.
 */
import { DeviceCategory, getDeviceTypeMeta } from '../constants/deviceTypeRegistry';
import { CATEGORY_ACCENTS } from './tokens';

export type GlyphName =
  | 'plc'
  | 'rtu'
  | 'hmi'
  | 'instrument'
  | 'valve'
  | 'vfd'
  | 'motor'
  | 'io'
  | 'safety'
  | 'switch'
  | 'router'
  | 'firewall'
  | 'gateway'
  | 'server'
  | 'historian'
  | 'ahu'
  | 'thermostat'
  | 'camera'
  | 'robot'
  | 'meter'
  | 'sign'
  | 'generic';

const CATEGORY_GLYPHS: Record<DeviceCategory, GlyphName> = {
  [DeviceCategory.CONTROLLER]: 'plc',
  [DeviceCategory.HMI_WORKSTATION]: 'hmi',
  [DeviceCategory.DRIVE_ACTUATOR]: 'vfd',
  [DeviceCategory.SENSOR]: 'instrument',
  [DeviceCategory.FIELD_DEVICE]: 'io',
  [DeviceCategory.SAFETY]: 'safety',
  [DeviceCategory.NETWORK]: 'switch',
  [DeviceCategory.SERVER]: 'server',
  [DeviceCategory.BUILDING_HVAC]: 'ahu',
  [DeviceCategory.TRANSPORTATION]: 'sign',
  [DeviceCategory.LOGISTICS]: 'robot',
  [DeviceCategory.CAMERA]: 'camera',
  [DeviceCategory.OTHER]: 'generic',
};

const TYPE_GLYPH_OVERRIDES: Record<string, GlyphName> = {
  rtu: 'rtu',
  valve: 'valve',
  valve_positioner: 'valve',
  actuator: 'valve',
  motor: 'motor',
  servo: 'motor',
  scada_server: 'server',
  scada: 'server',
  historian: 'historian',
  router: 'router',
  firewall: 'firewall',
  gateway: 'gateway',
  remote_gateway: 'gateway',
  remote_access: 'gateway',
  thermostat: 'thermostat',
  meter: 'meter',
  power_meter: 'meter',
  energy_meter: 'meter',
  custody_meter: 'meter',
  flow_meter: 'meter',
  weigh_scale: 'meter',
  // Rail / train control. The TRANSPORTATION category glyph is 'sign' (a DMS),
  // which is wrong for these — map each to the glyph that actually fits.
  back_office_server: 'server',
  atcs_office: 'server',
  wayside_interface_unit: 'rtu',
  wayside_mcp: 'rtu',
  atcs_base_station: 'gateway',
  locomotive_computer: 'plc',
  wayside_signal_controller: 'plc',
};

export function glyphNameForType(deviceType: string): GlyphName {
  const override = TYPE_GLYPH_OVERRIDES[deviceType];
  if (override) return override;
  const meta = getDeviceTypeMeta(deviceType);
  return CATEGORY_GLYPHS[meta.category] ?? 'generic';
}

export function accentForType(deviceType: string): string {
  const meta = getDeviceTypeMeta(deviceType);
  return CATEGORY_ACCENTS[meta.category];
}
