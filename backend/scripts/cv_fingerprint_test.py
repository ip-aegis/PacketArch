#!/usr/bin/env python3
"""CV Fingerprint Diagnostic — Generate PCAPs, inspect identity packets.

Standalone script — NO database, NO server required.
Generates a short PCAP per protocol, parses with scapy, reports PASS/FAIL.

Usage:
    cd /home/rocsmith/PacketArch/backend
    poetry run python scripts/cv_fingerprint_test.py
"""

import struct
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Suppress noisy scapy warnings
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

from scapy.all import rdpcap, Ether, IP, UDP, TCP, Raw

from app.protocol_engines.output import PcapOutput
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType
from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator
from app.services.device_templates._fingerprints import get_fingerprint_from_template

# ─────────────────────────────────────────────────────────────────
# Test Matrix: one device per protocol
# ─────────────────────────────────────────────────────────────────

TEST_CASES = [
    {
        "name": "Modbus — Schneider M340",
        "template_id": "schneider/modicon-m340/bmxp342020",
        "protocol": "modbus_tcp",
        "src_port": 50000,
        "dst_port": 502,
        "src_mac": None,  # Will be set from OUI
        "dst_mac": None,
        "src_ip": "10.1.0.100",
        "dst_ip": "10.1.0.10",
        "expected_oui": ["00:00:54", "00:80:F4"],
        "checks": ["mac_oui", "modbus_mei"],
    },
    {
        "name": "EtherNet/IP — Rockwell ControlLogix",
        "template_id": "rockwell/controllogix/l83e",
        "protocol": "ethernet_ip",
        "src_port": 50000,
        "dst_port": 44818,
        "src_mac": None,
        "dst_mac": None,
        "src_ip": "10.2.0.100",
        "dst_ip": "10.2.0.10",
        "expected_oui": ["00:00:BC", "00:1D:9C", "08:61:95", "5C:88:16", "E4:90:69"],
        "checks": ["mac_oui", "enip_list_identity"],
    },
    {
        "name": "S7comm — Siemens S7-1500",
        "template_id": "siemens/s7-1500/cpu-1516-3",
        "protocol": "s7comm",
        "src_port": 50000,
        "dst_port": 102,
        "src_mac": None,
        "dst_mac": None,
        "src_ip": "10.3.0.100",
        "dst_ip": "10.3.0.10",
        "expected_oui": ["00:0E:8C", "00:1B:1B", "00:1C:06"],
        "checks": ["mac_oui", "s7_szl"],
    },
    {
        "name": "PROFINET — Siemens S7-1500",
        "template_id": "siemens/s7-1500/cpu-1516-3",
        "protocol": "profinet",
        "src_port": 0,
        "dst_port": 0,
        "src_mac": None,
        "dst_mac": None,
        "src_ip": "10.4.0.100",
        "dst_ip": "10.4.0.10",
        "expected_oui": ["00:0E:8C", "00:1B:1B", "00:1C:06"],
        "checks": ["mac_oui", "profinet_dcp"],
    },
    {
        "name": "BACnet — Honeywell JACE 8000",
        "template_id": "honeywell/niagara/jace-8000",
        "protocol": "bacnet",
        "src_port": 47809,
        "dst_port": 47808,
        "src_mac": None,
        "dst_mac": None,
        "src_ip": "10.5.0.100",
        "dst_ip": "10.5.0.10",
        "expected_oui": ["00:60:35", "00:D0:36"],
        "checks": ["mac_oui", "bacnet_iam"],
    },
    {
        "name": "SNMP — Schneider ConneXium",
        "template_id": "schneider/connexium/tcsesm083f2cu0",
        "protocol": "snmp",
        "src_port": 50000,
        "dst_port": 161,
        "src_mac": None,
        "dst_mac": None,
        "src_ip": "10.6.0.100",
        "dst_ip": "10.6.0.10",
        "expected_oui": ["00:00:54", "00:80:F4"],
        "checks": ["mac_oui", "snmp_sysinfo"],
    },
]


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"
BOLD = "\033[1m"
RESET = "\033[0m"

results_summary: list[tuple[str, str, str, bool]] = []  # (test, check, detail, passed)


def report(test_name: str, check: str, detail: str, passed: bool):
    """Record and print a check result."""
    status = PASS if passed else FAIL
    print(f"  [{status}] {check}: {detail}")
    results_summary.append((test_name, check, detail, passed))


def mac_to_oui(mac: str) -> str:
    """Extract OUI prefix from MAC address."""
    parts = mac.upper().split(":")
    return ":".join(parts[:3])


def generate_vendor_mac(oui_prefix: str) -> str:
    """Generate a MAC address with the given OUI prefix."""
    import random
    suffix = ":".join(f"{random.randint(0, 255):02X}" for _ in range(3))
    return f"{oui_prefix}:{suffix}"


def load_fingerprint(template_id: str) -> dict:
    """Load fingerprint from template library."""
    fp = get_fingerprint_from_template(template_id, include_instance=True)
    if not fp:
        print(f"  ERROR: Template '{template_id}' not found!")
        return {}
    return fp


# ─────────────────────────────────────────────────────────────────
# PCAP Generation
# ─────────────────────────────────────────────────────────────────

def generate_pcap(test_case: dict, output_dir: Path) -> Path | None:
    """Generate a PCAP for a single protocol test case."""
    name = test_case["name"]
    template_id = test_case["template_id"]
    protocol_str = test_case["protocol"]

    print(f"\n  Generating PCAP for: {name}")

    # Load fingerprint
    fp = load_fingerprint(template_id)
    if not fp:
        return None

    oui_prefixes = fp.get("oui_prefixes", [])
    dst_oui = oui_prefixes[0] if oui_prefixes else "02:00:00"
    src_oui = "00:AA:BB"  # HMI/generic client

    dst_mac = generate_vendor_mac(dst_oui)
    src_mac = generate_vendor_mac(src_oui)

    print(f"    Fingerprint vendor: {fp.get('vendor', 'N/A')}")
    print(f"    Fingerprint model:  {fp.get('model', 'N/A')}")
    print(f"    OUI prefixes:       {oui_prefixes}")
    print(f"    Target MAC:         {dst_mac} (OUI: {dst_oui})")
    print(f"    Firmware:           {fp.get('firmware_version', 'N/A')}")

    # Show protocol identities present
    for proto_key in ["modbus_identity", "ethernet_ip_identity", "profinet_identity",
                      "s7_identity", "bacnet_identity", "snmp_identity"]:
        val = fp.get(proto_key)
        if val:
            print(f"    {proto_key}: {len(val)} fields")
        else:
            print(f"    {proto_key}: NONE")

    # Build device contexts
    source = DeviceContext(
        device_id="hmi-test",
        mac_address=src_mac,
        ip_address=test_case["src_ip"],
        port=test_case["src_port"],
        vendor_fingerprint={},  # HMI has no fingerprint
        device_name="Test HMI",
    )

    destination = DeviceContext(
        device_id="device-under-test",
        mac_address=dst_mac,
        ip_address=test_case["dst_ip"],
        port=test_case["dst_port"],
        vendor_fingerprint=fp,
        scenario_id="cv-test-001",
        device_name=name,
    )

    protocol = ProtocolType(protocol_str)

    flow = FlowContext(
        flow_id=f"test-{protocol_str}",
        source=source,
        destination=destination,
        protocol=protocol,
        config={"poll_interval_ms": 1000},
        timing_model={},
    )

    # Store for later checks
    test_case["_fingerprint"] = fp
    test_case["_dst_mac"] = dst_mac

    # Generate PCAP
    pcap_path = output_dir / f"cv_test_{protocol_str}.pcap"
    try:
        output = PcapOutput(str(pcap_path))
        orchestrator = UnifiedOrchestrator(
            output=output,
            duration_ms=5000,  # 5 seconds of traffic
        )
        orchestrator.add_flow(flow)
        result = orchestrator.run()
        output.close()

        if result.error:
            print(f"    ERROR: {result.error}")
            return None

        print(f"    Generated: {result.packets_generated} packets, {pcap_path.stat().st_size} bytes")
        return pcap_path

    except Exception as e:
        print(f"    ERROR generating PCAP: {e}")
        import traceback
        traceback.print_exc()
        return None


# ─────────────────────────────────────────────────────────────────
# PCAP Analysis Functions
# ─────────────────────────────────────────────────────────────────

def check_mac_oui(test_name: str, packets, expected_ouis: list[str], dst_ip: str, dst_mac: str):
    """Check that device MAC addresses use correct vendor OUI."""
    expected_upper = [o.upper() for o in expected_ouis]
    assigned_oui = mac_to_oui(dst_mac)

    passed = assigned_oui in expected_upper
    report(test_name, "MAC OUI Assigned",
           f"Device MAC {dst_mac} → OUI {assigned_oui} {'in' if passed else 'NOT in'} {expected_ouis}",
           passed)

    # Also check packets actually use the assigned MAC
    device_macs_seen = set()
    for pkt in packets:
        if pkt.haslayer(Ether):
            eth = pkt[Ether]
            # Check if the device IP matches (look at IP layer)
            if pkt.haslayer(IP):
                if pkt[IP].src == dst_ip:
                    device_macs_seen.add(eth.src.upper())
                elif pkt[IP].dst == dst_ip:
                    device_macs_seen.add(eth.dst.upper())
            else:
                # Layer 2 only (PROFINET) - check Ethernet src
                device_macs_seen.add(eth.src.upper())
                device_macs_seen.add(eth.dst.upper())

    if device_macs_seen:
        # Filter out the HMI/client MAC (non-device MACs are expected in L2 frames)
        device_only = {m for m in device_macs_seen if m == dst_mac.upper()}
        other_macs = device_macs_seen - device_only
        if device_only:
            for mac in device_only:
                oui = mac_to_oui(mac)
                mac_ok = oui in expected_upper
                if not mac_ok:
                    report(test_name, "MAC in packets",
                           f"Device MAC {mac} OUI {oui} NOT in expected {expected_ouis}",
                           False)
                    return
            report(test_name, "MAC in packets",
                   f"Device MAC {dst_mac.upper()} has correct OUI in packets",
                   True)
        else:
            report(test_name, "MAC in packets",
                   f"Device MAC {dst_mac.upper()} not seen in packets (only saw {other_macs})",
                   False)
    else:
        report(test_name, "MAC in packets", "No packets found with device IP", False)


def check_modbus_mei(test_name: str, packets, fingerprint: dict):
    """Check for Modbus MEI (FC 43) device identification responses."""
    mei_responses = []
    modbus_id = fingerprint.get("modbus_identity", {})

    for pkt in packets:
        if not pkt.haslayer(TCP) or not pkt.haslayer(Raw):
            continue
        payload = bytes(pkt[Raw].load)
        if len(payload) < 8:
            continue

        # MBAP header: 2-byte txn_id, 2-byte protocol_id(0), 2-byte length, 1-byte unit_id
        # Then PDU: function_code
        if len(payload) >= 8:
            func_code = payload[7]
            # FC 43 = 0x2B (Read Device Identification)
            if func_code == 0x2B and len(payload) > 10:
                mei_type = payload[8]  # MEI type (0x0E)
                if mei_type == 0x0E:
                    mei_responses.append(payload)

    if mei_responses:
        report(test_name, "Modbus MEI present",
               f"Found {len(mei_responses)} FC43/MEI response(s)", True)

        # Try to extract object 0x00 (vendor name)
        for resp in mei_responses:
            objects = _parse_mei_objects(resp)
            if objects:
                vendor_found = objects.get(0, "")
                product_code_found = objects.get(1, "")
                revision_found = objects.get(2, "")
                product_name_found = objects.get(4, "")

                expected_vendor = modbus_id.get("vendor_name", "")
                expected_product = modbus_id.get("product_code", "")

                if vendor_found:
                    report(test_name, "Modbus vendor_name",
                           f"'{vendor_found}' (expected: '{expected_vendor}')",
                           vendor_found == expected_vendor if expected_vendor else True)
                else:
                    report(test_name, "Modbus vendor_name", "NOT FOUND in MEI response", False)

                if product_code_found:
                    report(test_name, "Modbus product_code",
                           f"'{product_code_found}' (expected: '{expected_product}')",
                           product_code_found == expected_product if expected_product else True)

                if revision_found:
                    report(test_name, "Modbus revision", f"'{revision_found}'", True)
                else:
                    report(test_name, "Modbus revision", "NOT FOUND", False)

                if product_name_found:
                    report(test_name, "Modbus product_name", f"'{product_name_found}'", True)

                break  # Only check first MEI response
    else:
        # Check if there are ANY Modbus packets
        modbus_count = sum(1 for p in packets if p.haslayer(TCP) and p.haslayer(Raw)
                          and len(bytes(p[Raw].load)) >= 8)
        report(test_name, "Modbus MEI present",
               f"NO FC43/MEI responses found ({modbus_count} TCP+payload packets total)", False)


def _parse_mei_objects(payload: bytes) -> dict[int, str]:
    """Parse Modbus MEI response objects."""
    objects = {}
    try:
        # Skip MBAP (7 bytes) + FC(1) + MEI type(1) + read_device_id(1) + conformity(1) + more_follows(1) + next_obj(1) + num_objects(1)
        offset = 14
        if offset >= len(payload):
            return objects
        num_objects = payload[13]
        for _ in range(num_objects):
            if offset + 2 > len(payload):
                break
            obj_id = payload[offset]
            obj_len = payload[offset + 1]
            offset += 2
            if offset + obj_len > len(payload):
                break
            obj_val = payload[offset:offset + obj_len].decode("ascii", errors="replace")
            objects[obj_id] = obj_val
            offset += obj_len
    except Exception:
        pass
    return objects


def check_enip_list_identity(test_name: str, packets, fingerprint: dict):
    """Check for EtherNet/IP ListIdentity responses."""
    enip_id = fingerprint.get("ethernet_ip_identity", {})
    list_identity_found = False

    for pkt in packets:
        if not pkt.haslayer(Raw):
            continue
        # Check both TCP and UDP
        if pkt.haslayer(TCP):
            payload = bytes(pkt[Raw].load)
        elif pkt.haslayer(UDP):
            payload = bytes(pkt[Raw].load)
        else:
            continue

        if len(payload) < 24:
            continue

        # EtherNet/IP encapsulation header: command(2) + length(2) + session(4) + status(4) + context(8) + options(4) = 24 bytes
        command = struct.unpack_from("<H", payload, 0)[0]
        data_length = struct.unpack_from("<H", payload, 2)[0]

        # 0x0063 = ListIdentity — skip requests (data_length=0)
        if command == 0x0063 and data_length > 0:
            list_identity_found = True
            report(test_name, "EtherNet/IP ListIdentity", "Response packet found", True)

            # Try to parse identity data from CPF
            _parse_enip_identity(test_name, payload, enip_id)
            break

        # Also check for CIP Identity Get Attributes All response
        if command == 0x006F:  # SendRRData
            # This contains wrapped CIP responses
            pass

    if not list_identity_found:
        # Check if we have any EtherNet/IP packets at all
        enip_count = 0
        for pkt in packets:
            if pkt.haslayer(TCP) and pkt.haslayer(Raw):
                payload = bytes(pkt[Raw].load)
                if len(payload) >= 4:
                    cmd = struct.unpack_from("<H", payload, 0)[0]
                    if cmd in (0x0001, 0x0004, 0x0063, 0x0065, 0x0066, 0x006F, 0x0070):
                        enip_count += 1
        report(test_name, "EtherNet/IP ListIdentity",
               f"NOT found ({enip_count} EtherNet/IP packets total)", False)


def _parse_enip_identity(test_name: str, payload: bytes, expected: dict):
    """Parse EtherNet/IP ListIdentity response for identity data."""
    try:
        # Encapsulation header = 24 bytes
        # CPF: item_count(2), then items...
        offset = 24
        if offset + 2 > len(payload):
            return
        item_count = struct.unpack_from("<H", payload, offset)[0]
        offset += 2

        for _ in range(item_count):
            if offset + 4 > len(payload):
                break
            type_id, length = struct.unpack_from("<HH", payload, offset)
            offset += 4

            # 0x000C = ListIdentity response item
            if type_id == 0x000C and length > 20:
                # Identity data structure
                # protocol_version(2) + socket_addr(16) + vendor_id(2) + device_type(2) +
                # product_code(2) + revision_major(1) + revision_minor(1) + status(2) +
                # serial_number(4) + product_name_len(1) + product_name(N) + state(1)
                id_offset = offset
                proto_ver = struct.unpack_from("<H", payload, id_offset)[0]
                id_offset += 2

                # Skip socket address (sin_family(2) + sin_port(2) + sin_addr(4) + sin_zero(8) = 16)
                id_offset += 16

                vendor_id = struct.unpack_from("<H", payload, id_offset)[0]
                id_offset += 2
                device_type = struct.unpack_from("<H", payload, id_offset)[0]
                id_offset += 2
                product_code = struct.unpack_from("<H", payload, id_offset)[0]
                id_offset += 2
                rev_major = payload[id_offset]
                id_offset += 1
                rev_minor = payload[id_offset]
                id_offset += 1
                status = struct.unpack_from("<H", payload, id_offset)[0]
                id_offset += 2
                serial = struct.unpack_from("<I", payload, id_offset)[0]
                id_offset += 4
                name_len = payload[id_offset]
                id_offset += 1
                product_name = payload[id_offset:id_offset + name_len].decode("ascii", errors="replace")

                exp_vendor_id = expected.get("vendor_id")
                if exp_vendor_id is not None:
                    report(test_name, "EtherNet/IP vendor_id",
                           f"{vendor_id} (expected: {exp_vendor_id})",
                           vendor_id == exp_vendor_id)
                else:
                    report(test_name, "EtherNet/IP vendor_id", f"{vendor_id}", True)

                report(test_name, "EtherNet/IP device_type", f"{device_type}", True)
                report(test_name, "EtherNet/IP product_code", f"{product_code}", True)
                report(test_name, "EtherNet/IP revision", f"{rev_major}.{rev_minor}", True)
                report(test_name, "EtherNet/IP serial_number", f"0x{serial:08X}", serial != 0)
                report(test_name, "EtherNet/IP product_name",
                       f"'{product_name}'" if product_name else "EMPTY",
                       bool(product_name))
                return

            offset += length

    except Exception as e:
        report(test_name, "EtherNet/IP identity parse", f"Error: {e}", False)


def check_s7_szl(test_name: str, packets, fingerprint: dict):
    """Check for S7comm SZL responses with identity data."""
    s7_id = fingerprint.get("s7_identity", {})
    szl_found = False

    for pkt in packets:
        if not pkt.haslayer(TCP) or not pkt.haslayer(Raw):
            continue
        payload = bytes(pkt[Raw].load)
        if len(payload) < 10:
            continue

        # TPKT header: version(1)=3, reserved(1)=0, length(2)
        # COTP header: length(1), pdu_type(1), ...
        # S7 header: protocol_id(1)=0x32, ...
        if payload[0] != 0x03:  # TPKT version
            continue

        # Find S7 protocol marker (0x32)
        s7_offset = None
        for i in range(2, min(len(payload) - 1, 20)):
            if payload[i] == 0x32:
                s7_offset = i
                break

        if s7_offset is None:
            continue

        # S7 header: protocol_id(1) + rosctr(1) + ...
        rosctr = payload[s7_offset + 1]
        if rosctr == 0x07:  # Userdata (SZL request or response)
            # Check ALL rosctr 0x07 packets — the first is the request,
            # subsequent ones are responses that contain the identity data.
            szl_found = True
            _parse_s7_szl_response(test_name, payload, s7_offset, s7_id)

    if szl_found:
        report(test_name, "S7 SZL response", "Found SZL userdata response", True)
        # Report failures for items not found in any SZL packet
        for key, field, label in [
            ("module_type", s7_id.get("module_type", ""), "S7 module_type"),
            ("order_code", s7_id.get("order_code", ""), "S7 order_code"),
            ("firmware_version", s7_id.get("firmware_version", ""), "S7 firmware"),
            ("serial_number", "expected", "S7 serial"),
        ]:
            rk = f"{test_name}:{key}"
            if field and rk not in _s7_szl_reported:
                report(test_name, label,
                       f"'{field}' NOT found in any SZL data" if key != "serial_number"
                       else "No serial number pattern found in SZL data",
                       False)
    else:
        # Count S7 packets
        s7_count = 0
        for pkt in packets:
            if pkt.haslayer(TCP) and pkt.haslayer(Raw):
                p = bytes(pkt[Raw].load)
                if len(p) > 3 and p[0] == 0x03:
                    s7_count += 1
        report(test_name, "S7 SZL response",
               f"NOT found ({s7_count} TPKT packets total)", False)


_s7_szl_reported: set[str] = set()  # Track which checks already reported


def _parse_s7_szl_response(test_name: str, payload: bytes, s7_offset: int, expected: dict):
    """Parse S7 SZL response for identity data.

    SZL 0x0011 record layout (64 bytes, offsets relative to SZL data start):
        0-1:   SZL ID (0x0011)
        2-3:   SZL Index
        4-5:   Data length (64)
        6-7:   Element count
        8-27:  order_code (20 bytes, ASCII null-padded)
        28-39: serial_number (12 bytes, ASCII null-padded)
        40-47: firmware_version (8 bytes, ASCII null-padded)
        48-71: module_type (24 bytes, ASCII null-padded)
    """
    try:
        data = payload[s7_offset:]
        text = data.decode("ascii", errors="replace")
        order_code = expected.get("order_code", "")
        module_type = expected.get("module_type", "")
        serial_number = expected.get("serial_number", "")
        firmware_version = expected.get("firmware_version", "")

        # Try to find SZL data by looking for the 64-byte record
        # The SZL data contains known strings at fixed offsets
        found_fields: dict[str, str] = {}
        for key, val, label in [
            ("module_type", module_type, "S7 module_type"),
            ("order_code", order_code[:8] if order_code else "", "S7 order_code"),
            ("firmware_version", firmware_version, "S7 firmware"),
        ]:
            report_key = f"{test_name}:{key}"
            if val and val in text and report_key not in _s7_szl_reported:
                found_fields[key] = val
                report(test_name, label, f"Found '{val}' in SZL data", True)
                _s7_szl_reported.add(report_key)

        # Serial number: FingerprintApplicator generates unique serials,
        # so check for "S " prefix pattern (Siemens serial format) instead of exact match
        serial_key = f"{test_name}:serial_number"
        if serial_key not in _s7_szl_reported:
            # Look for any serial-like pattern: "S " followed by alphanumeric
            import re
            serial_match = re.search(r"S [A-Z0-9-]{6,}", text)
            if serial_match:
                report(test_name, "S7 serial", f"Found '{serial_match.group()}' in SZL data", True)
                _s7_szl_reported.add(serial_key)

    except Exception as e:
        report(test_name, "S7 SZL parse", f"Error: {e}", False)


def check_profinet_dcp(test_name: str, packets, fingerprint: dict):
    """Check for PROFINET DCP Identify responses."""
    pn_id = fingerprint.get("profinet_identity", {})
    dcp_found = False

    for pkt in packets:
        if not pkt.haslayer(Ether):
            continue
        eth = pkt[Ether]

        # PROFINET frames use EtherType 0x8892
        if eth.type == 0x8892:
            payload = bytes(pkt.payload.payload) if pkt.payload and pkt.payload.payload else bytes(pkt)[14:]
            # Actually, for raw Ether frames with unknown type, scapy puts rest in Raw
            if pkt.haslayer(Raw):
                payload = bytes(pkt[Raw].load)
            else:
                payload = bytes(pkt)[14:]  # Skip Ethernet header

            if len(payload) < 4:
                continue

            # Frame ID (2 bytes)
            frame_id = struct.unpack_from(">H", payload, 0)[0]

            # DCP Identify Response: frame_id = 0xFEFF
            # DCP Identify Request:  frame_id = 0xFEFE
            if frame_id == 0xFEFF:  # Identify response
                dcp_found = True
                report(test_name, "PROFINET DCP Identify",
                       f"Response found (frame_id=0x{frame_id:04X})", True)
                _parse_dcp_blocks(test_name, payload, pn_id)
                break
            elif frame_id == 0xFEFE:
                pass  # Request, skip

    if not dcp_found:
        # Count PROFINET frames
        pn_count = sum(1 for p in packets if p.haslayer(Ether) and p[Ether].type == 0x8892)
        report(test_name, "PROFINET DCP Identify",
               f"Response NOT found ({pn_count} PROFINET frames total)", False)


def _parse_dcp_blocks(test_name: str, payload: bytes, expected: dict):
    """Parse PROFINET DCP blocks for identity data."""
    try:
        # Skip FrameID(2) + ServiceID(1) + ServiceType(1) + Xid(4) + ResponseDelay(2) + DataLength(2)
        offset = 12
        if offset >= len(payload):
            return

        found_vendor_id = None
        found_device_id = None
        found_station_name = None
        found_oem_device_id = None  # "OrderID:...;SN:...;Type:...;HW:...;SW:..."

        while offset + 4 <= len(payload):
            option = payload[offset]
            suboption = payload[offset + 1]
            block_len = struct.unpack_from(">H", payload, offset + 2)[0]
            offset += 4

            if offset + block_len > len(payload):
                break

            block_data = payload[offset:offset + block_len]

            # Device Properties (option 2)
            if option == 0x02:
                if suboption == 0x03 and len(block_data) >= 4:
                    # DeviceID block: Vendor ID (2) + Device ID (2)
                    found_vendor_id = struct.unpack_from(">H", block_data, 0)[0]
                    found_device_id = struct.unpack_from(">H", block_data, 2)[0]
                elif suboption == 0x02 and len(block_data) >= 1:
                    # NameOfStation — raw ASCII
                    found_station_name = block_data.decode("ascii", errors="replace").rstrip("\x00")
                elif suboption == 0x08 and len(block_data) >= 5:
                    # OEM Device ID — "OrderID:...;SN:...;Type:...;HW:...;SW:..."
                    found_oem_device_id = block_data.decode("ascii", errors="replace").rstrip("\x00")

            # Pad to even
            offset += block_len
            if block_len % 2 == 1:
                offset += 1

        exp_vendor_id = expected.get("vendor_id")
        if found_vendor_id is not None:
            report(test_name, "PROFINET vendor_id",
                   f"0x{found_vendor_id:04X} (expected: 0x{exp_vendor_id:04X})" if exp_vendor_id else f"0x{found_vendor_id:04X}",
                   found_vendor_id == exp_vendor_id if exp_vendor_id else True)
        else:
            report(test_name, "PROFINET vendor_id", "NOT found in DCP blocks", False)

        if found_station_name:
            report(test_name, "PROFINET station_name", f"'{found_station_name}'", True)
        else:
            report(test_name, "PROFINET station_name", "NOT found in DCP blocks", False)

        # Parse OEM Device ID for firmware, serial, order code
        if found_oem_device_id:
            oem_parts = {}
            for part in found_oem_device_id.split(";"):
                if ":" in part:
                    k, v = part.split(":", 1)
                    oem_parts[k.strip()] = v.strip()
            sw = oem_parts.get("SW", "")
            sn = oem_parts.get("SN", "")
            order_id = oem_parts.get("OrderID", "")
            dev_type = oem_parts.get("Type", "")
            report(test_name, "PROFINET firmware (OEM)",
                   f"SW='{sw}'" if sw else "SW field MISSING in OEM",
                   bool(sw))
            report(test_name, "PROFINET serial (OEM)",
                   f"SN='{sn}'" if sn else "SN field MISSING in OEM",
                   bool(sn))
            report(test_name, "PROFINET order_code (OEM)",
                   f"OrderID='{order_id}'" if order_id else "OrderID MISSING in OEM",
                   bool(order_id))
        else:
            report(test_name, "PROFINET OEM Device ID", "NOT found in DCP blocks", False)

    except Exception as e:
        report(test_name, "PROFINET DCP parse", f"Error: {e}", False)


def check_bacnet_iam(test_name: str, packets, fingerprint: dict):
    """Check for BACnet I-Am broadcasts and ReadProperty identity responses."""
    bacnet_id = fingerprint.get("bacnet_identity", {})
    iam_found = False

    # Check all BACnet packets for I-Am and identity strings
    identity_strings_found: dict[str, str] = {}

    for pkt in packets:
        if not pkt.haslayer(UDP) or not pkt.haslayer(Raw):
            continue
        if pkt[UDP].dport != 47808 and pkt[UDP].sport != 47808:
            continue

        payload = bytes(pkt[Raw].load)
        if len(payload) < 8:
            continue

        # BVLC header: type(1)=0x81, function(1), length(2)
        if payload[0] != 0x81:  # Not BVLC
            continue

        # Skip BVLC header (4 bytes)
        npdu_offset = 4
        if npdu_offset >= len(payload):
            continue

        # NPDU: version(1) + control(1)
        npdu_control = payload[npdu_offset + 1]
        npdu_len = 2
        if npdu_control & 0x20:  # DNET present
            npdu_len += 4  # DNET(2) + DLEN(1) + hop_count(1)
            if npdu_offset + 2 < len(payload):
                dlen = payload[npdu_offset + 4]
                npdu_len += dlen

        apdu_offset = npdu_offset + npdu_len
        if apdu_offset >= len(payload):
            continue

        apdu_type = (payload[apdu_offset] >> 4) & 0x0F

        # I-Am is Unconfirmed Service Request (type 1), service choice 0
        if apdu_type == 0x01:  # Unconfirmed
            if apdu_offset + 1 < len(payload):
                service_choice = payload[apdu_offset + 1]
                if service_choice == 0x00:  # I-Am
                    iam_found = True

        # Search for identity strings in all BACnet response packets
        # ReadProperty responses contain the identity as ASCII strings in the APDU
        text = payload.decode("ascii", errors="replace")
        for key, field in [
            ("vendor_name", bacnet_id.get("vendor_name", "")),
            ("model_name", bacnet_id.get("model_name", "")),
            ("firmware_revision", bacnet_id.get("firmware_revision", "")),
        ]:
            if field and field in text and key not in identity_strings_found:
                identity_strings_found[key] = field

    if iam_found:
        report(test_name, "BACnet I-Am", "I-Am broadcast found", True)
    else:
        bacnet_count = sum(1 for p in packets if p.haslayer(UDP) and p.haslayer(Raw)
                          and (p[UDP].dport == 47808 or p[UDP].sport == 47808))
        report(test_name, "BACnet I-Am",
               f"NOT found ({bacnet_count} BACnet/UDP packets total)", False)

    # Report identity field checks
    for key, label in [
        ("vendor_name", "BACnet vendor_name"),
        ("model_name", "BACnet model_name"),
        ("firmware_revision", "BACnet firmware"),
    ]:
        expected_val = bacnet_id.get(key, "")
        if expected_val:
            found = identity_strings_found.get(key)
            if found:
                report(test_name, label, f"'{found}' found in ReadProperty response", True)
            else:
                report(test_name, label,
                       f"'{expected_val}' NOT found in any BACnet packet", False)
        else:
            report(test_name, label, f"No expected {key} in fingerprint", False)


def check_snmp_sysinfo(test_name: str, packets, fingerprint: dict):
    """Check for SNMP GetResponse with system info (sysDescr, sysName, sysObjectID)."""
    snmp_id = fingerprint.get("snmp_identity", {})
    snmp_responses = 0
    found_fields: dict[str, str] = {}

    for pkt in packets:
        if not pkt.haslayer(UDP):
            continue
        if pkt[UDP].sport != 161:  # Responses come FROM port 161
            continue

        # Scapy auto-parses SNMP so Raw may not exist.
        # Get raw bytes from the UDP payload instead.
        payload = bytes(pkt[UDP].payload)
        if len(payload) < 10:
            continue

        # SNMP is BER/ASN.1 encoded — Sequence tag = 0x30
        if payload[0] != 0x30:
            continue

        snmp_responses += 1
        # Search for identity strings in the raw SNMP response bytes
        text = payload.decode("ascii", errors="replace")
        for key, field in [
            ("sys_descr", snmp_id.get("sys_descr", "")),
            ("sys_name", snmp_id.get("sys_name", "")),
            ("sys_object_id", snmp_id.get("sys_object_id", "")),
        ]:
            if field and field[:20] in text and key not in found_fields:
                found_fields[key] = field

    if snmp_responses > 0:
        report(test_name, "SNMP responses",
               f"Found {snmp_responses} GetResponse packets from port 161", True)
    else:
        snmp_count = sum(1 for p in packets if p.haslayer(UDP)
                        and (p[UDP].dport == 161 or p[UDP].sport == 161))
        report(test_name, "SNMP responses",
               f"NOT found ({snmp_count} SNMP port 161 packets total)", False)

    # Report identity field checks
    for key, label in [
        ("sys_descr", "SNMP sysDescr"),
        ("sys_name", "SNMP sysName"),
    ]:
        expected_val = snmp_id.get(key, "")
        if expected_val:
            found = found_fields.get(key)
            if found:
                report(test_name, label, f"'{found[:60]}' found in response", True)
            else:
                report(test_name, label,
                       f"'{expected_val[:40]}' NOT found in any SNMP response", False)


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────

def main():
    output_dir = Path("/tmp/cv_fingerprint_test")
    output_dir.mkdir(exist_ok=True)

    print(f"{BOLD}{'=' * 70}")
    print("PacketArch CV Fingerprint Diagnostic")
    print(f"{'=' * 70}{RESET}")
    print(f"Output directory: {output_dir}\n")

    # Phase 1: Generate PCAPs
    print(f"{BOLD}Phase 1: Generate PCAPs{RESET}")
    print("-" * 50)

    pcap_paths: dict[str, Path | None] = {}
    for tc in TEST_CASES:
        try:
            path = generate_pcap(tc, output_dir)
            pcap_paths[tc["name"]] = path
        except Exception as e:
            print(f"  FATAL: {tc['name']}: {e}")
            import traceback
            traceback.print_exc()
            pcap_paths[tc["name"]] = None

    # Phase 2: Analyze PCAPs
    print(f"\n{BOLD}Phase 2: Analyze PCAPs{RESET}")
    print("-" * 50)

    for tc in TEST_CASES:
        name = tc["name"]
        pcap_path = pcap_paths.get(name)

        print(f"\n{BOLD}>>> {name}{RESET}")

        if not pcap_path or not pcap_path.exists():
            report(name, "PCAP generation", "Failed to generate PCAP", False)
            continue

        packets = rdpcap(str(pcap_path))
        print(f"  Loaded {len(packets)} packets from {pcap_path.name}")

        fp = tc.get("_fingerprint", {})
        dst_mac = tc.get("_dst_mac", "")
        dst_ip = tc["dst_ip"]

        for check in tc["checks"]:
            if check == "mac_oui":
                check_mac_oui(name, packets, tc["expected_oui"], dst_ip, dst_mac)
            elif check == "modbus_mei":
                check_modbus_mei(name, packets, fp)
            elif check == "enip_list_identity":
                check_enip_list_identity(name, packets, fp)
            elif check == "s7_szl":
                check_s7_szl(name, packets, fp)
            elif check == "profinet_dcp":
                check_profinet_dcp(name, packets, fp)
            elif check == "bacnet_iam":
                check_bacnet_iam(name, packets, fp)
            elif check == "snmp_sysinfo":
                check_snmp_sysinfo(name, packets, fp)

    # Summary
    print(f"\n{BOLD}{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}{RESET}")

    passed = sum(1 for _, _, _, p in results_summary if p)
    failed = sum(1 for _, _, _, p in results_summary if not p)
    total = len(results_summary)

    print(f"\n  Total checks: {total}")
    print(f"  {PASS}: {passed}")
    print(f"  {FAIL}: {failed}")

    if failed:
        print(f"\n{BOLD}Failed checks:{RESET}")
        for test_name, check, detail, p in results_summary:
            if not p:
                print(f"  [{FAIL}] {test_name} / {check}: {detail}")

    print(f"\nPCAP files in: {output_dir}/")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
