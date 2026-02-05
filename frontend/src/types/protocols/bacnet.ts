/**
 * BACnet/IP protocol configuration types.
 *
 * BACnet (Building Automation and Control Networks) is a communication
 * protocol for building automation and control systems.
 */

/**
 * BACnet object types.
 */
export type BACnetObjectType =
  | 'analog-input'
  | 'analog-output'
  | 'analog-value'
  | 'binary-input'
  | 'binary-output'
  | 'binary-value'
  | 'calendar'
  | 'command'
  | 'device'
  | 'event-enrollment'
  | 'file'
  | 'group'
  | 'loop'
  | 'multi-state-input'
  | 'multi-state-output'
  | 'notification-class'
  | 'program'
  | 'schedule'
  | 'trend-log';

/**
 * BACnet services.
 */
export type BACnetService =
  | 'read-property'
  | 'read-property-multiple'
  | 'write-property'
  | 'write-property-multiple'
  | 'subscribe-cov'
  | 'i-am'
  | 'who-is'
  | 'who-has'
  | 'i-have';

/**
 * BACnet object reference.
 */
export interface BACnetObjectRef {
  /** Object type */
  objectType: BACnetObjectType;
  /** Object instance number */
  instanceNumber: number;
}

/**
 * BACnet property reference.
 */
export interface BACnetPropertyRef {
  /** Object reference */
  object: BACnetObjectRef;
  /** Property identifier */
  propertyId: string;
  /** Array index (optional) */
  arrayIndex?: number;
}

/**
 * BACnet/IP flow configuration.
 */
export interface BACnetConfig {
  /** Local device instance number */
  deviceInstance: number;

  /** Services to use */
  services: BACnetService[];

  /** Objects to poll */
  objects: BACnetObjectRef[];

  /** Properties to read */
  properties?: BACnetPropertyRef[];

  /** Poll interval (ms) */
  pollIntervalMs: number;

  /** Include Who-Is broadcasts */
  includeWhoIs?: boolean;

  /** Who-Is device range (min, max) */
  whoIsRange?: {
    min: number;
    max: number;
  };

  /** Enable COV (Change of Value) subscriptions */
  enableCov?: boolean;

  /** COV lifetime (seconds) */
  covLifetime?: number;

  /** APDU timeout (ms) */
  apduTimeout?: number;

  /** APDU retries */
  apduRetries?: number;
}

/**
 * Default BACnet configuration for quick setup.
 */
export const DEFAULT_BACNET_CONFIG: BACnetConfig = {
  deviceInstance: 1234,
  services: ['read-property', 'who-is', 'i-am'],
  objects: [
    { objectType: 'device', instanceNumber: 1234 },
    { objectType: 'analog-input', instanceNumber: 1 },
  ],
  pollIntervalMs: 5000,
  includeWhoIs: true,
  enableCov: false,
  apduTimeout: 6000,
  apduRetries: 3,
};
