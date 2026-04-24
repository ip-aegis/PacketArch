/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * PROFINET protocol configuration types.
 *
 * PROFINET is an industry technical standard for data communication
 * over Industrial Ethernet, designed for automation.
 */

/**
 * PROFINET device roles.
 */
export type ProfinetRole = 'controller' | 'device' | 'supervisor';

/**
 * PROFINET communication classes.
 */
export type ProfinetClass = 'RT' | 'IRT'; // Real-Time or Isochronous Real-Time

/**
 * PROFINET slot/subslot definition.
 */
export interface ProfinetSlot {
  /** Slot number */
  slot: number;
  /** Subslot number */
  subslot: number;
  /** Module identifier */
  moduleId?: number;
  /** Submodule identifier */
  submoduleId?: number;
  /** I/O data length */
  ioDataLength?: number;
}

/**
 * PROFINET AR (Application Relationship) parameters.
 */
export interface ProfinetARParams {
  /** AR type (0x0001 = IOCARSingle, 0x0006 = IOSAR) */
  arType: number;
  /** AR UUID (auto-generated if not provided) */
  arUuid?: string;
  /** Session key */
  sessionKey?: number;
  /** AR properties */
  properties?: {
    state: 'active' | 'backup';
    parameterization: boolean;
  };
}

/**
 * PROFINET flow configuration.
 */
export interface ProfinetConfig {
  /** Device role in communication */
  role: ProfinetRole;

  /** Communication class */
  communicationClass: ProfinetClass;

  /** Station name (for DCP identification) */
  stationName: string;

  /** Device type name */
  deviceType?: string;

  /** Vendor ID */
  vendorId?: number;

  /** Device ID */
  deviceId?: number;

  /** Slot/subslot configuration */
  slots: ProfinetSlot[];

  /** AR parameters */
  arParams?: ProfinetARParams;

  /** Send clock factor (31.25us * factor) */
  sendClockFactor?: number;

  /** Reduction ratio */
  reductionRatio?: number;

  /** Update cycle (ms) */
  updateCycleMs: number;

  /** Include DCP identify requests */
  includeDcpIdentify?: boolean;

  /** Include alarm handling */
  includeAlarms?: boolean;
}

/**
 * Default PROFINET configuration for quick setup.
 */
export const DEFAULT_PROFINET_CONFIG: ProfinetConfig = {
  role: 'controller',
  communicationClass: 'RT',
  stationName: 'plc-station',
  slots: [
    { slot: 0, subslot: 1 }, // DAP
    { slot: 1, subslot: 1 }, // First I/O module
  ],
  updateCycleMs: 32,
  includeDcpIdentify: true,
  includeAlarms: false,
};
