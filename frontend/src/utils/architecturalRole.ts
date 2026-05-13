/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Resolves a device's architectural role for the canvas rationality
 * checker. Generator-built scenarios populate this directly; legacy /
 * freeform scenarios fall back to a `device.type` heuristic.
 */

import type { ScenarioDevice } from '../types';

/**
 * Best-effort mapping from `device.type` to the closest architectural
 * role ID. Used only when a device lacks an explicit architecturalRole
 * (e.g. legacy templates not yet on the architecture rail, freeform
 * canvas authoring).
 */
const TYPE_TO_ROLE: Record<string, string> = {
  // Control
  plc: 'cell_controller',
  safety_plc: 'safety_controller',
  rtu: 'field_rtu',
  protection_relay: 'protection_relay',
  ied: 'protection_relay',
  dcs_controller: 'dcs_controller',
  controller: 'cell_controller',
  traffic_controller: 'traffic_controller',
  // Area / supervision
  hmi: 'area_hmi',
  // Process
  io_module: 'distributed_io',
  distributed_io: 'distributed_io',
  remote_io: 'distributed_io',
  drive: 'vfd',
  vfd: 'vfd',
  servo: 'servo',
  sensor: 'discrete_sensor',
  instrument: 'field_instrument',
  transmitter: 'field_instrument',
  temperature_controller: 'field_instrument',
  actuator: 'valve_actuator',
  valve: 'valve_actuator',
  // Operations / IDMZ
  scada_server: 'scada_primary',
  historian: 'process_historian',
  workstation: 'engineering_workstation',
  engineering_workstation: 'engineering_workstation',
  jump_server: 'jump_server',
  remote_gateway: 'remote_access_gateway',
  reverse_proxy: 'reverse_proxy',
  nms: 'nms_server',
  server: 'scada_primary', // weak default for generic L3 servers
  // Network
  switch: 'cell_switch',
  router: 'wan_edge_router',
  gateway: 'aggregator_rtu',
};

/**
 * Resolve the architectural role for a device. Returns the explicit
 * `architecturalRole` if set; otherwise infers from `device.type` via
 * the best-effort mapping; otherwise returns `null` (caller decides
 * whether to skip rationality checks).
 *
 * Also tolerates the snake_case `architectural_role` field that some
 * backend-built definitions emit.
 */
export function resolveArchitecturalRole(
  device: ScenarioDevice | undefined,
): string | null {
  if (!device) return null;
  // Prefer explicit field (camelCase from new generator path).
  if (device.architecturalRole) return device.architecturalRole;
  // Snake-case field straight from the backend definition (load-path
  // doesn't currently camel-case unknown fields).
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const snake = (device as any).architectural_role;
  if (typeof snake === 'string' && snake) return snake;
  // Heuristic fallback by device type.
  if (device.type && TYPE_TO_ROLE[device.type]) {
    return TYPE_TO_ROLE[device.type];
  }
  return null;
}
