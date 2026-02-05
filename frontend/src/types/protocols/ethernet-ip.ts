/**
 * EtherNet/IP protocol configuration types.
 *
 * EtherNet/IP (Ethernet Industrial Protocol) is an industrial network protocol
 * that adapts the Common Industrial Protocol (CIP) to standard Ethernet.
 */

/**
 * CIP service codes for EtherNet/IP operations.
 */
export type CIPServiceCode =
  | 0x01 // Get_Attribute_All
  | 0x02 // Set_Attribute_All
  | 0x03 // Get_Attribute_List
  | 0x04 // Set_Attribute_List
  | 0x05 // Reset
  | 0x06 // Start
  | 0x07 // Stop
  | 0x08 // Create
  | 0x09 // Delete
  | 0x0a // Multiple_Service_Packet
  | 0x0d // Apply_Attributes
  | 0x0e // Get_Attribute_Single
  | 0x10 // Set_Attribute_Single
  | 0x4c // Read_Tag
  | 0x4d // Read_Tag_Fragmented
  | 0x4e // Write_Tag
  | 0x4f // Write_Tag_Fragmented
  | 0x52; // Read_Modify_Write_Tag

/**
 * CIP path segment for addressing objects.
 */
export interface CIPPath {
  /** Class ID */
  classId: number;
  /** Instance ID */
  instanceId: number;
  /** Attribute ID (optional) */
  attributeId?: number;
}

/**
 * Tag definition for symbolic addressing.
 */
export interface EtherNetIPTag {
  /** Tag name (symbolic address) */
  name: string;
  /** Data type (DINT, REAL, BOOL, etc.) */
  dataType: string;
  /** Array dimensions (empty for scalar) */
  dimensions?: number[];
  /** Description */
  description?: string;
}

/**
 * EtherNet/IP flow configuration.
 */
export interface EtherNetIPConfig {
  /** Connection type: explicit (connected) or implicit (I/O) */
  connectionType: 'explicit' | 'implicit';

  /** CIP service codes to use */
  serviceCodes: CIPServiceCode[];

  /** Target CIP paths for messaging */
  targetPaths: CIPPath[];

  /** Tags for symbolic addressing (ControlLogix/CompactLogix) */
  tags?: EtherNetIPTag[];

  /** Request Packet Interval for I/O connections (ms) */
  rpi?: number;

  /** Connection timeout multiplier */
  timeoutMultiplier?: number;

  /** O->T (originator to target) connection parameters */
  oToTParams?: {
    size: number;
    priority: 'low' | 'high' | 'scheduled' | 'urgent';
    connectionType: 'null' | 'multicast' | 'point_to_point';
  };

  /** T->O (target to originator) connection parameters */
  tToOParams?: {
    size: number;
    priority: 'low' | 'high' | 'scheduled' | 'urgent';
    connectionType: 'null' | 'multicast' | 'point_to_point';
  };

  /** Include ListIdentity requests for device discovery */
  includeListIdentity?: boolean;

  /** Poll interval for explicit messages (ms) */
  pollIntervalMs: number;
}

/**
 * Default EtherNet/IP configuration for quick setup.
 */
export const DEFAULT_ETHERNET_IP_CONFIG: EtherNetIPConfig = {
  connectionType: 'explicit',
  serviceCodes: [0x0e, 0x01], // Get_Attribute_Single, Get_Attribute_All
  targetPaths: [
    { classId: 0x01, instanceId: 1 }, // Identity Object
  ],
  pollIntervalMs: 1000,
  includeListIdentity: true,
};
