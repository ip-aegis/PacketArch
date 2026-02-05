/**
 * SNMP/NTCIP protocol configuration types.
 *
 * SNMP (Simple Network Management Protocol) is used for network management,
 * and NTCIP extends it for transportation systems.
 */

/**
 * SNMP version.
 */
export type SNMPVersion = 'v1' | 'v2c' | 'v3';

/**
 * SNMP PDU types.
 */
export type SNMPPDUType =
  | 'get'
  | 'get-next'
  | 'get-bulk'
  | 'set'
  | 'trap'
  | 'inform';

/**
 * SNMPv3 authentication protocol.
 */
export type SNMPv3AuthProtocol = 'MD5' | 'SHA' | 'SHA-256' | 'SHA-512';

/**
 * SNMPv3 privacy protocol.
 */
export type SNMPv3PrivProtocol = 'DES' | 'AES' | 'AES-256';

/**
 * SNMPv3 security level.
 */
export type SNMPv3SecurityLevel =
  | 'noAuthNoPriv'
  | 'authNoPriv'
  | 'authPriv';

/**
 * OID (Object Identifier) definition.
 */
export interface SNMPOid {
  /** OID string (e.g., "1.3.6.1.2.1.1.1") */
  oid: string;
  /** Human-readable name */
  name?: string;
  /** Description */
  description?: string;
}

/**
 * SNMPv3 user security model configuration.
 */
export interface SNMPv3USM {
  /** Security level */
  securityLevel: SNMPv3SecurityLevel;
  /** Username */
  username: string;
  /** Authentication protocol */
  authProtocol?: SNMPv3AuthProtocol;
  /** Authentication password (not stored in scenarios) */
  authPassword?: string;
  /** Privacy protocol */
  privProtocol?: SNMPv3PrivProtocol;
  /** Privacy password (not stored in scenarios) */
  privPassword?: string;
  /** Engine ID */
  engineId?: string;
}

/**
 * SNMP flow configuration.
 */
export interface SNMPConfig {
  /** SNMP version */
  version: SNMPVersion;

  /** Community string (v1/v2c) */
  community?: string;

  /** SNMPv3 USM configuration */
  v3Config?: SNMPv3USM;

  /** PDU types to use */
  pduTypes: SNMPPDUType[];

  /** OIDs to poll */
  oids: SNMPOid[];

  /** Poll interval (ms) */
  pollIntervalMs: number;

  /** Use get-bulk for efficiency (v2c/v3) */
  useGetBulk?: boolean;

  /** Max repetitions for get-bulk */
  maxRepetitions?: number;

  /** Non-repeaters for get-bulk */
  nonRepeaters?: number;

  /** Include system MIB (sysDescr, sysObjectID, etc.) */
  includeSystemMib?: boolean;

  /** NTCIP-specific OIDs for transportation */
  ntcipMode?: boolean;
}

/**
 * Common SNMP OIDs.
 */
export const COMMON_SNMP_OIDS: SNMPOid[] = [
  { oid: '1.3.6.1.2.1.1.1', name: 'sysDescr', description: 'System Description' },
  { oid: '1.3.6.1.2.1.1.2', name: 'sysObjectID', description: 'System Object ID' },
  { oid: '1.3.6.1.2.1.1.3', name: 'sysUpTime', description: 'System Uptime' },
  { oid: '1.3.6.1.2.1.1.4', name: 'sysContact', description: 'System Contact' },
  { oid: '1.3.6.1.2.1.1.5', name: 'sysName', description: 'System Name' },
  { oid: '1.3.6.1.2.1.1.6', name: 'sysLocation', description: 'System Location' },
];

/**
 * Default SNMP configuration for quick setup.
 */
export const DEFAULT_SNMP_CONFIG: SNMPConfig = {
  version: 'v2c',
  community: 'public',
  pduTypes: ['get', 'get-next'],
  oids: COMMON_SNMP_OIDS.slice(0, 3),
  pollIntervalMs: 10000,
  useGetBulk: true,
  maxRepetitions: 10,
  includeSystemMib: true,
  ntcipMode: false,
};
