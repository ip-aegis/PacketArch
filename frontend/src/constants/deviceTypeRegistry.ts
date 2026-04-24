/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Device Type Registry — single source of truth for all device type metadata.
 *
 * Replaces the 4 duplicate hardcoded DEVICE_TYPE_CONFIG maps that were scattered
 * across DeviceNode, PaletteItem, and DevicePalette.
 *
 * Handles 60+ device types across all verticals with category-based grouping
 * and smart fallback for unknown types.
 */

import React from 'react';
import {
  ControlOutlined,
  DesktopOutlined,
  ThunderboltOutlined,
  DashboardOutlined,
  SafetyCertificateOutlined,
  DatabaseOutlined,
  SettingOutlined,
  CloudServerOutlined,
  ApartmentOutlined,
  HomeOutlined,
  CarOutlined,
  RobotOutlined,
  VideoCameraOutlined,
  AppstoreOutlined,
  GlobalOutlined,
  ToolOutlined,
  NodeIndexOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';

// ---------------------------------------------------------------------------
// Categories
// ---------------------------------------------------------------------------

export enum DeviceCategory {
  CONTROLLER = 'controller',
  HMI_WORKSTATION = 'hmi_workstation',
  DRIVE_ACTUATOR = 'drive_actuator',
  SENSOR = 'sensor',
  FIELD_DEVICE = 'field_device',
  SAFETY = 'safety',
  NETWORK = 'network',
  SERVER = 'server',
  BUILDING_HVAC = 'building_hvac',
  TRANSPORTATION = 'transportation',
  LOGISTICS = 'logistics',
  CAMERA = 'camera',
  OTHER = 'other',
}

/** Display order for palette sections and dropdowns. */
export const CATEGORY_ORDER: DeviceCategory[] = [
  DeviceCategory.CONTROLLER,
  DeviceCategory.HMI_WORKSTATION,
  DeviceCategory.DRIVE_ACTUATOR,
  DeviceCategory.SENSOR,
  DeviceCategory.FIELD_DEVICE,
  DeviceCategory.SAFETY,
  DeviceCategory.NETWORK,
  DeviceCategory.SERVER,
  DeviceCategory.BUILDING_HVAC,
  DeviceCategory.TRANSPORTATION,
  DeviceCategory.LOGISTICS,
  DeviceCategory.CAMERA,
  DeviceCategory.OTHER,
];

/** Human-readable category labels for palette section headers. */
export const DEVICE_CATEGORY_LABELS: Record<DeviceCategory, string> = {
  [DeviceCategory.CONTROLLER]: 'Controllers',
  [DeviceCategory.HMI_WORKSTATION]: 'HMIs & Workstations',
  [DeviceCategory.DRIVE_ACTUATOR]: 'Drives & Actuators',
  [DeviceCategory.SENSOR]: 'Sensors & Instruments',
  [DeviceCategory.FIELD_DEVICE]: 'Field Devices & I/O',
  [DeviceCategory.SAFETY]: 'Safety Systems',
  [DeviceCategory.NETWORK]: 'Network Infrastructure',
  [DeviceCategory.SERVER]: 'Servers & Data',
  [DeviceCategory.BUILDING_HVAC]: 'Building & HVAC',
  [DeviceCategory.TRANSPORTATION]: 'Transportation & ITS',
  [DeviceCategory.LOGISTICS]: 'Logistics & Robotics',
  [DeviceCategory.CAMERA]: 'Cameras & Vision',
  [DeviceCategory.OTHER]: 'Other Devices',
};

// ---------------------------------------------------------------------------
// Category defaults (icon component + color)
// ---------------------------------------------------------------------------

interface CategoryDefaults {
  icon: React.ComponentType;
  color: string;
}

const CATEGORY_DEFAULTS: Record<DeviceCategory, CategoryDefaults> = {
  [DeviceCategory.CONTROLLER]: { icon: ControlOutlined, color: '#049FD9' },
  [DeviceCategory.HMI_WORKSTATION]: { icon: DesktopOutlined, color: '#6CC04A' },
  [DeviceCategory.DRIVE_ACTUATOR]: { icon: ThunderboltOutlined, color: '#FF7043' },
  [DeviceCategory.SENSOR]: { icon: DashboardOutlined, color: '#00BCEB' },
  [DeviceCategory.FIELD_DEVICE]: { icon: ToolOutlined, color: '#00BCEB' },
  [DeviceCategory.SAFETY]: { icon: SafetyCertificateOutlined, color: '#E53935' },
  [DeviceCategory.NETWORK]: { icon: ApartmentOutlined, color: '#00BCD4' },
  [DeviceCategory.SERVER]: { icon: DatabaseOutlined, color: '#607D8B' },
  [DeviceCategory.BUILDING_HVAC]: { icon: HomeOutlined, color: '#00BCD4' },
  [DeviceCategory.TRANSPORTATION]: { icon: CarOutlined, color: '#9C27B0' },
  [DeviceCategory.LOGISTICS]: { icon: RobotOutlined, color: '#795548' },
  [DeviceCategory.CAMERA]: { icon: VideoCameraOutlined, color: '#607D8B' },
  [DeviceCategory.OTHER]: { icon: AppstoreOutlined, color: '#8c8c8c' },
};

// ---------------------------------------------------------------------------
// Registry entry type
// ---------------------------------------------------------------------------

export interface DeviceTypeMeta {
  key: string;
  label: string;
  category: DeviceCategory;
  color: string;
  /** Override icon component; if omitted, uses category default. */
  icon?: React.ComponentType;
}

// ---------------------------------------------------------------------------
// Registry — explicit entries for all known device types
// ---------------------------------------------------------------------------

const C = DeviceCategory;

function entry(
  key: string,
  label: string,
  category: DeviceCategory,
  color?: string,
  icon?: React.ComponentType,
): DeviceTypeMeta {
  return { key, label, category, color: color ?? CATEGORY_DEFAULTS[category].color, icon };
}

/**
 * All known device types. Sourced from:
 *  - backend/app/protocol_engines/vendor_oui.py  DEVICE_TYPE_VENDORS
 *  - backend/app/scenario_templates/*.py
 *  - backend/app/services/seed_data.py  DEVICE_PROFILES
 *  - backend/app/services/device_templates/ vendor templates
 */
export const DEVICE_TYPE_REGISTRY: Record<string, DeviceTypeMeta> = {
  // ---- Controllers ----
  plc:                    entry('plc', 'PLC', C.CONTROLLER, '#049FD9', ControlOutlined),
  rtu:                    entry('rtu', 'RTU', C.CONTROLLER, '#FBAB18', CloudServerOutlined),
  dcs_controller:         entry('dcs_controller', 'DCS Controller', C.CONTROLLER),
  traffic_controller:     entry('traffic_controller', 'Traffic Controller', C.CONTROLLER, '#9C27B0', CarOutlined),
  conveyor_controller:    entry('conveyor_controller', 'Conveyor Controller', C.CONTROLLER),
  sortation_controller:   entry('sortation_controller', 'Sortation Controller', C.CONTROLLER),
  compressor_controller:  entry('compressor_controller', 'Compressor Controller', C.CONTROLLER),
  plant_controller:       entry('plant_controller', 'Plant Controller', C.CONTROLLER),
  pump_controller:        entry('pump_controller', 'Pump Controller', C.CONTROLLER),
  wellhead_controller:    entry('wellhead_controller', 'Wellhead Controller', C.CONTROLLER),
  controller:             entry('controller', 'Controller', C.CONTROLLER),

  // ---- HMIs & Workstations ----
  hmi:                    entry('hmi', 'HMI', C.HMI_WORKSTATION, '#6CC04A', DesktopOutlined),
  ews:                    entry('ews', 'EWS', C.HMI_WORKSTATION, '#9C27B0', SettingOutlined),
  engineering_station:    entry('engineering_station', 'Engineering Station', C.HMI_WORKSTATION, undefined, SettingOutlined),
  scada_server:           entry('scada_server', 'SCADA Server', C.HMI_WORKSTATION),
  operator_station:       entry('operator_station', 'Operator Station', C.HMI_WORKSTATION),
  master_station:         entry('master_station', 'Master Station', C.HMI_WORKSTATION),

  // ---- Drives & Actuators ----
  drive:                  entry('drive', 'Drive', C.DRIVE_ACTUATOR, '#FF7043', ThunderboltOutlined),
  servo:                  entry('servo', 'Servo', C.DRIVE_ACTUATOR),
  motor:                  entry('motor', 'Motor', C.DRIVE_ACTUATOR),
  motion_controller:      entry('motion_controller', 'Motion Controller', C.DRIVE_ACTUATOR),
  actuator:               entry('actuator', 'Actuator', C.DRIVE_ACTUATOR),
  valve:                  entry('valve', 'Valve', C.DRIVE_ACTUATOR),
  valve_positioner:       entry('valve_positioner', 'Valve Positioner', C.DRIVE_ACTUATOR),

  // ---- Sensors & Instruments ----
  sensor:                 entry('sensor', 'Sensor', C.SENSOR, '#00BCEB', DashboardOutlined),
  flow_meter:             entry('flow_meter', 'Flow Meter', C.SENSOR),
  flow_sensor:            entry('flow_sensor', 'Flow Sensor', C.SENSOR),
  level_sensor:           entry('level_sensor', 'Level Sensor', C.SENSOR),
  level_gauge:            entry('level_gauge', 'Level Gauge', C.SENSOR),
  pressure_sensor:        entry('pressure_sensor', 'Pressure Sensor', C.SENSOR),
  pressure_transmitter:   entry('pressure_transmitter', 'Pressure Transmitter', C.SENSOR),
  flow_transmitter:       entry('flow_transmitter', 'Flow Transmitter', C.SENSOR),
  level_transmitter:      entry('level_transmitter', 'Level Transmitter', C.SENSOR),
  temperature_transmitter: entry('temperature_transmitter', 'Temperature Transmitter', C.SENSOR),
  transmitter:            entry('transmitter', 'Transmitter', C.SENSOR),
  meter:                  entry('meter', 'Meter', C.SENSOR),
  power_meter:            entry('power_meter', 'Power Meter', C.SENSOR),
  energy_meter:           entry('energy_meter', 'Energy Meter', C.SENSOR),
  custody_meter:          entry('custody_meter', 'Custody Meter', C.SENSOR),
  flow_computer:          entry('flow_computer', 'Flow Computer', C.SENSOR),
  radar_sensor:           entry('radar_sensor', 'Radar Sensor', C.SENSOR),
  thermal_sensor:         entry('thermal_sensor', 'Thermal Sensor', C.SENSOR),
  weather_station:        entry('weather_station', 'Weather Station', C.SENSOR),
  analyzer:               entry('analyzer', 'Analyzer', C.SENSOR, undefined, ExperimentOutlined),
  process_analyzer:       entry('process_analyzer', 'Process Analyzer', C.SENSOR, undefined, ExperimentOutlined),
  gas_chromatograph:      entry('gas_chromatograph', 'Gas Chromatograph', C.SENSOR, undefined, ExperimentOutlined),
  instrument:             entry('instrument', 'Instrument', C.SENSOR),
  field_instrument:       entry('field_instrument', 'Field Instrument', C.SENSOR),
  weigh_scale:            entry('weigh_scale', 'Weigh Scale', C.SENSOR),
  classification_sensor:  entry('classification_sensor', 'Classification Sensor', C.SENSOR),
  chem_sensor:            entry('chem_sensor', 'Chemical Sensor', C.SENSOR),
  seismic_sensor:         entry('seismic_sensor', 'Seismic Sensor', C.SENSOR),

  // ---- Field Devices & I/O ----
  io_module:              entry('io_module', 'I/O Module', C.FIELD_DEVICE),
  remote_io:              entry('remote_io', 'Remote I/O', C.FIELD_DEVICE),
  communication_module:   entry('communication_module', 'Communication Module', C.FIELD_DEVICE),
  temperature_controller: entry('temperature_controller', 'Temperature Controller', C.FIELD_DEVICE),

  // ---- Safety Systems ----
  safety_plc:             entry('safety_plc', 'Safety PLC', C.SAFETY),
  safety_io:              entry('safety_io', 'Safety I/O', C.SAFETY),
  relay:                  entry('relay', 'Relay', C.SAFETY, '#E53935', SafetyCertificateOutlined),
  protection_relay:       entry('protection_relay', 'Protection Relay', C.SAFETY),
  fire_panel:             entry('fire_panel', 'Fire Panel', C.SAFETY),
  leak_detection:         entry('leak_detection', 'Leak Detection', C.SAFETY),

  // ---- Network Infrastructure ----
  switch:                 entry('switch', 'Switch', C.NETWORK, undefined, ApartmentOutlined),
  network_switch:         entry('network_switch', 'Network Switch', C.NETWORK, undefined, ApartmentOutlined),
  router:                 entry('router', 'Router', C.NETWORK, undefined, NodeIndexOutlined),
  gateway:                entry('gateway', 'Gateway', C.NETWORK, '#795548', GlobalOutlined),
  remote_gateway:         entry('remote_gateway', 'Remote Gateway', C.NETWORK, '#795548', GlobalOutlined),
  firewall:               entry('firewall', 'Firewall', C.NETWORK),
  remote_access:          entry('remote_access', 'Remote Access', C.NETWORK),

  // ---- Servers & Data ----
  historian:              entry('historian', 'Historian', C.SERVER, '#607D8B', DatabaseOutlined),
  server:                 entry('server', 'Server', C.SERVER),
  bms_server:             entry('bms_server', 'BMS Server', C.SERVER),
  scada:                  entry('scada', 'SCADA', C.SERVER),
  jump_server:            entry('jump_server', 'Jump Server', C.SERVER),
  dcim_server:            entry('dcim_server', 'DCIM Server', C.SERVER),

  // ---- Building & HVAC ----
  bac:                    entry('bac', 'Building Controller', C.BUILDING_HVAC),
  building_controller:    entry('building_controller', 'Building Controller', C.BUILDING_HVAC),
  bms_controller:         entry('bms_controller', 'BMS Controller', C.BUILDING_HVAC),
  hvac_controller:        entry('hvac_controller', 'HVAC Controller', C.BUILDING_HVAC),
  ahu_controller:         entry('ahu_controller', 'AHU Controller', C.BUILDING_HVAC),
  vav_controller:         entry('vav_controller', 'VAV Controller', C.BUILDING_HVAC),
  chiller_controller:     entry('chiller_controller', 'Chiller Controller', C.BUILDING_HVAC),
  boiler_controller:      entry('boiler_controller', 'Boiler Controller', C.BUILDING_HVAC),
  rooftop_unit:           entry('rooftop_unit', 'Rooftop Unit', C.BUILDING_HVAC),
  crac_unit:              entry('crac_unit', 'CRAC Unit', C.BUILDING_HVAC),
  thermostat:             entry('thermostat', 'Thermostat', C.BUILDING_HVAC),
  room_controller:        entry('room_controller', 'Room Controller', C.BUILDING_HVAC),
  zone_controller:        entry('zone_controller', 'Zone Controller', C.BUILDING_HVAC),
  field_controller:       entry('field_controller', 'Field Controller', C.BUILDING_HVAC),
  lighting_controller:    entry('lighting_controller', 'Lighting Controller', C.BUILDING_HVAC),
  ventilation_controller: entry('ventilation_controller', 'Ventilation Controller', C.BUILDING_HVAC),
  access_panel:           entry('access_panel', 'Access Panel', C.BUILDING_HVAC),
  access_controller:      entry('access_controller', 'Access Controller', C.BUILDING_HVAC),
  pdu:                    entry('pdu', 'PDU', C.BUILDING_HVAC),
  ups:                    entry('ups', 'UPS', C.BUILDING_HVAC),
  niagara_jace:           entry('niagara_jace', 'Niagara JACE', C.BUILDING_HVAC),
  webctrl:                entry('webctrl', 'WebCTRL', C.BUILDING_HVAC),
  metasys:                entry('metasys', 'Metasys', C.BUILDING_HVAC),
  tracer:                 entry('tracer', 'Tracer', C.BUILDING_HVAC),

  // ---- Transportation & ITS ----
  dms:                    entry('dms', 'DMS', C.TRANSPORTATION),
  dms_sign:               entry('dms_sign', 'DMS Sign', C.TRANSPORTATION),
  dynamic_message_sign:   entry('dynamic_message_sign', 'Dynamic Message Sign', C.TRANSPORTATION),
  toll_system:            entry('toll_system', 'Toll System', C.TRANSPORTATION),
  toll_controller:        entry('toll_controller', 'Toll Controller', C.TRANSPORTATION),
  toll_host:              entry('toll_host', 'Toll Host', C.TRANSPORTATION),
  toll_rsu:               entry('toll_rsu', 'Toll RSU', C.TRANSPORTATION),
  lane_controller:        entry('lane_controller', 'Lane Controller', C.TRANSPORTATION),
  rsu:                    entry('rsu', 'RSU', C.TRANSPORTATION),
  roadside_unit:          entry('roadside_unit', 'Roadside Unit', C.TRANSPORTATION),
  detector_rack:          entry('detector_rack', 'Detector Rack', C.TRANSPORTATION),
  barrier_controller:     entry('barrier_controller', 'Barrier Controller', C.TRANSPORTATION),

  // ---- Logistics & Robotics ----
  agv:                    entry('agv', 'AGV', C.LOGISTICS),
  amr:                    entry('amr', 'AMR', C.LOGISTICS),
  agv_controller:         entry('agv_controller', 'AGV Controller', C.LOGISTICS),
  robot_controller:       entry('robot_controller', 'Robot Controller', C.LOGISTICS),
  fleet_manager:          entry('fleet_manager', 'Fleet Manager', C.LOGISTICS),
  barcode_scanner:        entry('barcode_scanner', 'Barcode Scanner', C.LOGISTICS),
  rfid_reader:            entry('rfid_reader', 'RFID Reader', C.LOGISTICS),
  rfid_gateway:           entry('rfid_gateway', 'RFID Gateway', C.LOGISTICS),
  pick_to_light:          entry('pick_to_light', 'Pick-to-Light', C.LOGISTICS),
  label_applicator:       entry('label_applicator', 'Label Applicator', C.LOGISTICS),
  cold_storage_controller: entry('cold_storage_controller', 'Cold Storage Controller', C.LOGISTICS),

  // ---- Cameras & Vision ----
  camera:                 entry('camera', 'Camera', C.CAMERA),
  camera_fixed:           entry('camera_fixed', 'Fixed Camera', C.CAMERA),
  camera_ptz:             entry('camera_ptz', 'PTZ Camera', C.CAMERA),
  camera_anpr:            entry('camera_anpr', 'ANPR Camera', C.CAMERA),
  ip_camera:              entry('ip_camera', 'IP Camera', C.CAMERA),
  its_camera:             entry('its_camera', 'ITS Camera', C.CAMERA),
  ptz_camera:             entry('ptz_camera', 'PTZ Camera', C.CAMERA),
  anpr_camera:            entry('anpr_camera', 'ANPR Camera', C.CAMERA),
  video_detector:         entry('video_detector', 'Video Detector', C.CAMERA),
  vision_system:          entry('vision_system', 'Vision System', C.CAMERA),
  vision_sensor:          entry('vision_sensor', 'Vision Sensor', C.CAMERA),
};

// ---------------------------------------------------------------------------
// Category inference for unknown types
// ---------------------------------------------------------------------------

function inferCategory(type: string): DeviceCategory {
  const t = type.toLowerCase();

  // Order matters — more specific checks first
  if (t.includes('safety') || t.includes('leak_detection') || t.includes('fire_panel')) return DeviceCategory.SAFETY;
  if (t.includes('camera') || t.includes('ptz') || t.includes('anpr') || t.includes('vision')) return DeviceCategory.CAMERA;
  if (t.includes('agv') || t.includes('amr') || t.includes('robot') || t.includes('conveyor') ||
      t.includes('barcode') || t.includes('rfid') || t.includes('fleet') || t.includes('pick_to_light') ||
      t.includes('label_applicator') || t.includes('cold_storage')) return DeviceCategory.LOGISTICS;
  if (t.includes('hvac') || t.includes('ahu') || t.includes('vav') || t.includes('chiller') ||
      t.includes('boiler') || t.includes('thermostat') || t.includes('rooftop') || t.includes('crac') ||
      t.includes('building') || t.includes('room_controller') || t.includes('zone_controller') ||
      t.includes('lighting') || t.includes('ventilation') || t.includes('access_panel') ||
      t.includes('access_controller') || t === 'bac' || t === 'pdu' || t === 'ups') return DeviceCategory.BUILDING_HVAC;
  if (t.includes('traffic') || t.includes('toll') || t.includes('dms') || t === 'rsu' ||
      t.includes('roadside') || t.includes('lane_controller') || t.includes('detector_rack') ||
      t.includes('barrier_controller')) return DeviceCategory.TRANSPORTATION;
  if (t.includes('switch') || t.includes('router') || t.includes('gateway') || t.includes('firewall') ||
      t.includes('remote_access')) return DeviceCategory.NETWORK;
  if (t.includes('drive') || t.includes('servo') || t.includes('actuator') || t.includes('valve') ||
      t.includes('motor') || t.includes('motion_controller')) return DeviceCategory.DRIVE_ACTUATOR;
  if (t.includes('sensor') || t.includes('transmitter') || t.includes('meter') || t.includes('analyzer') ||
      t.includes('chromatograph') || t.includes('instrument') || t.includes('weather_station') ||
      t.includes('flow_computer') || t.includes('weigh_scale')) return DeviceCategory.SENSOR;
  if (t.includes('io_module') || t.includes('remote_io') || t.includes('communication_module') ||
      t.includes('temperature_controller')) return DeviceCategory.FIELD_DEVICE;
  if (t.includes('historian') || t.includes('server') || t.includes('database') || t === 'scada') return DeviceCategory.SERVER;
  if (t.includes('hmi') || t.includes('workstation') || t === 'ews' || t.includes('scada_server') ||
      t.includes('operator_station') || t.includes('master_station')) return DeviceCategory.HMI_WORKSTATION;
  if (t.includes('plc') || t.includes('controller') || t === 'rtu') return DeviceCategory.CONTROLLER;

  return DeviceCategory.OTHER;
}

/** Convert a type key to a human-readable label (e.g. "safety_plc" → "Safety PLC"). */
function humanize(type: string): string {
  return type
    .split('_')
    .map((w) => {
      const upper = w.toUpperCase();
      // Keep common acronyms uppercase
      if (['plc', 'hmi', 'rtu', 'ews', 'io', 'dcs', 'bms', 'hvac', 'ahu', 'vav',
           'dms', 'rsu', 'agv', 'amr', 'rfid', 'pdu', 'ups', 'ptz', 'anpr', 'ip',
           'its', 'scada', 'crac', 'dcim', 'bac'].includes(w.toLowerCase())) {
        return upper;
      }
      return w.charAt(0).toUpperCase() + w.slice(1);
    })
    .join(' ');
}

// ---------------------------------------------------------------------------
// Lookup functions
// ---------------------------------------------------------------------------

/**
 * Get full metadata for a device type.
 * Falls back to category inference → OTHER for unknown types.
 */
export function getDeviceTypeMeta(type: string): DeviceTypeMeta {
  if (!type) {
    return {
      key: 'unknown',
      label: 'Unknown',
      category: DeviceCategory.OTHER,
      color: CATEGORY_DEFAULTS[DeviceCategory.OTHER].color,
    };
  }
  const existing = DEVICE_TYPE_REGISTRY[type];
  if (existing) return existing;

  // Build a fallback entry from category inference
  const category = inferCategory(type);
  return {
    key: type,
    label: humanize(type),
    category,
    color: CATEGORY_DEFAULTS[category].color,
  };
}

/** Get the icon JSX element for a device type. */
export function getDeviceTypeIcon(type: string): React.ReactNode {
  const meta = getDeviceTypeMeta(type);
  const IconComponent = meta.icon ?? CATEGORY_DEFAULTS[meta.category].icon;
  return React.createElement(IconComponent);
}

/** Get the display color for a device type. */
export function getDeviceTypeColor(type: string): string {
  return getDeviceTypeMeta(type).color;
}

/** Get the human-readable label for a device type. */
export function getDeviceTypeLabel(type: string): string {
  return getDeviceTypeMeta(type).label;
}

/**
 * Get all known device types grouped by category, in display order.
 * Used by DevicePalette for section grouping.
 */
export function getDeviceTypesByCategory(): [DeviceCategory, DeviceTypeMeta[]][] {
  const groups = new Map<DeviceCategory, DeviceTypeMeta[]>();
  for (const cat of CATEGORY_ORDER) {
    groups.set(cat, []);
  }
  for (const meta of Object.values(DEVICE_TYPE_REGISTRY)) {
    groups.get(meta.category)?.push(meta);
  }
  return CATEGORY_ORDER
    .map((cat) => [cat, groups.get(cat) ?? []] as [DeviceCategory, DeviceTypeMeta[]])
    .filter(([, entries]) => entries.length > 0);
}

/**
 * Get device type options for Select dropdowns, grouped by category.
 */
export function getDeviceTypeOptions(): { value: string; label: string; category: string }[] {
  const options: { value: string; label: string; category: string }[] = [];
  for (const [cat, types] of getDeviceTypesByCategory()) {
    for (const t of types) {
      options.push({ value: t.key, label: t.label, category: DEVICE_CATEGORY_LABELS[cat] });
    }
  }
  return options;
}
