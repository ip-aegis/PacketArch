import { describe, it, expect } from 'vitest';
import {
  isModbusConfig,
  isEtherNetIPConfig,
  isProfinetConfig,
  isS7Config,
  isBACnetConfig,
  isSNMPConfig,
  getDefaultConfig,
  PROTOCOL_LABELS,
  PROTOCOL_PORTS,
} from './index';
import type { Protocol, ProtocolConfig } from './index';
import { DEFAULT_MODBUS_CONFIG } from './modbus';
import { DEFAULT_ETHERNET_IP_CONFIG } from './ethernet-ip';
import { DEFAULT_PROFINET_CONFIG } from './profinet';
import { DEFAULT_S7_CONFIG } from './s7';
import { DEFAULT_BACNET_CONFIG } from './bacnet';
import { DEFAULT_SNMP_CONFIG } from './snmp';

// ---------------------------------------------------------------------------
// Type guard tests
// ---------------------------------------------------------------------------

const modbusConfig: ProtocolConfig = {
  protocol: 'modbus_tcp',
  config: { ...DEFAULT_MODBUS_CONFIG },
};

const ethernetIPConfig: ProtocolConfig = {
  protocol: 'ethernet_ip',
  config: { ...DEFAULT_ETHERNET_IP_CONFIG },
};

const profinetConfig: ProtocolConfig = {
  protocol: 'profinet',
  config: { ...DEFAULT_PROFINET_CONFIG },
};

const s7Config: ProtocolConfig = {
  protocol: 's7',
  config: { ...DEFAULT_S7_CONFIG },
};

const bacnetConfig: ProtocolConfig = {
  protocol: 'bacnet',
  config: { ...DEFAULT_BACNET_CONFIG },
};

const snmpConfig: ProtocolConfig = {
  protocol: 'snmp',
  config: { ...DEFAULT_SNMP_CONFIG },
};

const allConfigs = [
  modbusConfig,
  ethernetIPConfig,
  profinetConfig,
  s7Config,
  bacnetConfig,
  snmpConfig,
];

describe('isModbusConfig', () => {
  it('returns true for modbus config', () => {
    expect(isModbusConfig(modbusConfig)).toBe(true);
  });

  it('returns false for all other protocol configs', () => {
    for (const cfg of allConfigs.filter((c) => c.protocol !== 'modbus_tcp')) {
      expect(isModbusConfig(cfg)).toBe(false);
    }
  });

  it('returns false for null', () => {
    expect(isModbusConfig(null)).toBe(false);
  });

  it('returns false for undefined', () => {
    expect(isModbusConfig(undefined)).toBe(false);
  });

  it('returns false for string', () => {
    expect(isModbusConfig('modbus_tcp')).toBe(false);
  });

  it('returns false for object without protocol field', () => {
    expect(isModbusConfig({ config: {} })).toBe(false);
  });
});

describe('isEtherNetIPConfig', () => {
  it('returns true for ethernet_ip config', () => {
    expect(isEtherNetIPConfig(ethernetIPConfig)).toBe(true);
  });

  it('returns false for all other protocol configs', () => {
    for (const cfg of allConfigs.filter((c) => c.protocol !== 'ethernet_ip')) {
      expect(isEtherNetIPConfig(cfg)).toBe(false);
    }
  });

  it('returns false for null', () => {
    expect(isEtherNetIPConfig(null)).toBe(false);
  });
});

describe('isProfinetConfig', () => {
  it('returns true for profinet config', () => {
    expect(isProfinetConfig(profinetConfig)).toBe(true);
  });

  it('returns false for all other protocol configs', () => {
    for (const cfg of allConfigs.filter((c) => c.protocol !== 'profinet')) {
      expect(isProfinetConfig(cfg)).toBe(false);
    }
  });

  it('returns false for null', () => {
    expect(isProfinetConfig(null)).toBe(false);
  });
});

describe('isS7Config', () => {
  it('returns true for s7 config', () => {
    expect(isS7Config(s7Config)).toBe(true);
  });

  it('returns false for all other protocol configs', () => {
    for (const cfg of allConfigs.filter((c) => c.protocol !== 's7')) {
      expect(isS7Config(cfg)).toBe(false);
    }
  });

  it('returns false for null', () => {
    expect(isS7Config(null)).toBe(false);
  });
});

describe('isBACnetConfig', () => {
  it('returns true for bacnet config', () => {
    expect(isBACnetConfig(bacnetConfig)).toBe(true);
  });

  it('returns false for all other protocol configs', () => {
    for (const cfg of allConfigs.filter((c) => c.protocol !== 'bacnet')) {
      expect(isBACnetConfig(cfg)).toBe(false);
    }
  });

  it('returns false for null', () => {
    expect(isBACnetConfig(null)).toBe(false);
  });
});

describe('isSNMPConfig', () => {
  it('returns true for snmp config', () => {
    expect(isSNMPConfig(snmpConfig)).toBe(true);
  });

  it('returns false for all other protocol configs', () => {
    for (const cfg of allConfigs.filter((c) => c.protocol !== 'snmp')) {
      expect(isSNMPConfig(cfg)).toBe(false);
    }
  });

  it('returns false for null', () => {
    expect(isSNMPConfig(null)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// getDefaultConfig
// ---------------------------------------------------------------------------
describe('getDefaultConfig', () => {
  const protocols: Protocol[] = [
    'modbus_tcp',
    'ethernet_ip',
    'profinet',
    's7',
    'bacnet',
    'snmp',
  ];

  it('returns a config object for every supported protocol', () => {
    for (const proto of protocols) {
      const cfg = getDefaultConfig(proto);
      expect(cfg).toBeDefined();
      expect(cfg.protocol).toBe(proto);
      expect(cfg.config).toBeDefined();
      expect(typeof cfg.config).toBe('object');
    }
  });

  it('returns correct protocol discriminator for modbus', () => {
    const cfg = getDefaultConfig('modbus_tcp');
    expect(cfg.protocol).toBe('modbus_tcp');
    expect(isModbusConfig(cfg)).toBe(true);
  });

  it('returns correct protocol discriminator for ethernet_ip', () => {
    const cfg = getDefaultConfig('ethernet_ip');
    expect(cfg.protocol).toBe('ethernet_ip');
    expect(isEtherNetIPConfig(cfg)).toBe(true);
  });

  it('returns correct protocol discriminator for profinet', () => {
    const cfg = getDefaultConfig('profinet');
    expect(cfg.protocol).toBe('profinet');
    expect(isProfinetConfig(cfg)).toBe(true);
  });

  it('returns correct protocol discriminator for s7', () => {
    const cfg = getDefaultConfig('s7');
    expect(cfg.protocol).toBe('s7');
    expect(isS7Config(cfg)).toBe(true);
  });

  it('returns correct protocol discriminator for bacnet', () => {
    const cfg = getDefaultConfig('bacnet');
    expect(cfg.protocol).toBe('bacnet');
    expect(isBACnetConfig(cfg)).toBe(true);
  });

  it('returns correct protocol discriminator for snmp', () => {
    const cfg = getDefaultConfig('snmp');
    expect(cfg.protocol).toBe('snmp');
    expect(isSNMPConfig(cfg)).toBe(true);
  });

  // Verify default configs contain expected fields
  it('modbus default has unitId and functionCodes', () => {
    const cfg = getDefaultConfig('modbus_tcp');
    if (isModbusConfig(cfg)) {
      expect(cfg.config.unitId).toBe(1);
      expect(cfg.config.functionCodes).toEqual([0x03, 0x04]);
      expect(cfg.config.pollIntervalMs).toBe(1000);
      expect(cfg.config.timeoutMs).toBe(5000);
    }
  });

  it('ethernet_ip default has connectionType', () => {
    const cfg = getDefaultConfig('ethernet_ip');
    if (isEtherNetIPConfig(cfg)) {
      expect(cfg.config.connectionType).toBe('explicit');
      expect(cfg.config.includeListIdentity).toBe(true);
    }
  });

  it('profinet default has stationName and role', () => {
    const cfg = getDefaultConfig('profinet');
    if (isProfinetConfig(cfg)) {
      expect(cfg.config.role).toBe('controller');
      expect(cfg.config.stationName).toBe('plc-station');
      expect(cfg.config.communicationClass).toBe('RT');
    }
  });

  it('s7 default has rack and slot', () => {
    const cfg = getDefaultConfig('s7');
    if (isS7Config(cfg)) {
      expect(cfg.config.rack).toBe(0);
      expect(cfg.config.slot).toBe(1);
      expect(cfg.config.connectionType).toBe('PG');
      expect(cfg.config.mode).toBe('read');
    }
  });

  it('bacnet default has deviceInstance', () => {
    const cfg = getDefaultConfig('bacnet');
    if (isBACnetConfig(cfg)) {
      expect(cfg.config.deviceInstance).toBe(1234);
      expect(cfg.config.includeWhoIs).toBe(true);
    }
  });

  it('snmp default has version and community', () => {
    const cfg = getDefaultConfig('snmp');
    if (isSNMPConfig(cfg)) {
      expect(cfg.config.version).toBe('v2c');
      expect(cfg.config.community).toBe('public');
    }
  });

  // Verify getDefaultConfig returns a copy, not the same reference
  it('returns a new object on each call (not a shared reference)', () => {
    const cfg1 = getDefaultConfig('modbus_tcp');
    const cfg2 = getDefaultConfig('modbus_tcp');
    expect(cfg1).not.toBe(cfg2);
    expect(cfg1.config).not.toBe(cfg2.config);
  });
});

// ---------------------------------------------------------------------------
// PROTOCOL_LABELS
// ---------------------------------------------------------------------------
describe('PROTOCOL_LABELS', () => {
  it('has a label for every protocol', () => {
    const protocols: Protocol[] = [
      'modbus_tcp',
      'ethernet_ip',
      'profinet',
      's7',
      'bacnet',
      'snmp',
    ];
    for (const proto of protocols) {
      expect(PROTOCOL_LABELS[proto]).toBeDefined();
      expect(typeof PROTOCOL_LABELS[proto]).toBe('string');
      expect(PROTOCOL_LABELS[proto].length).toBeGreaterThan(0);
    }
  });

  it('maps to expected display names', () => {
    expect(PROTOCOL_LABELS.modbus_tcp).toBe('Modbus TCP');
    expect(PROTOCOL_LABELS.ethernet_ip).toBe('EtherNet/IP');
    expect(PROTOCOL_LABELS.profinet).toBe('PROFINET');
    expect(PROTOCOL_LABELS.s7).toBe('S7comm');
    expect(PROTOCOL_LABELS.bacnet).toBe('BACnet/IP');
    expect(PROTOCOL_LABELS.snmp).toBe('SNMP');
  });
});

// ---------------------------------------------------------------------------
// PROTOCOL_PORTS
// ---------------------------------------------------------------------------
describe('PROTOCOL_PORTS', () => {
  it('has a port for every protocol', () => {
    const protocols: Protocol[] = [
      'modbus_tcp',
      'ethernet_ip',
      'profinet',
      's7',
      'bacnet',
      'snmp',
    ];
    for (const proto of protocols) {
      expect(PROTOCOL_PORTS[proto]).toBeDefined();
      expect(typeof PROTOCOL_PORTS[proto]).toBe('number');
      expect(PROTOCOL_PORTS[proto]).toBeGreaterThan(0);
    }
  });

  it('maps to expected port numbers', () => {
    expect(PROTOCOL_PORTS.modbus_tcp).toBe(502);
    expect(PROTOCOL_PORTS.ethernet_ip).toBe(44818);
    expect(PROTOCOL_PORTS.s7).toBe(102);
    expect(PROTOCOL_PORTS.bacnet).toBe(47808);
    expect(PROTOCOL_PORTS.snmp).toBe(161);
  });
});
