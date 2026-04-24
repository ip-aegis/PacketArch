/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Modbus TCP protocol configuration types.
 *
 * Modbus TCP is a serial communication protocol widely used in industrial
 * control systems for connecting electronic devices.
 */

/**
 * Modbus function codes supported by the traffic generator.
 */
export type ModbusFunctionCode =
  | 0x01 // Read Coils
  | 0x02 // Read Discrete Inputs
  | 0x03 // Read Holding Registers
  | 0x04 // Read Input Registers
  | 0x05 // Write Single Coil
  | 0x06 // Write Single Register
  | 0x0f // Write Multiple Coils
  | 0x10 // Write Multiple Registers
  | 0x17 // Read/Write Multiple Registers
  | 0x2b; // Read Device Identification (MEI)

/**
 * Register range definition for Modbus operations.
 */
export interface ModbusRegisterRange {
  /** Starting register address (0-65535) */
  start: number;
  /** Number of registers to read/write */
  count: number;
  /** Optional description of what these registers represent */
  description?: string;
}

/**
 * Modbus TCP flow configuration.
 */
export interface ModbusConfig {
  /** Modbus unit ID (slave address, 0-255) */
  unitId: number;

  /** Function codes to use in traffic generation */
  functionCodes: ModbusFunctionCode[];

  /** Register ranges to poll/write */
  registerRanges: ModbusRegisterRange[];

  /** Poll interval in milliseconds */
  pollIntervalMs: number;

  /** Response timeout in milliseconds */
  timeoutMs: number;

  /** Whether to include device identification requests (FC 0x2B) */
  includeDeviceIdentification?: boolean;

  /** Coil ranges for digital I/O operations */
  coilRanges?: ModbusRegisterRange[];

  /** Whether to simulate exception responses */
  simulateExceptions?: boolean;

  /** Exception rate (0-1) if exceptions are enabled */
  exceptionRate?: number;
}

/**
 * Default Modbus configuration for quick setup.
 */
export const DEFAULT_MODBUS_CONFIG: ModbusConfig = {
  unitId: 1,
  functionCodes: [0x03, 0x04], // Read holding and input registers
  registerRanges: [{ start: 0, count: 10 }],
  pollIntervalMs: 1000,
  timeoutMs: 5000,
  includeDeviceIdentification: false,
  simulateExceptions: false,
};
