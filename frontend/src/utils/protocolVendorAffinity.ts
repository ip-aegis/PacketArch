/**
 * Client-side protocol-vendor affinity validation.
 * Mirrors backend rules in protocol_engines/protocols.py:validate_protocol_vendor_affinity()
 */

export function validateProtocolVendorAffinity(
  vendor: string,
  protocols: string[],
): string[] {
  const warnings: string[] = [];
  const v = vendor.toLowerCase();

  if (v.includes('siemens') && protocols.includes('ethernet_ip')) {
    warnings.push(
      'Siemens devices typically use PROFINET/S7comm, not EtherNet/IP.'
    );
  }

  if ((v.includes('rockwell') || v.includes('allen-bradley')) && protocols.includes('profinet')) {
    warnings.push(
      'Rockwell/Allen-Bradley devices typically use EtherNet/IP, not PROFINET.'
    );
  }

  const bmsVendors = ['johnson controls', 'trane', 'carrier', 'tridium'];
  if (bmsVendors.some((b) => v.includes(b))) {
    if (!protocols.includes('bacnet') && !protocols.includes('snmp')) {
      warnings.push(`BMS vendor '${vendor}' typically supports BACnet or SNMP.`);
    }
  }

  const itsVendors = ['econolite', 'wavetronix', 'mccain'];
  if (itsVendors.some((i) => v.includes(i))) {
    if (!protocols.includes('snmp')) {
      warnings.push(`ITS vendor '${vendor}' typically supports SNMP/NTCIP.`);
    }
  }

  return warnings;
}
