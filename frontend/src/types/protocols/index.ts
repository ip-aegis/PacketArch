/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Protocol-specific configuration types.
 *
 * This module provides type-safe configuration for all supported OT protocols,
 * replacing generic Record<string, unknown> with properly typed interfaces.
 *
 * Usage:
 *   import { ProtocolConfig, isModbusConfig } from '@/types/protocols';
 *
 *   // Type-safe protocol configuration
 *   const flow: ScenarioFlow = {
 *     protocol: 'modbus_tcp',
 *     protocolConfig: {
 *       protocol: 'modbus_tcp',
 *       config: {
 *         unitId: 1,
 *         functionCodes: [0x03],
 *         // ... typed fields
 *       }
 *     }
 *   };
 *
 *   // Type guards for runtime checking
 *   if (isModbusConfig(flow.protocolConfig)) {
 *     console.log(flow.protocolConfig.config.unitId);
 *   }
 */

// Re-export all protocol types
export * from './modbus';
export * from './ethernet-ip';
export * from './profinet';
export * from './s7';
export * from './bacnet';
export * from './snmp';

// Import config types and default constants for the discriminated union
import { type ModbusConfig, DEFAULT_MODBUS_CONFIG } from './modbus';
import { type EtherNetIPConfig, DEFAULT_ETHERNET_IP_CONFIG } from './ethernet-ip';
import { type ProfinetConfig, DEFAULT_PROFINET_CONFIG } from './profinet';
import { type S7Config, DEFAULT_S7_CONFIG } from './s7';
import { type BACnetConfig, DEFAULT_BACNET_CONFIG } from './bacnet';
import { type SNMPConfig, DEFAULT_SNMP_CONFIG } from './snmp';

/**
 * Protocol type literals for type-safe protocol identification.
 */
export type Protocol =
  | 'modbus_tcp'
  | 'ethernet_ip'
  | 'profinet'
  | 's7comm'
  | 'bacnet'
  | 'snmp';

/**
 * Discriminated union for protocol configurations.
 *
 * This enables type-safe access to protocol-specific fields based on the
 * protocol discriminator.
 *
 * Example:
 *   function processConfig(config: ProtocolConfig) {
 *     switch (config.protocol) {
 *       case 'modbus_tcp':
 *         // TypeScript knows config.config is ModbusConfig
 *         console.log(config.config.unitId);
 *         break;
 *       case 'ethernet_ip':
 *         // TypeScript knows config.config is EtherNetIPConfig
 *         console.log(config.config.connectionType);
 *         break;
 *       // ... other protocols
 *     }
 *   }
 */
export type ProtocolConfig =
  | { protocol: 'modbus_tcp'; config: ModbusConfig }
  | { protocol: 'ethernet_ip'; config: EtherNetIPConfig }
  | { protocol: 'profinet'; config: ProfinetConfig }
  | { protocol: 's7comm'; config: S7Config }
  | { protocol: 'bacnet'; config: BACnetConfig }
  | { protocol: 'snmp'; config: SNMPConfig };

/**
 * Type guard for Modbus configuration.
 */
export function isModbusConfig(
  config: ProtocolConfig | unknown
): config is { protocol: 'modbus_tcp'; config: ModbusConfig } {
  return (
    typeof config === 'object' &&
    config !== null &&
    'protocol' in config &&
    (config as ProtocolConfig).protocol === 'modbus_tcp'
  );
}

/**
 * Type guard for EtherNet/IP configuration.
 */
export function isEtherNetIPConfig(
  config: ProtocolConfig | unknown
): config is { protocol: 'ethernet_ip'; config: EtherNetIPConfig } {
  return (
    typeof config === 'object' &&
    config !== null &&
    'protocol' in config &&
    (config as ProtocolConfig).protocol === 'ethernet_ip'
  );
}

/**
 * Type guard for PROFINET configuration.
 */
export function isProfinetConfig(
  config: ProtocolConfig | unknown
): config is { protocol: 'profinet'; config: ProfinetConfig } {
  return (
    typeof config === 'object' &&
    config !== null &&
    'protocol' in config &&
    (config as ProtocolConfig).protocol === 'profinet'
  );
}

/**
 * Type guard for S7 configuration.
 */
export function isS7Config(
  config: ProtocolConfig | unknown
): config is { protocol: 's7comm'; config: S7Config } {
  return (
    typeof config === 'object' &&
    config !== null &&
    'protocol' in config &&
    (config as ProtocolConfig).protocol === 's7comm'
  );
}

/**
 * Type guard for BACnet configuration.
 */
export function isBACnetConfig(
  config: ProtocolConfig | unknown
): config is { protocol: 'bacnet'; config: BACnetConfig } {
  return (
    typeof config === 'object' &&
    config !== null &&
    'protocol' in config &&
    (config as ProtocolConfig).protocol === 'bacnet'
  );
}

/**
 * Type guard for SNMP configuration.
 */
export function isSNMPConfig(
  config: ProtocolConfig | unknown
): config is { protocol: 'snmp'; config: SNMPConfig } {
  return (
    typeof config === 'object' &&
    config !== null &&
    'protocol' in config &&
    (config as ProtocolConfig).protocol === 'snmp'
  );
}

/**
 * Get the default configuration for a protocol.
 */
export function getDefaultConfig(protocol: Protocol): ProtocolConfig {
  switch (protocol) {
    case 'modbus_tcp':
      return {
        protocol: 'modbus_tcp',
        config: { ...DEFAULT_MODBUS_CONFIG },
      };
    case 'ethernet_ip':
      return {
        protocol: 'ethernet_ip',
        config: { ...DEFAULT_ETHERNET_IP_CONFIG },
      };
    case 'profinet':
      return {
        protocol: 'profinet',
        config: { ...DEFAULT_PROFINET_CONFIG },
      };
    case 's7comm':
      return {
        protocol: 's7comm',
        config: { ...DEFAULT_S7_CONFIG },
      };
    case 'bacnet':
      return {
        protocol: 'bacnet',
        config: { ...DEFAULT_BACNET_CONFIG },
      };
    case 'snmp':
      return {
        protocol: 'snmp',
        config: { ...DEFAULT_SNMP_CONFIG },
      };
  }
}

/**
 * Map of protocol names to display labels.
 */
export const PROTOCOL_LABELS: Record<Protocol, string> = {
  modbus_tcp: 'Modbus TCP',
  ethernet_ip: 'EtherNet/IP',
  profinet: 'PROFINET',
  s7comm: 'S7comm',
  bacnet: 'BACnet/IP',
  snmp: 'SNMP',
};

/**
 * Map of protocol names to default ports.
 */
export const PROTOCOL_PORTS: Record<Protocol, number> = {
  modbus_tcp: 502,
  ethernet_ip: 44818,
  profinet: 34964, // UDP for RT
  s7comm: 102,
  bacnet: 47808,
  snmp: 161,
};
