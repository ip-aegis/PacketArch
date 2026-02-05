/**
 * S7comm protocol configuration types.
 *
 * S7comm is the proprietary protocol used by Siemens PLCs (S7-300/400/1200/1500).
 */

/**
 * S7 memory area types.
 */
export type S7MemoryArea =
  | 'DB' // Data Block
  | 'I' // Inputs
  | 'Q' // Outputs
  | 'M' // Memory/Markers
  | 'T' // Timers
  | 'C'; // Counters

/**
 * S7 data types for variable addressing.
 */
export type S7DataType =
  | 'BOOL'
  | 'BYTE'
  | 'WORD'
  | 'DWORD'
  | 'INT'
  | 'DINT'
  | 'REAL'
  | 'CHAR'
  | 'STRING';

/**
 * S7 variable definition.
 */
export interface S7Variable {
  /** Memory area (DB, I, Q, M, etc.) */
  area: S7MemoryArea;
  /** Data block number (for DB area) */
  dbNumber?: number;
  /** Start byte offset */
  startByte: number;
  /** Bit offset within byte (for BOOL) */
  bitOffset?: number;
  /** Data type */
  dataType: S7DataType;
  /** Number of elements (for arrays) */
  count?: number;
  /** Description */
  description?: string;
}

/**
 * S7 PDU configuration.
 */
export interface S7PDUConfig {
  /** Maximum PDU size (240-960 bytes) */
  maxPduSize: number;
  /** Maximum number of variables per request */
  maxAmqCalling: number;
  /** Maximum number of variables per response */
  maxAmqCalled: number;
}

/**
 * S7comm flow configuration.
 */
export interface S7Config {
  /** Rack number (0-7) */
  rack: number;

  /** Slot number (0-31) */
  slot: number;

  /** Connection type (PG, OP, or S7Basic) */
  connectionType: 'PG' | 'OP' | 'S7Basic';

  /** Variables to read/write */
  variables: S7Variable[];

  /** PDU configuration */
  pduConfig?: S7PDUConfig;

  /** Poll interval (ms) */
  pollIntervalMs: number;

  /** Include SZL (System Status List) requests for device info */
  includeSzl?: boolean;

  /** SZL IDs to request */
  szlIds?: number[];

  /** Read/Write mode */
  mode: 'read' | 'write' | 'both';
}

/**
 * Default S7 configuration for quick setup.
 */
export const DEFAULT_S7_CONFIG: S7Config = {
  rack: 0,
  slot: 1,
  connectionType: 'PG',
  variables: [
    { area: 'DB', dbNumber: 1, startByte: 0, dataType: 'DINT' },
    { area: 'M', startByte: 0, dataType: 'BYTE', count: 10 },
  ],
  pduConfig: {
    maxPduSize: 480,
    maxAmqCalling: 1,
    maxAmqCalled: 1,
  },
  pollIntervalMs: 1000,
  includeSzl: true,
  mode: 'read',
};
