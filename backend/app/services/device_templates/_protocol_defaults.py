# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Vendor-aware default supported_protocols computer for templates.

The fingerprint catalog has identity blocks (modbus_identity, ethernet_ip_identity,
profinet_identity, etc.) that are over-populated for many devices — Siemens S7
templates carry a Modbus identity even though S7 PLCs don't natively serve
Modbus. Naively inferring "supports protocol if identity exists" claims
capabilities the device can't deliver.

This module computes a defensible default for `supported_protocols` by
INTERSECTING:
  1. The vendor's known native protocol set (vendor brand → protocols)
  2. The protocols whose identity block is actually populated on the template

Plus an SNMP carve-out: if a template has any vendor name, SNMP is supportable
even without an explicit snmp_identity, because the ambient noise generator
can synthesise an SNMP identity from vendor OUI alone.

Templates that explicitly declare `supported_protocols` always win — this
helper is only used when the template leaves the field empty.
"""

from __future__ import annotations

from typing import Any


# Vendor → native protocol set. Conservative: when uncertain, list a
# protocol; the worst case is leaving it in place. Vendor names are matched
# case-insensitive on the leading brand word ("Siemens AG" → "siemens",
# "Rockwell Automation" → "rockwell").
VENDOR_NATIVE_PROTOCOLS: dict[str, set[str]] = {
    # Industrial control vendors — major brands. Each set is conservative:
    # omitting a protocol means the audit will flag declarations that
    # include it, prompting human review.
    "siemens": {
        "s7", "s7comm", "s7comm_plus",
        "profinet", "profisafe",
        "opc_ua", "snmp", "modbus_tcp", "modbus",
        "iec61850",  # SIPROTEC and other 61850-compliant relays
        "bacnet",    # Desigo BMS line (Desigo CC / DXR2)
        "https",     # web HMIs (Comfort panels, WinCC, S7 web server)
    },
    "rockwell": {
        "ethernet_ip", "enip", "cip_safety", "cip_motion",
        "modbus_tcp", "modbus", "opc_ua", "snmp",
        "https",   # PanelView+ web access, ControlLogix web pages
    },
    "allen-bradley": {
        "ethernet_ip", "enip", "cip_safety", "cip_motion",
        "modbus_tcp", "modbus", "opc_ua", "snmp",
        "https",
    },
    "schneider": {
        "modbus_tcp", "modbus",
        "ethernet_ip", "enip", "opc_ua", "snmp",
        "bacnet",      # PowerLogic / Andover BAS products
        "dnp3",        # PowerLogic substation gear
        "profinet",    # some hybrid devices
        "profisafe",   # PacDrive / safety extensions
        "https",       # Magelis HMIs, M580 web server
    },
    "abb": {
        "modbus_tcp", "modbus", "profinet", "ethernet_ip", "enip",
        "opc_ua", "snmp", "iec104", "dnp3",
        "iec61850",    # Relion protection relays
    },
    "honeywell": {
        "modbus_tcp", "modbus", "opc_ua", "bacnet", "snmp",
        "dnp3",        # Experion / RTU products
    },
    "yokogawa": {"modbus_tcp", "modbus", "opc_ua", "snmp"},
    "emerson": {
        "modbus_tcp", "modbus", "opc_ua", "snmp",
        "dnp3",        # DeltaV with DNP3 gateway
    },
    "ge": {
        "modbus_tcp", "modbus", "opc_ua", "snmp", "dnp3",
        "ethernet_ip", "enip",  # GE-IP Rockwell heritage
        "iec61850",    # Multilin protection relays
    },
    "mitsubishi": {"slmp", "modbus_tcp", "modbus", "snmp"},
    "omron": {"fins", "ethernet_ip", "enip", "modbus_tcp", "modbus", "snmp"},
    "fanuc": {
        "ethernet_ip", "enip", "snmp",
        "modbus_tcp", "modbus",  # FOCAS over Ethernet variants
        "fanuc",                  # FOCAS / FANUC FOCAS protocol
    },
    "kuka": {
        "ethernet_ip", "enip", "profinet", "profisafe", "snmp",
        "modbus_tcp", "modbus",   # KUKA.RoboticEthernet variants
    },
    "sel": {
        "dnp3", "modbus_tcp", "modbus", "snmp",
        "iec61850", "iec104",     # SEL relays support both
    },
    "hms": {
        "modbus_tcp", "modbus", "https", "snmp",
        "ethernet_ip", "enip", "profinet",  # Anybus gateway products
    },
    "endress+hauser": {"modbus_tcp", "modbus", "profinet", "ethernet_ip", "enip", "snmp"},
    "endress": {"modbus_tcp", "modbus", "profinet", "ethernet_ip", "enip", "snmp"},
    "cisco": {
        "snmp", "ethernet_ip", "enip", "profinet", "profisafe",
        "lldp", "cdp",  # Cisco's core network-discovery protocols
        "ssh", "telnet", "https",  # CLI / web management
    },
    "moxa": {"modbus_tcp", "modbus", "snmp", "ethernet_ip", "enip"},
    "phoenix": {
        "modbus_tcp", "modbus", "profinet", "ethernet_ip", "enip", "snmp",
        "opc_ua",  # modern PLCs (PLCnext) speak OPC UA
    },
    "phoenix-contact": {
        "modbus_tcp", "modbus", "profinet", "ethernet_ip", "enip", "snmp",
        "opc_ua",
    },
    "wago": {
        "modbus_tcp", "modbus", "ethernet_ip", "enip", "profinet", "snmp",
        "opc_ua", "codesys",  # WAGO PFC = CODESYS-based controllers
    },
    "beckhoff": {
        "profinet", "ethernet_ip", "enip", "modbus_tcp", "modbus",
        "opc_ua", "snmp",
        "ethercat",   # Beckhoff's flagship protocol
    },
    "b&r": {
        "profinet", "modbus_tcp", "modbus", "opc_ua", "snmp",
        "powerlink",  # B&R's native fieldbus
        "ethercat",
    },
    "advantech": {"modbus_tcp", "modbus", "snmp"},
    "kepware": {
        "modbus_tcp", "modbus", "opc_ua", "snmp",
        "ethernet_ip", "enip", "s7", "s7comm", "s7comm_plus",
        # Kepware ServerEx is a multi-protocol gateway; broad set is correct
    },
    "bosch": {"profinet", "ethernet_ip", "enip", "snmp"},
    # Jump servers / Windows admin hosts — full remote-access stack.
    "microsoft": {
        "snmp", "https", "rdp", "ssh", "telnet",
        # Jump servers also routinely poll OT assets — add the OT
        # protocols they typically tunnel for an admin (read-only).
        "modbus_tcp", "modbus", "opc_ua",
    },
    "vmware": {"snmp", "https"},
    # Robotics / AGV / warehouse — many of these speak Modbus/HTTPS for
    # WCS/WES integration even though their core protocol is proprietary.
    "dematic": {"profinet", "ethernet_ip", "enip", "snmp", "modbus_tcp", "modbus"},
    "mir": {"https", "snmp", "modbus_tcp", "modbus"},
    "impinj": {"snmp", "https", "modbus_tcp", "modbus"},
    "zebra": {"snmp", "https", "modbus_tcp", "modbus"},
    # Building automation / HVAC
    "johnson": {"bacnet", "modbus_tcp", "modbus", "snmp"},
    "delta": {"bacnet", "modbus_tcp", "modbus", "snmp"},
    "automated": {"bacnet", "modbus_tcp", "modbus", "snmp"},
    "trane": {"bacnet", "modbus_tcp", "modbus", "snmp"},
    "carrier": {"bacnet", "modbus_tcp", "modbus", "snmp"},
    "distech": {"bacnet", "modbus_tcp", "modbus", "snmp"},
    "carel": {"bacnet", "modbus_tcp", "modbus", "snmp"},
    "notifier": {"bacnet", "snmp"},
    "lutron": {"bacnet", "snmp"},
    # Transportation / ITS
    "econolite": {"snmp", "ntcip", "modbus_tcp", "modbus"},
    "siemens its": {"snmp", "ntcip", "modbus_tcp", "modbus"},
    "mccain": {"snmp", "ntcip"},
    "daktronics": {"snmp", "ntcip"},
    "wavetronix": {"snmp", "ntcip"},
    "q-free": {"snmp", "ntcip"},
    "kapsch": {"snmp", "ntcip"},
    # Cameras / sensors
    "flir": {"snmp", "https", "rtsp"},
    "axis": {"snmp", "https", "rtsp", "onvif"},
    "pelco": {"snmp", "https", "rtsp", "onvif"},
    "hikvision": {"snmp", "https", "rtsp", "onvif"},
    "sick": {"profinet", "ethernet_ip", "enip", "modbus_tcp", "modbus", "snmp"},
    "cognex": {"ethernet_ip", "enip", "modbus_tcp", "modbus", "snmp"},
    "vaisala": {"modbus_tcp", "modbus", "snmp"},
    # (impinj / zebra / dematic / mir defined above with broader sets)
}


# Each protocol → the identity field on a DeviceTemplate that confirms it
# can be served. When the identity is None/empty, the template can't
# generate that protocol's traffic — exclude it from supported_protocols
# regardless of the vendor's typical capabilities.
PROTOCOL_TO_TEMPLATE_IDENTITY: dict[str, str] = {
    "s7": "s7_identity",
    "s7comm": "s7_identity",
    "s7comm_plus": "s7_identity",
    "profinet": "profinet_identity",
    "profisafe": "profinet_identity",
    "ethernet_ip": "ethernet_ip_identity",
    "enip": "ethernet_ip_identity",
    "cip_safety": "ethernet_ip_identity",
    "modbus": "modbus_identity",
    "modbus_tcp": "modbus_identity",
    "opc_ua": "opc_ua_identity",
    "snmp": "snmp_identity",
    "bacnet": "bacnet_identity",
    "dnp3": "dnp3_identity",
    "iec104": "iec104_identity",
}


def vendor_brand(vendor: str | None) -> str:
    """Strip suffixes ('AG', 'Inc.', 'Automation', 'Group', etc.) and
    lowercase to match the keys in VENDOR_NATIVE_PROTOCOLS."""
    if not vendor:
        return ""
    first = vendor.strip().lower().split()[0]
    return first.rstrip(".,;:")


def compute_default_supported_protocols(template: Any) -> list[str]:
    """Compute supported_protocols for a template that doesn't declare it.

    Algorithm:
      1. Look up vendor-native set by stripped vendor brand.
      2. For each native protocol, check that the template has the
         corresponding identity block populated.
      3. Carve-out: SNMP survives if any vendor name is present (noise
         generator synthesises SNMP identity from vendor OUI alone).

    Vendors not in the whitelist fall back to "any protocol whose identity
    block is populated" — same behavior as the legacy inference, since we
    have no domain knowledge to filter by.
    """
    vendor_str = getattr(template, "vendor", "") or ""
    brand = vendor_brand(vendor_str)
    natives = VENDOR_NATIVE_PROTOCOLS.get(brand)

    out: set[str] = set()
    if natives is None:
        # Unknown vendor → permissive fallback.
        for proto, ikey in PROTOCOL_TO_TEMPLATE_IDENTITY.items():
            if getattr(template, ikey, None):
                out.add(proto)
        return sorted(out)

    for proto in natives:
        ikey = PROTOCOL_TO_TEMPLATE_IDENTITY.get(proto)
        if ikey is None:
            # Protocols with no identity requirement (raw TCP probes,
            # ntcip, https, rtsp, etc.) — trust the vendor mapping.
            out.add(proto)
            continue
        if getattr(template, ikey, None):
            out.add(proto)
        elif proto == "snmp" and vendor_str:
            # SNMP synthesisable from vendor OUI; survives without
            # explicit snmp_identity.
            out.add(proto)
    return sorted(out)


def compute_default_supported_protocols_from_db(template: Any) -> list[str]:
    """Same as compute_default_supported_protocols but for the DB
    DeviceTemplate model where identity blocks live as columns and
    `active_protocols` may already be populated.
    """
    vendor_str = getattr(template, "vendor", "") or ""
    brand = vendor_brand(vendor_str)
    natives = VENDOR_NATIVE_PROTOCOLS.get(brand)

    out: set[str] = set()
    if natives is None:
        for proto, ikey in PROTOCOL_TO_TEMPLATE_IDENTITY.items():
            if getattr(template, ikey, None):
                out.add(proto)
        return sorted(out)

    for proto in natives:
        ikey = PROTOCOL_TO_TEMPLATE_IDENTITY.get(proto)
        if ikey is None:
            out.add(proto)
            continue
        if getattr(template, ikey, None):
            out.add(proto)
        elif proto == "snmp" and vendor_str:
            out.add(proto)
    return sorted(out)
