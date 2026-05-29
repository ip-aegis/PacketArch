#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""
Validate fingerprint packets from captured PCAP.
Parses protocol-specific fields and compares against expected values.

Usage:
    cd /home/rocsmith/PacketArch/backend
    poetry run python scripts/validate_fingerprint_packets.py --pcap /tmp/fingerprint_test.pcap

Prerequisites:
    - PCAP file captured from traffic generator
    - /tmp/expected_fingerprints.json from create_fingerprint_test_scenario.py
"""

import argparse
import json
import struct
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from scapy.all import rdpcap, Ether, IP, UDP, TCP, Raw
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    print("Warning: scapy not available, using basic parsing")


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    device_ip: str
    protocol: str
    field_name: str
    expected: Any
    found: Any
    passed: bool
    details: str = ""


@dataclass
class ProtocolFindings:
    """Collected findings for a device/protocol combination."""
    device_ip: str
    protocol: str
    values: dict = field(default_factory=dict)
    packet_count: int = 0


class FingerprintValidator:
    """Validates fingerprint data in captured packets."""

    def __init__(self, pcap_path: str, expected_path: str):
        self.pcap_path = pcap_path
        self.expected_path = expected_path
        self.results: list[ValidationResult] = []
        self.findings: dict[str, dict[str, ProtocolFindings]] = defaultdict(dict)

        # Load expected values
        with open(expected_path) as f:
            self.expected = json.load(f)

        print(f"Loaded expected values for {len(self.expected)} devices")

    def load_packets(self):
        """Load packets from PCAP file."""
        if not SCAPY_AVAILABLE:
            print("ERROR: scapy is required for packet parsing")
            print("Install with: pip install scapy")
            sys.exit(1)

        print(f"Loading PCAP: {self.pcap_path}")
        self.packets = rdpcap(self.pcap_path)
        print(f"Loaded {len(self.packets)} packets")

    def validate_all(self):
        """Run all protocol validations."""
        self.load_packets()

        print("\nParsing packets...")
        self.parse_snmp_packets()
        self.parse_modbus_packets()
        self.parse_ethernet_ip_packets()
        self.parse_profinet_dcp_packets()
        self.parse_s7_packets()
        self.parse_bacnet_packets()

        print("\nValidating against expected values...")
        self.compare_findings()

        return self.results

    def parse_snmp_packets(self):
        """Parse SNMP GetResponse packets and extract sysDescr/sysObjectID."""
        snmp_count = 0

        for pkt in self.packets:
            try:
                if UDP not in pkt:
                    continue

                # SNMP agent responses come from port 161
                if pkt[UDP].sport != 161:
                    continue

                if Raw not in pkt:
                    continue

                payload = bytes(pkt[Raw].load)
                src_ip = pkt[IP].src

                # Parse SNMP BER-TLV structure
                # Sequence tag = 0x30
                if len(payload) < 10 or payload[0] != 0x30:
                    continue

                snmp_count += 1

                # Try to extract sysDescr from the response
                # Look for OID 1.3.6.1.2.1.1.1.0 (sysDescr)
                sys_descr = self._extract_snmp_string(payload, b"\x06\x08\x2b\x06\x01\x02\x01\x01\x01\x00")

                # Look for OID 1.3.6.1.2.1.1.2.0 (sysObjectID)
                sys_object_id = self._extract_snmp_oid(payload, b"\x06\x08\x2b\x06\x01\x02\x01\x01\x02\x00")

                # Look for OID 1.3.6.1.2.1.1.5.0 (sysName)
                sys_name = self._extract_snmp_string(payload, b"\x06\x08\x2b\x06\x01\x02\x01\x01\x05\x00")

                if src_ip not in self.findings:
                    self.findings[src_ip] = {}
                if "snmp" not in self.findings[src_ip]:
                    self.findings[src_ip]["snmp"] = ProtocolFindings(src_ip, "snmp")

                finding = self.findings[src_ip]["snmp"]
                finding.packet_count += 1

                if sys_descr:
                    finding.values["sys_descr"] = sys_descr
                if sys_object_id:
                    finding.values["sys_object_id"] = sys_object_id
                if sys_name:
                    finding.values["sys_name"] = sys_name

            except Exception:
                continue

        print(f"  SNMP: Found {snmp_count} response packets")

    def _extract_snmp_string(self, payload: bytes, oid_bytes: bytes) -> str | None:
        """Extract string value following an OID in SNMP payload."""
        try:
            idx = payload.find(oid_bytes)
            if idx < 0:
                return None

            # Skip past the OID
            pos = idx + len(oid_bytes)
            if pos >= len(payload):
                return None

            # Next should be the value - OCTET STRING (0x04) or other
            if payload[pos] == 0x04:  # OCTET STRING
                pos += 1
                length = payload[pos]
                if length & 0x80:  # Long form length
                    num_octets = length & 0x7F
                    length = int.from_bytes(payload[pos+1:pos+1+num_octets], 'big')
                    pos += 1 + num_octets
                else:
                    pos += 1
                return payload[pos:pos+length].decode('utf-8', errors='replace')
        except Exception:
            pass
        return None

    def _extract_snmp_oid(self, payload: bytes, oid_prefix: bytes) -> str | None:
        """Extract OID value following an OID prefix in SNMP payload."""
        try:
            idx = payload.find(oid_prefix)
            if idx < 0:
                return None

            pos = idx + len(oid_prefix)
            if pos >= len(payload):
                return None

            # Next should be OID value (0x06)
            if payload[pos] == 0x06:
                pos += 1
                length = payload[pos]
                pos += 1
                oid_bytes = payload[pos:pos+length]
                return self._decode_oid(oid_bytes)
        except Exception:
            pass
        return None

    def _decode_oid(self, oid_bytes: bytes) -> str:
        """Decode BER-encoded OID bytes to string."""
        if not oid_bytes:
            return ""
        components = [str(oid_bytes[0] // 40), str(oid_bytes[0] % 40)]
        value = 0
        for b in oid_bytes[1:]:
            value = (value << 7) | (b & 0x7F)
            if not (b & 0x80):
                components.append(str(value))
                value = 0
        return ".".join(components)

    def parse_modbus_packets(self):
        """Parse Modbus FC43 responses and extract MajorMinorRevision."""
        modbus_count = 0

        for pkt in self.packets:
            try:
                if TCP not in pkt or Raw not in pkt:
                    continue

                # Modbus server responses come from port 502
                if pkt[TCP].sport != 502:
                    continue

                payload = bytes(pkt[Raw].load)
                src_ip = pkt[IP].src

                # MBAP header is 7 bytes, then function code
                if len(payload) < 8:
                    continue

                # Check for FC43 (0x2B) - Read Device Identification
                function_code = payload[7]
                if function_code != 0x2B:
                    continue

                modbus_count += 1

                # Parse MEI response
                # Offset 8: MEI type (should be 0x0E)
                # Offset 9: Device ID code
                # Offset 10: Conformity level
                # Offset 11: More follows
                # Offset 12: Next object ID
                # Offset 13: Number of objects
                # Offset 14+: Objects (ID, length, value)

                if len(payload) < 14:
                    continue

                mei_type = payload[8]
                if mei_type != 0x0E:
                    continue

                num_objects = payload[13]
                pos = 14

                values = {}
                for _ in range(num_objects):
                    if pos + 2 > len(payload):
                        break
                    obj_id = payload[pos]
                    obj_len = payload[pos + 1]
                    if pos + 2 + obj_len > len(payload):
                        break
                    obj_val = payload[pos + 2:pos + 2 + obj_len].decode('utf-8', errors='replace')
                    values[obj_id] = obj_val
                    pos += 2 + obj_len

                if src_ip not in self.findings:
                    self.findings[src_ip] = {}
                if "modbus" not in self.findings[src_ip]:
                    self.findings[src_ip]["modbus"] = ProtocolFindings(src_ip, "modbus")

                finding = self.findings[src_ip]["modbus"]
                finding.packet_count += 1

                # Object IDs: 0x00=VendorName, 0x01=ProductCode, 0x02=MajorMinorRevision
                if 0x00 in values:
                    finding.values["vendor_name"] = values[0x00]
                if 0x01 in values:
                    finding.values["product_code"] = values[0x01]
                if 0x02 in values:
                    finding.values["major_minor_revision"] = values[0x02]

            except Exception:
                continue

        print(f"  Modbus FC43: Found {modbus_count} response packets")

    def parse_ethernet_ip_packets(self):
        """Parse EtherNet/IP ListIdentity responses."""
        enip_count = 0

        for pkt in self.packets:
            try:
                if TCP not in pkt or Raw not in pkt:
                    continue

                # EtherNet/IP can be on TCP 44818 or UDP 44818
                if pkt[TCP].sport != 44818 and pkt[TCP].dport != 44818:
                    continue

                payload = bytes(pkt[Raw].load)
                src_ip = pkt[IP].src

                # Encapsulation header: command (2 bytes), length (2 bytes), session (4 bytes), etc.
                if len(payload) < 24:
                    continue

                command = struct.unpack("<H", payload[0:2])[0]

                # ListIdentity response = 0x0063
                if command != 0x0063:
                    continue

                enip_count += 1

                # Find the identity data in CPF items
                # Skip encapsulation header (24 bytes)
                # Item count (2 bytes), then items
                pos = 24
                if pos + 2 > len(payload):
                    continue

                item_count = struct.unpack("<H", payload[pos:pos+2])[0]
                pos += 2

                for _ in range(item_count):
                    if pos + 4 > len(payload):
                        break
                    item_type = struct.unpack("<H", payload[pos:pos+2])[0]
                    item_length = struct.unpack("<H", payload[pos+2:pos+4])[0]
                    pos += 4

                    # Type 0x000C is ListIdentity
                    if item_type == 0x000C:
                        # Parse identity data
                        # Skip: encap_version(2), socket_family(2), port(2), ip(4), zeros(8)
                        # Then: vendor_id(2), device_type(2), product_code(2), revision(2)
                        id_pos = pos + 18  # Skip socket info
                        if id_pos + 8 <= pos + item_length:
                            vendor_id = struct.unpack("<H", payload[id_pos:id_pos+2])[0]
                            device_type = struct.unpack("<H", payload[id_pos+2:id_pos+4])[0]
                            product_code = struct.unpack("<H", payload[id_pos+4:id_pos+6])[0]
                            revision_major = payload[id_pos+6]
                            revision_minor = payload[id_pos+7]

                            if src_ip not in self.findings:
                                self.findings[src_ip] = {}
                            if "ethernet_ip" not in self.findings[src_ip]:
                                self.findings[src_ip]["ethernet_ip"] = ProtocolFindings(src_ip, "ethernet_ip")

                            finding = self.findings[src_ip]["ethernet_ip"]
                            finding.packet_count += 1
                            finding.values["vendor_id"] = vendor_id
                            finding.values["device_type"] = device_type
                            finding.values["product_code"] = product_code
                            finding.values["revision_major"] = revision_major
                            finding.values["revision_minor"] = revision_minor

                    pos += item_length

            except Exception:
                continue

        print(f"  EtherNet/IP: Found {enip_count} ListIdentity responses")

    def parse_profinet_dcp_packets(self):
        """Parse PROFINET DCP Identify Response packets."""
        profinet_count = 0

        for pkt in self.packets:
            try:
                if Ether not in pkt:
                    continue

                # PROFINET EtherType = 0x8892
                if pkt[Ether].type != 0x8892:
                    continue

                if Raw not in pkt:
                    continue

                payload = bytes(pkt[Raw].load)
                src_mac = pkt[Ether].src

                # DCP header: FrameID (2 bytes), ServiceID, ServiceType, XID (4), etc.
                if len(payload) < 10:
                    continue

                frame_id = struct.unpack(">H", payload[0:2])[0]
                service_id = payload[2]
                service_type = payload[3]

                # FrameID 0xFEFF = DCP Identify Response, or 0xFEFE = DCP Get/Set
                # ServiceID 0x05 = Identify, ServiceType 0x01 = Success Response
                if frame_id not in (0xFEFF, 0xFEFE):
                    continue
                if service_id != 0x05 or service_type != 0x01:
                    continue

                profinet_count += 1

                # Parse DCP blocks starting at offset 10
                # XID (4), Response Delay (2), Data Length (2)
                data_length = struct.unpack(">H", payload[8:10])[0]
                pos = 10

                values = {}
                while pos + 4 <= len(payload) and pos < 10 + data_length:
                    option = payload[pos]
                    suboption = payload[pos + 1]
                    block_length = struct.unpack(">H", payload[pos+2:pos+4])[0]
                    pos += 4

                    if pos + block_length > len(payload):
                        break

                    block_data = payload[pos:pos+block_length]

                    # Option 0x02, Suboption 0x08 = OEM Device ID (contains SW version)
                    if option == 0x02 and suboption == 0x08:
                        try:
                            oem_string = block_data.decode('ascii', errors='replace')
                            values["oem_device_id"] = oem_string
                            # Parse "SW:Vx.x.x" from OEM string
                            if "SW:" in oem_string:
                                sw_part = oem_string.split("SW:")[1].split(";")[0].strip()
                                values["sw_release"] = sw_part
                        except Exception:
                            pass

                    # Option 0x02, Suboption 0x02 = Device Name
                    if option == 0x02 and suboption == 0x02:
                        try:
                            values["device_name"] = block_data.decode('ascii', errors='replace')
                        except Exception:
                            pass

                    # Option 0x02, Suboption 0x03 = Device ID (Vendor + Device)
                    if option == 0x02 and suboption == 0x03:
                        if len(block_data) >= 4:
                            vendor_id = struct.unpack(">H", block_data[0:2])[0]
                            device_id = struct.unpack(">H", block_data[2:4])[0]
                            values["vendor_id"] = vendor_id
                            values["device_id"] = device_id

                    pos += block_length
                    # Pad to even
                    if block_length % 2:
                        pos += 1

                # Use source MAC as key since DCP is Layer 2
                mac_key = f"mac:{src_mac}"
                if mac_key not in self.findings:
                    self.findings[mac_key] = {}
                if "profinet" not in self.findings[mac_key]:
                    self.findings[mac_key]["profinet"] = ProtocolFindings(mac_key, "profinet")

                finding = self.findings[mac_key]["profinet"]
                finding.packet_count += 1
                finding.values.update(values)

            except Exception:
                continue

        print(f"  PROFINET DCP: Found {profinet_count} Identify Response packets")

    def parse_s7_packets(self):
        """Parse S7comm SZL 0x0011 responses."""
        s7_count = 0

        for pkt in self.packets:
            try:
                if TCP not in pkt or Raw not in pkt:
                    continue

                # S7comm uses port 102
                if pkt[TCP].sport != 102 and pkt[TCP].dport != 102:
                    continue

                payload = bytes(pkt[Raw].load)
                src_ip = pkt[IP].src

                # TPKT header (4 bytes): version, reserved, length
                if len(payload) < 4:
                    continue
                if payload[0] != 0x03:  # TPKT version
                    continue

                struct.unpack(">H", payload[2:4])[0]

                # COTP header starts at offset 4
                cotp_length = payload[4]
                cotp_pdu_type = payload[5]

                # PDU type 0x0F = Data (DT)
                if cotp_pdu_type != 0x0F:
                    continue

                # S7comm starts after COTP header
                s7_pos = 4 + 1 + cotp_length
                if s7_pos + 10 > len(payload):
                    continue

                # S7 header
                s7_protocol_id = payload[s7_pos]
                if s7_protocol_id != 0x32:  # S7comm protocol ID
                    continue

                s7_msg_type = payload[s7_pos + 1]
                # Message type 0x07 = Userdata (for SZL)
                if s7_msg_type != 0x07:
                    continue

                s7_count += 1

                # Parse Userdata response to find SZL data
                # This is complex - look for SZL ID 0x0011
                szl_id_bytes = b"\x00\x11\x00\x00"  # SZL ID 0x0011, Index 0x0000
                szl_idx = payload.find(szl_id_bytes, s7_pos)

                if szl_idx < 0:
                    continue

                # SZL data follows: szl_id(2), index(2), data_length(2), element_count(2)
                # Then the actual SZL record
                data_pos = szl_idx + 8  # Skip header

                if data_pos + 64 > len(payload):
                    continue

                # SZL 0x0011 record structure (64 bytes):
                # Order code: 20 bytes (offset 0)
                # Serial number: 12 bytes (offset 20)
                # Firmware version: 8 bytes (offset 32)
                # Module type: 24 bytes (offset 40)

                order_code = payload[data_pos:data_pos+20].decode('ascii', errors='replace').strip('\x00')
                serial_number = payload[data_pos+20:data_pos+32].decode('ascii', errors='replace').strip('\x00')
                firmware_version = payload[data_pos+32:data_pos+40].decode('ascii', errors='replace').strip('\x00')
                module_type = payload[data_pos+40:data_pos+64].decode('ascii', errors='replace').strip('\x00')

                if src_ip not in self.findings:
                    self.findings[src_ip] = {}
                if "s7comm" not in self.findings[src_ip]:
                    self.findings[src_ip]["s7comm"] = ProtocolFindings(src_ip, "s7comm")

                finding = self.findings[src_ip]["s7comm"]
                finding.packet_count += 1
                finding.values["order_code"] = order_code
                finding.values["serial_number"] = serial_number
                finding.values["firmware_version"] = firmware_version
                finding.values["module_type"] = module_type

            except Exception:
                continue

        print(f"  S7comm SZL: Found {s7_count} Userdata response packets")

    def parse_bacnet_packets(self):
        """Parse BACnet I-Am and ReadProperty responses."""
        bacnet_count = 0

        for pkt in self.packets:
            try:
                if UDP not in pkt or Raw not in pkt:
                    continue

                # BACnet uses UDP 47808 (0xBAC0)
                if pkt[UDP].sport != 47808 and pkt[UDP].dport != 47808:
                    continue

                payload = bytes(pkt[Raw].load)
                src_ip = pkt[IP].src

                # BVLC header: type (1), function (1), length (2)
                if len(payload) < 4:
                    continue

                bvlc_type = payload[0]
                payload[1]
                struct.unpack(">H", payload[2:4])[0]

                # Type 0x81 = BACnet/IP
                if bvlc_type != 0x81:
                    continue

                bacnet_count += 1

                # For now, just record that we saw BACnet traffic
                # Full BACnet APDU parsing is complex

                if src_ip not in self.findings:
                    self.findings[src_ip] = {}
                if "bacnet" not in self.findings[src_ip]:
                    self.findings[src_ip]["bacnet"] = ProtocolFindings(src_ip, "bacnet")

                finding = self.findings[src_ip]["bacnet"]
                finding.packet_count += 1

                # Look for firmware revision in ReadProperty response
                # This would require full APDU parsing - simplified here
                # Property 44 (0x2C) = firmware_revision
                fw_marker = b"\x0c\x2c"  # Context tag 3 + Property 44
                if fw_marker in payload:
                    # Try to extract the value
                    idx = payload.find(fw_marker)
                    if idx > 0 and idx + 10 < len(payload):
                        # Look for character string value
                        for i in range(idx, min(idx + 20, len(payload))):
                            if payload[i] == 0x75:  # Character string application tag
                                str_len = payload[i+1] if i+1 < len(payload) else 0
                                if i + 2 + str_len <= len(payload):
                                    fw_string = payload[i+2:i+2+str_len].decode('utf-8', errors='replace')
                                    finding.values["firmware_revision"] = fw_string
                                break

            except Exception:
                continue

        print(f"  BACnet: Found {bacnet_count} packets")

    def compare_findings(self):
        """Compare findings against expected values."""
        for device_ip, expected_data in self.expected.items():
            expected_data.get("device_name", device_ip)
            expected_data.get("expected_firmware", "")

            # Check SNMP
            if "snmp_sys_descr" in expected_data or "snmp_sys_descr_contains" in expected_data:
                snmp_finding = self.findings.get(device_ip, {}).get("snmp")
                found_descr = snmp_finding.values.get("sys_descr", "") if snmp_finding else ""

                if "snmp_sys_descr" in expected_data:
                    expected = expected_data["snmp_sys_descr"]
                    passed = expected == found_descr
                    self.results.append(ValidationResult(
                        device_ip=device_ip,
                        protocol="SNMP",
                        field_name="sysDescr (exact)",
                        expected=expected,
                        found=found_descr,
                        passed=passed,
                    ))
                elif "snmp_sys_descr_contains" in expected_data:
                    expected = expected_data["snmp_sys_descr_contains"]
                    passed = expected.lower() in found_descr.lower()
                    self.results.append(ValidationResult(
                        device_ip=device_ip,
                        protocol="SNMP",
                        field_name="sysDescr (contains)",
                        expected=expected,
                        found=found_descr,
                        passed=passed,
                    ))

            if "snmp_sys_descr_contains_fw" in expected_data:
                snmp_finding = self.findings.get(device_ip, {}).get("snmp")
                found_descr = snmp_finding.values.get("sys_descr", "") if snmp_finding else ""
                expected_fw = expected_data["snmp_sys_descr_contains_fw"]
                passed = expected_fw in found_descr
                self.results.append(ValidationResult(
                    device_ip=device_ip,
                    protocol="SNMP",
                    field_name="sysDescr firmware",
                    expected=expected_fw,
                    found=found_descr,
                    passed=passed,
                ))

            if "snmp_sys_object_id" in expected_data:
                snmp_finding = self.findings.get(device_ip, {}).get("snmp")
                found_oid = snmp_finding.values.get("sys_object_id", "") if snmp_finding else ""
                expected = expected_data["snmp_sys_object_id"]
                passed = expected == found_oid
                self.results.append(ValidationResult(
                    device_ip=device_ip,
                    protocol="SNMP",
                    field_name="sysObjectID",
                    expected=expected,
                    found=found_oid,
                    passed=passed,
                ))

            # Check Modbus FC43
            if "modbus_major_minor_revision" in expected_data:
                modbus_finding = self.findings.get(device_ip, {}).get("modbus")
                found = modbus_finding.values.get("major_minor_revision", "") if modbus_finding else ""
                expected = expected_data["modbus_major_minor_revision"]
                passed = expected == found
                self.results.append(ValidationResult(
                    device_ip=device_ip,
                    protocol="Modbus FC43",
                    field_name="MajorMinorRevision",
                    expected=expected,
                    found=found,
                    passed=passed,
                ))

            # Check EtherNet/IP
            if "enip_revision_major" in expected_data:
                enip_finding = self.findings.get(device_ip, {}).get("ethernet_ip")
                found_major = enip_finding.values.get("revision_major", -1) if enip_finding else -1
                found_minor = enip_finding.values.get("revision_minor", -1) if enip_finding else -1
                expected_major = expected_data["enip_revision_major"]
                expected_minor = expected_data.get("enip_revision_minor", 0)

                self.results.append(ValidationResult(
                    device_ip=device_ip,
                    protocol="EtherNet/IP",
                    field_name="revision_major",
                    expected=expected_major,
                    found=found_major,
                    passed=expected_major == found_major,
                ))
                self.results.append(ValidationResult(
                    device_ip=device_ip,
                    protocol="EtherNet/IP",
                    field_name="revision_minor",
                    expected=expected_minor,
                    found=found_minor,
                    passed=expected_minor == found_minor,
                ))

            # Check PROFINET DCP (need to match by finding the device)
            if "profinet_sw_release" in expected_data:
                # PROFINET uses MAC, so we need to find by matching expected values
                expected_sw = expected_data["profinet_sw_release"]
                found_sw = None
                for key, protocols in self.findings.items():
                    if "profinet" in protocols:
                        pf = protocols["profinet"]
                        if pf.values.get("sw_release") == expected_sw:
                            found_sw = expected_sw
                            break
                        elif pf.values.get("sw_release"):
                            found_sw = pf.values.get("sw_release")

                self.results.append(ValidationResult(
                    device_ip=device_ip,
                    protocol="PROFINET DCP",
                    field_name="sw_release",
                    expected=expected_sw,
                    found=found_sw or "(not found)",
                    passed=expected_sw == found_sw,
                ))

            # Check S7comm
            if "s7_firmware_version" in expected_data:
                s7_finding = self.findings.get(device_ip, {}).get("s7comm")
                found = s7_finding.values.get("firmware_version", "") if s7_finding else ""
                expected = expected_data["s7_firmware_version"]
                passed = expected == found or expected in found
                self.results.append(ValidationResult(
                    device_ip=device_ip,
                    protocol="S7comm SZL",
                    field_name="firmware_version",
                    expected=expected,
                    found=found,
                    passed=passed,
                ))

            if "s7_order_code" in expected_data:
                s7_finding = self.findings.get(device_ip, {}).get("s7comm")
                found = s7_finding.values.get("order_code", "") if s7_finding else ""
                expected = expected_data["s7_order_code"]
                passed = expected == found or expected in found
                self.results.append(ValidationResult(
                    device_ip=device_ip,
                    protocol="S7comm SZL",
                    field_name="order_code",
                    expected=expected,
                    found=found,
                    passed=passed,
                ))

            # Check BACnet
            if "bacnet_firmware_revision" in expected_data:
                bacnet_finding = self.findings.get(device_ip, {}).get("bacnet")
                found = bacnet_finding.values.get("firmware_revision", "") if bacnet_finding else ""
                expected = expected_data["bacnet_firmware_revision"]
                passed = expected == found
                self.results.append(ValidationResult(
                    device_ip=device_ip,
                    protocol="BACnet",
                    field_name="firmware_revision",
                    expected=expected,
                    found=found or "(not parsed)",
                    passed=passed,
                    details="BACnet APDU parsing is simplified",
                ))

    def print_report(self) -> bool:
        """Print validation report and return success status."""
        print("\n" + "=" * 70)
        print("FINGERPRINT VALIDATION REPORT")
        print("=" * 70)

        # Print raw findings first
        print("\n--- RAW FINDINGS ---")
        for device_key, protocols in sorted(self.findings.items()):
            print(f"\n{device_key}:")
            for proto_name, finding in sorted(protocols.items()):
                print(f"  {proto_name} ({finding.packet_count} packets):")
                for k, v in finding.values.items():
                    print(f"    {k}: {v}")

        # Print validation results
        print("\n--- VALIDATION RESULTS ---")

        passed_count = sum(1 for r in self.results if r.passed)
        failed_count = len(self.results) - passed_count

        # Group by device
        by_device: dict[str, list[ValidationResult]] = defaultdict(list)
        for r in self.results:
            by_device[r.device_ip].append(r)

        for device_ip in sorted(by_device.keys()):
            expected_info = self.expected.get(device_ip, {})
            device_name = expected_info.get("device_name", device_ip)
            print(f"\n{device_name} ({device_ip}):")

            for r in by_device[device_ip]:
                status_symbol = "[+]" if r.passed else "[-]"
                print(f"  {status_symbol} {r.protocol} - {r.field_name}")
                print(f"      Expected: {r.expected}")
                print(f"      Found:    {r.found}")
                if r.details:
                    print(f"      Note:     {r.details}")

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Total Checks: {len(self.results)}")
        print(f"Passed:       {passed_count}")
        print(f"Failed:       {failed_count}")

        if failed_count == 0:
            print("\nAll fingerprint validations PASSED!")
        else:
            print(f"\n{failed_count} validation(s) FAILED - review findings above")

        return failed_count == 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate fingerprint packets from captured PCAP"
    )
    parser.add_argument(
        "--pcap",
        required=True,
        help="Path to PCAP file to analyze"
    )
    parser.add_argument(
        "--expected",
        default="/tmp/expected_fingerprints.json",
        help="Path to expected fingerprints JSON"
    )

    args = parser.parse_args()

    if not Path(args.pcap).exists():
        print(f"ERROR: PCAP file not found: {args.pcap}")
        sys.exit(1)

    if not Path(args.expected).exists():
        print(f"ERROR: Expected values file not found: {args.expected}")
        print("Run create_fingerprint_test_scenario.py first")
        sys.exit(1)

    validator = FingerprintValidator(args.pcap, args.expected)
    validator.validate_all()
    success = validator.print_report()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
