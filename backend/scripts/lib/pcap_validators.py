"""Shared PCAP fingerprint validation library.

Parses PCAP files with Scapy and validates per-device protocol identity
packets against expected values from device templates.

Used by:
  - scripts/validate_scenario.py  (full scenario validation)
  - scripts/cv_fingerprint_test.py (single-protocol quick tests)
"""

from __future__ import annotations

import struct
import re
import logging
from dataclasses import dataclass, field
from typing import Any

from scapy.all import Ether, IP, UDP, TCP, Raw

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    """Result of a single validation check."""

    device_name: str
    device_ip: str
    protocol: str
    check_name: str
    expected: str | None
    actual: str | None
    passed: bool
    detail: str


@dataclass
class DeviceExpectation:
    """Expected identity fields for a device."""

    device_id: str
    device_name: str
    mac_address: str  # Upper-cased
    ip_address: str
    vendor: str
    model: str
    fingerprint: dict[str, Any]  # Full vendor_fingerprint dict
    expected_oui_prefixes: list[str]
    protocols_serving: set[str]  # Protocols where this device is TARGET


@dataclass
class DeviceValidationReport:
    """All check results for one device."""

    device_name: str
    device_ip: str
    device_mac: str
    vendor: str
    model: str
    protocols_serving: set[str]
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]


@dataclass
class ScenarioValidationReport:
    """Full report for a scenario template."""

    template_name: str
    vertical: str
    device_count: int
    flow_count: int
    pcap_packets: int
    generation_time_ms: float
    pcap_path: str | None
    device_reports: list[DeviceValidationReport] = field(default_factory=list)

    @property
    def total_checks(self) -> int:
        return sum(len(r.checks) for r in self.device_reports)

    @property
    def total_passed(self) -> int:
        return sum(r.pass_count for r in self.device_reports)

    @property
    def total_failed(self) -> int:
        return sum(r.fail_count for r in self.device_reports)

    @property
    def all_passed(self) -> bool:
        return self.total_failed == 0


# ─────────────────────────────────────────────────────────────────
# Protocol Alias Map (for mapping flow protocols to identity keys)
# ─────────────────────────────────────────────────────────────────

PROTOCOL_ALIASES: dict[str, str] = {
    "profisafe": "profinet",
    "s7comm_plus": "s7comm",
    "cip_safety": "ethernet_ip",
    "modbus": "modbus_tcp",
    "enip": "ethernet_ip",
    "bacnet_ip": "bacnet",
}

# Map parent protocol → identity key in fingerprint dict
PROTOCOL_TO_IDENTITY_KEY: dict[str, str] = {
    "modbus_tcp": "modbus_identity",
    "ethernet_ip": "ethernet_ip_identity",
    "profinet": "profinet_identity",
    "s7comm": "s7_identity",
    "bacnet": "bacnet_identity",
    "snmp": "snmp_identity",
}

# Map parent protocol → validator method name
PROTOCOL_TO_VALIDATOR: dict[str, str] = {
    "modbus_tcp": "_check_modbus_mei",
    "ethernet_ip": "_check_enip_list_identity",
    "profinet": "_check_profinet_dcp",
    "s7comm": "_check_s7_szl",
    "bacnet": "_check_bacnet_iam",
    "snmp": "_check_snmp_sysinfo",
}


def resolve_protocol(protocol: str) -> str:
    """Resolve protocol alias to parent protocol."""
    return PROTOCOL_ALIASES.get(protocol, protocol)


def mac_to_oui(mac: str) -> str:
    """Extract OUI prefix from MAC address."""
    parts = mac.upper().split(":")
    return ":".join(parts[:3])


# ─────────────────────────────────────────────────────────────────
# Main Validator Class
# ─────────────────────────────────────────────────────────────────

class PcapFingerprintValidator:
    """Validate protocol identity packets in a PCAP against expected fingerprints.

    Usage:
        packets = rdpcap("test.pcap")
        expectations = { "00:0E:8C:AB:12:34": DeviceExpectation(...), ... }
        validator = PcapFingerprintValidator(packets, expectations)
        reports = validator.validate_all()
    """

    def __init__(
        self,
        packets: list,
        device_expectations: dict[str, DeviceExpectation],
    ):
        """
        Args:
            packets: Scapy packet list from rdpcap().
            device_expectations: MAC address (upper) → DeviceExpectation.
        """
        self._packets = packets
        self._expectations = device_expectations
        # Index packets by source MAC for efficient lookup
        self._packets_by_src_mac: dict[str, list] = {}
        self._packets_by_src_ip: dict[str, list] = {}
        self._index_packets()

    def _index_packets(self) -> None:
        """Index packets by source MAC and source IP for efficient lookup."""
        for pkt in self._packets:
            if pkt.haslayer(Ether):
                src_mac = pkt[Ether].src.upper()
                self._packets_by_src_mac.setdefault(src_mac, []).append(pkt)
            if pkt.haslayer(IP):
                src_ip = pkt[IP].src
                self._packets_by_src_ip.setdefault(src_ip, []).append(pkt)

    def validate_all(self) -> list[DeviceValidationReport]:
        """Run all checks for all devices."""
        reports = []
        for mac, expectation in self._expectations.items():
            report = self._validate_device(expectation)
            reports.append(report)
        return reports

    def _validate_device(self, exp: DeviceExpectation) -> DeviceValidationReport:
        """Validate all protocol checks for a single device."""
        report = DeviceValidationReport(
            device_name=exp.device_name,
            device_ip=exp.ip_address,
            device_mac=exp.mac_address,
            vendor=exp.vendor,
            model=exp.model,
            protocols_serving=exp.protocols_serving,
        )

        # 1. MAC OUI check
        report.checks.extend(self._check_mac_oui(exp))

        # 2. TCP stack check (TTL, window size, MSS) from SYN-ACK
        report.checks.extend(self._check_tcp_stack(exp))

        # 3. Protocol-specific identity checks
        resolved_protocols = set()
        for proto_raw in exp.protocols_serving:
            parent = resolve_protocol(proto_raw)
            resolved_protocols.add(parent)

        for parent_proto in sorted(resolved_protocols):
            validator_name = PROTOCOL_TO_VALIDATOR.get(parent_proto)
            if validator_name:
                validator_fn = getattr(self, validator_name, None)
                if validator_fn:
                    report.checks.extend(validator_fn(exp, parent_proto))

        return report

    # ─────────────────────────────────────────────────────────────
    # MAC OUI Validation
    # ─────────────────────────────────────────────────────────────

    def _check_mac_oui(self, exp: DeviceExpectation) -> list[CheckResult]:
        """Check that device MAC uses correct vendor OUI prefix."""
        results = []
        expected_ouis = [o.upper() for o in exp.expected_oui_prefixes]
        assigned_oui = mac_to_oui(exp.mac_address)

        passed = assigned_oui in expected_ouis if expected_ouis else True
        results.append(CheckResult(
            device_name=exp.device_name,
            device_ip=exp.ip_address,
            protocol="mac",
            check_name="MAC OUI",
            expected=str(expected_ouis),
            actual=assigned_oui,
            passed=passed,
            detail=f"OUI {assigned_oui} {'in' if passed else 'NOT in'} {exp.expected_oui_prefixes}",
        ))

        return results

    # ─────────────────────────────────────────────────────────────
    # TCP Stack Validation
    # ─────────────────────────────────────────────────────────────

    def _check_tcp_stack(self, exp: DeviceExpectation) -> list[CheckResult]:
        """Check TCP stack characteristics (TTL, window) from SYN-ACK packets."""
        results = []
        tcp_stack = exp.fingerprint.get("tcp_stack", {})
        if not tcp_stack:
            return results

        expected_ttl = tcp_stack.get("ttl")
        if expected_ttl is None:
            return results

        # Find SYN-ACK packets from this device's IP
        device_packets = self._packets_by_src_ip.get(exp.ip_address, [])
        for pkt in device_packets:
            if pkt.haslayer(TCP):
                tcp = pkt[TCP]
                # SYN-ACK: flags = 0x12 (SYN + ACK)
                if tcp.flags == 0x12:
                    actual_ttl = pkt[IP].ttl if pkt.haslayer(IP) else None
                    if actual_ttl is not None:
                        results.append(CheckResult(
                            device_name=exp.device_name,
                            device_ip=exp.ip_address,
                            protocol="tcp",
                            check_name="TCP TTL",
                            expected=str(expected_ttl),
                            actual=str(actual_ttl),
                            passed=actual_ttl == expected_ttl,
                            detail=f"TTL {actual_ttl} (expected: {expected_ttl})",
                        ))

                    actual_window = tcp.window
                    expected_window = tcp_stack.get("window_size")
                    if expected_window is not None:
                        results.append(CheckResult(
                            device_name=exp.device_name,
                            device_ip=exp.ip_address,
                            protocol="tcp",
                            check_name="TCP Window Size",
                            expected=str(expected_window),
                            actual=str(actual_window),
                            passed=actual_window == expected_window,
                            detail=f"Window {actual_window} (expected: {expected_window})",
                        ))
                    break  # Only check first SYN-ACK

        return results

    # ─────────────────────────────────────────────────────────────
    # Modbus MEI (FC 43)
    # ─────────────────────────────────────────────────────────────

    def _check_modbus_mei(
        self, exp: DeviceExpectation, protocol: str,
    ) -> list[CheckResult]:
        """Check for Modbus MEI (FC 43) device identification responses."""
        results = []
        modbus_id = exp.fingerprint.get("modbus_identity", {})
        if not modbus_id:
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="modbus_tcp",
                check_name="Modbus identity",
                expected="present",
                actual="None",
                passed=False,
                detail="No modbus_identity in fingerprint",
            ))
            return results

        # Find MEI responses from this device
        device_packets = self._packets_by_src_ip.get(exp.ip_address, [])
        mei_responses = []
        for pkt in device_packets:
            if not pkt.haslayer(TCP) or not pkt.haslayer(Raw):
                continue
            payload = bytes(pkt[Raw].load)
            if len(payload) < 8:
                continue
            func_code = payload[7]
            if func_code == 0x2B and len(payload) > 10:
                mei_type = payload[8]
                if mei_type == 0x0E:
                    mei_responses.append(payload)

        if not mei_responses:
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="modbus_tcp",
                check_name="Modbus MEI present",
                expected="FC43 response",
                actual="not found",
                passed=False,
                detail="No FC43/MEI responses from device",
            ))
            return results

        results.append(CheckResult(
            device_name=exp.device_name,
            device_ip=exp.ip_address,
            protocol="modbus_tcp",
            check_name="Modbus MEI present",
            expected="FC43 response",
            actual=f"{len(mei_responses)} response(s)",
            passed=True,
            detail=f"Found {len(mei_responses)} FC43/MEI response(s)",
        ))

        # Parse the first MEI response
        objects = _parse_mei_objects(mei_responses[0])
        if objects:
            _check_mei_field(results, exp, objects, 0, "vendor_name", modbus_id)
            _check_mei_field(results, exp, objects, 1, "product_code", modbus_id)
            _check_mei_field(results, exp, objects, 2, "major_minor_revision", modbus_id)
            _check_mei_field(results, exp, objects, 4, "product_name", modbus_id)

        return results

    # ─────────────────────────────────────────────────────────────
    # EtherNet/IP ListIdentity
    # ─────────────────────────────────────────────────────────────

    def _check_enip_list_identity(
        self, exp: DeviceExpectation, protocol: str,
    ) -> list[CheckResult]:
        """Check for EtherNet/IP ListIdentity responses."""
        results = []
        enip_id = exp.fingerprint.get("ethernet_ip_identity", {})
        if not enip_id:
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="ethernet_ip",
                check_name="EtherNet/IP identity",
                expected="present",
                actual="None",
                passed=False,
                detail="No ethernet_ip_identity in fingerprint",
            ))
            return results

        # Search packets from this device for ListIdentity response (cmd 0x0063)
        device_packets = self._packets_by_src_ip.get(exp.ip_address, [])
        found = False

        for pkt in device_packets:
            if not pkt.haslayer(Raw):
                continue
            payload = bytes(pkt[Raw].load) if pkt.haslayer(Raw) else b""
            if pkt.haslayer(TCP) and pkt.haslayer(Raw):
                payload = bytes(pkt[Raw].load)
            elif pkt.haslayer(UDP) and pkt.haslayer(Raw):
                payload = bytes(pkt[Raw].load)
            else:
                continue

            if len(payload) < 24:
                continue

            command = struct.unpack_from("<H", payload, 0)[0]
            data_length = struct.unpack_from("<H", payload, 2)[0]

            if command == 0x0063 and data_length > 0:
                found = True
                results.append(CheckResult(
                    device_name=exp.device_name,
                    device_ip=exp.ip_address,
                    protocol="ethernet_ip",
                    check_name="EtherNet/IP ListIdentity",
                    expected="response",
                    actual="found",
                    passed=True,
                    detail="ListIdentity response packet found",
                ))
                results.extend(
                    _parse_enip_identity(exp, payload, enip_id)
                )
                break

        if not found:
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="ethernet_ip",
                check_name="EtherNet/IP ListIdentity",
                expected="response",
                actual="not found",
                passed=False,
                detail="No ListIdentity response from device",
            ))

        return results

    # ─────────────────────────────────────────────────────────────
    # S7comm SZL
    # ─────────────────────────────────────────────────────────────

    def _check_s7_szl(
        self, exp: DeviceExpectation, protocol: str,
    ) -> list[CheckResult]:
        """Check for S7comm SZL responses with identity data."""
        results = []
        s7_id = exp.fingerprint.get("s7_identity", {})
        if not s7_id:
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="s7comm",
                check_name="S7 identity",
                expected="present",
                actual="None",
                passed=False,
                detail="No s7_identity in fingerprint",
            ))
            return results

        device_packets = self._packets_by_src_ip.get(exp.ip_address, [])
        szl_data_parts: list[str] = []

        for pkt in device_packets:
            if not pkt.haslayer(TCP) or not pkt.haslayer(Raw):
                continue
            payload = bytes(pkt[Raw].load)
            if len(payload) < 10 or payload[0] != 0x03:
                continue

            # Find S7 protocol marker (0x32)
            s7_offset = None
            for i in range(2, min(len(payload) - 1, 20)):
                if payload[i] == 0x32:
                    s7_offset = i
                    break
            if s7_offset is None:
                continue

            rosctr = payload[s7_offset + 1]
            if rosctr == 0x07:  # Userdata (SZL)
                data = payload[s7_offset:]
                text = data.decode("ascii", errors="replace")
                szl_data_parts.append(text)

        if not szl_data_parts:
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="s7comm",
                check_name="S7 SZL present",
                expected="SZL response",
                actual="not found",
                passed=False,
                detail="No SZL userdata responses from device",
            ))
            return results

        results.append(CheckResult(
            device_name=exp.device_name,
            device_ip=exp.ip_address,
            protocol="s7comm",
            check_name="S7 SZL present",
            expected="SZL response",
            actual=f"{len(szl_data_parts)} response(s)",
            passed=True,
            detail=f"Found {len(szl_data_parts)} SZL userdata responses",
        ))

        # Search all SZL data for expected fields
        combined = "".join(szl_data_parts)

        for field_key, label in [
            ("module_type", "S7 module_type"),
            ("order_code", "S7 order_code"),
            ("firmware_version", "S7 firmware"),
        ]:
            expected_val = s7_id.get(field_key, "")
            if not expected_val:
                continue
            # For order_code, match first 8 chars (shortened in SZL)
            search_val = expected_val[:8] if field_key == "order_code" else expected_val
            found = search_val in combined
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="s7comm",
                check_name=label,
                expected=expected_val,
                actual=search_val if found else "not found",
                passed=found,
                detail=f"'{search_val}' {'found' if found else 'NOT found'} in SZL data",
            ))

        # Serial: look for Siemens serial pattern "S " prefix
        serial_match = re.search(r"S [A-Z0-9-]{6,}", combined)
        results.append(CheckResult(
            device_name=exp.device_name,
            device_ip=exp.ip_address,
            protocol="s7comm",
            check_name="S7 serial",
            expected="serial pattern",
            actual=serial_match.group() if serial_match else "not found",
            passed=serial_match is not None,
            detail=f"Serial '{serial_match.group()}' found" if serial_match
            else "No serial pattern found in SZL data",
        ))

        return results

    # ─────────────────────────────────────────────────────────────
    # PROFINET DCP
    # ─────────────────────────────────────────────────────────────

    def _check_profinet_dcp(
        self, exp: DeviceExpectation, protocol: str,
    ) -> list[CheckResult]:
        """Check for PROFINET DCP Identify responses."""
        results = []
        pn_id = exp.fingerprint.get("profinet_identity", {})
        if not pn_id:
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="profinet",
                check_name="PROFINET identity",
                expected="present",
                actual="None",
                passed=False,
                detail="No profinet_identity in fingerprint",
            ))
            return results

        # PROFINET uses L2 — match by source MAC
        device_packets = self._packets_by_src_mac.get(exp.mac_address, [])
        dcp_response_payload = None

        for pkt in device_packets:
            if not pkt.haslayer(Ether):
                continue
            eth = pkt[Ether]
            if eth.type != 0x8892:
                continue

            if pkt.haslayer(Raw):
                payload = bytes(pkt[Raw].load)
            else:
                payload = bytes(pkt)[14:]

            if len(payload) < 4:
                continue

            frame_id = struct.unpack_from(">H", payload, 0)[0]
            if frame_id == 0xFEFF:  # DCP Identify Response
                dcp_response_payload = payload
                break

        if not dcp_response_payload:
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="profinet",
                check_name="PROFINET DCP Identify",
                expected="response",
                actual="not found",
                passed=False,
                detail="No DCP Identify Response from device",
            ))
            return results

        results.append(CheckResult(
            device_name=exp.device_name,
            device_ip=exp.ip_address,
            protocol="profinet",
            check_name="PROFINET DCP Identify",
            expected="response",
            actual="found",
            passed=True,
            detail="DCP Identify Response found",
        ))

        # Parse DCP blocks
        results.extend(_parse_dcp_blocks(exp, dcp_response_payload, pn_id))

        return results

    # ─────────────────────────────────────────────────────────────
    # BACnet I-Am
    # ─────────────────────────────────────────────────────────────

    def _check_bacnet_iam(
        self, exp: DeviceExpectation, protocol: str,
    ) -> list[CheckResult]:
        """Check for BACnet I-Am broadcasts and identity strings."""
        results = []
        bacnet_id = exp.fingerprint.get("bacnet_identity", {})
        if not bacnet_id:
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="bacnet",
                check_name="BACnet identity",
                expected="present",
                actual="None",
                passed=False,
                detail="No bacnet_identity in fingerprint",
            ))
            return results

        device_packets = self._packets_by_src_ip.get(exp.ip_address, [])
        iam_found = False
        identity_strings_found: dict[str, str] = {}

        for pkt in device_packets:
            if not pkt.haslayer(UDP) or not pkt.haslayer(Raw):
                continue
            if pkt[UDP].dport != 47808 and pkt[UDP].sport != 47808:
                continue

            payload = bytes(pkt[Raw].load)
            if len(payload) < 8 or payload[0] != 0x81:
                continue

            # Parse NPDU to find APDU
            npdu_offset = 4
            if npdu_offset >= len(payload):
                continue
            npdu_control = payload[npdu_offset + 1]
            npdu_len = 2
            if npdu_control & 0x20:
                npdu_len += 4
                if npdu_offset + 2 < len(payload):
                    dlen = payload[npdu_offset + 4]
                    npdu_len += dlen

            apdu_offset = npdu_offset + npdu_len
            if apdu_offset >= len(payload):
                continue

            apdu_type = (payload[apdu_offset] >> 4) & 0x0F
            if apdu_type == 0x01 and apdu_offset + 1 < len(payload):
                service_choice = payload[apdu_offset + 1]
                if service_choice == 0x00:
                    iam_found = True

            # Search for identity strings
            text = payload.decode("ascii", errors="replace")
            for key, field_name in [
                ("vendor_name", bacnet_id.get("vendor_name", "")),
                ("model_name", bacnet_id.get("model_name", "")),
                ("firmware_revision", bacnet_id.get("firmware_revision", "")),
            ]:
                if field_name and field_name in text and key not in identity_strings_found:
                    identity_strings_found[key] = field_name

        results.append(CheckResult(
            device_name=exp.device_name,
            device_ip=exp.ip_address,
            protocol="bacnet",
            check_name="BACnet I-Am",
            expected="I-Am broadcast",
            actual="found" if iam_found else "not found",
            passed=iam_found,
            detail="I-Am broadcast found" if iam_found else "No I-Am broadcast from device",
        ))

        for key, label in [
            ("vendor_name", "BACnet vendor_name"),
            ("model_name", "BACnet model_name"),
            ("firmware_revision", "BACnet firmware"),
        ]:
            expected_val = bacnet_id.get(key, "")
            if not expected_val:
                continue
            found = identity_strings_found.get(key)
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="bacnet",
                check_name=label,
                expected=expected_val,
                actual=found or "not found",
                passed=found is not None,
                detail=f"'{found}' found" if found
                else f"'{expected_val}' NOT found in any BACnet packet",
            ))

        return results

    # ─────────────────────────────────────────────────────────────
    # SNMP sysinfo
    # ─────────────────────────────────────────────────────────────

    def _check_snmp_sysinfo(
        self, exp: DeviceExpectation, protocol: str,
    ) -> list[CheckResult]:
        """Check for SNMP GetResponse with system info."""
        results = []
        snmp_id = exp.fingerprint.get("snmp_identity", {})
        if not snmp_id:
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="snmp",
                check_name="SNMP identity",
                expected="present",
                actual="None",
                passed=False,
                detail="No snmp_identity in fingerprint",
            ))
            return results

        device_packets = self._packets_by_src_ip.get(exp.ip_address, [])
        # SNMP engine uses device_name for sysName, not fingerprint's sys_name.
        # Check for both to be robust.
        sys_name_candidates = []
        if exp.device_name:
            sys_name_candidates.append(exp.device_name)
        fp_sys_name = snmp_id.get("sys_name", "")
        if fp_sys_name and fp_sys_name not in sys_name_candidates:
            sys_name_candidates.append(fp_sys_name)

        snmp_responses = 0
        found_fields: dict[str, str] = {}

        for pkt in device_packets:
            if not pkt.haslayer(UDP):
                continue
            if pkt[UDP].sport != 161:
                continue

            payload = bytes(pkt[UDP].payload)
            if len(payload) < 10 or payload[0] != 0x30:
                continue

            snmp_responses += 1
            text = payload.decode("ascii", errors="replace")
            # Note: sysObjectID is BER-encoded (binary OID), not text-searchable
            sys_descr_val = snmp_id.get("sys_descr", "")
            if sys_descr_val and sys_descr_val[:20] in text and "sys_descr" not in found_fields:
                found_fields["sys_descr"] = sys_descr_val
            # sysName: check device_name first (engine priority), then fingerprint
            if "sys_name" not in found_fields:
                for candidate in sys_name_candidates:
                    if candidate and candidate[:20] in text:
                        found_fields["sys_name"] = candidate
                        break

        results.append(CheckResult(
            device_name=exp.device_name,
            device_ip=exp.ip_address,
            protocol="snmp",
            check_name="SNMP responses",
            expected="GetResponse",
            actual=f"{snmp_responses} response(s)" if snmp_responses else "not found",
            passed=snmp_responses > 0,
            detail=f"Found {snmp_responses} GetResponse packets"
            if snmp_responses else "No SNMP GetResponse from device",
        ))

        # sysDescr check
        sys_descr_val = snmp_id.get("sys_descr", "")
        if sys_descr_val:
            found = found_fields.get("sys_descr")
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="snmp",
                check_name="SNMP sysDescr",
                expected=sys_descr_val[:60],
                actual=found[:60] if found else "not found",
                passed=found is not None,
                detail=f"'{found[:60]}' found" if found
                else f"'{sys_descr_val[:40]}' NOT found in SNMP responses",
            ))

        # sysName check — engine uses device_name, so check for that
        sys_name_expected = exp.device_name or snmp_id.get("sys_name", "")
        if sys_name_expected:
            found = found_fields.get("sys_name")
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="snmp",
                check_name="SNMP sysName",
                expected=sys_name_expected[:60],
                actual=found[:60] if found else "not found",
                passed=found is not None,
                detail=f"'{found[:60]}' found" if found
                else f"'{sys_name_expected[:40]}' NOT found in SNMP responses",
            ))

        return results


# ─────────────────────────────────────────────────────────────────
# Helper Functions (extracted from cv_fingerprint_test.py)
# ─────────────────────────────────────────────────────────────────

def _parse_mei_objects(payload: bytes) -> dict[int, str]:
    """Parse Modbus MEI response objects."""
    objects: dict[int, str] = {}
    try:
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


def _check_mei_field(
    results: list[CheckResult],
    exp: DeviceExpectation,
    objects: dict[int, str],
    obj_id: int,
    field_name: str,
    modbus_id: dict,
) -> None:
    """Check a single MEI object field."""
    expected_val = modbus_id.get(field_name, "")
    actual_val = objects.get(obj_id, "")

    if actual_val:
        passed = actual_val == expected_val if expected_val else True
        results.append(CheckResult(
            device_name=exp.device_name,
            device_ip=exp.ip_address,
            protocol="modbus_tcp",
            check_name=f"Modbus {field_name}",
            expected=expected_val or "(any)",
            actual=actual_val,
            passed=passed,
            detail=f"'{actual_val}'" + (f" (expected: '{expected_val}')" if expected_val else ""),
        ))
    elif expected_val:
        results.append(CheckResult(
            device_name=exp.device_name,
            device_ip=exp.ip_address,
            protocol="modbus_tcp",
            check_name=f"Modbus {field_name}",
            expected=expected_val,
            actual="not found",
            passed=False,
            detail=f"'{field_name}' NOT FOUND in MEI response",
        ))


def _parse_enip_identity(
    exp: DeviceExpectation,
    payload: bytes,
    expected: dict,
) -> list[CheckResult]:
    """Parse EtherNet/IP ListIdentity response for identity data."""
    results = []
    try:
        offset = 24  # Skip encapsulation header
        if offset + 2 > len(payload):
            return results
        item_count = struct.unpack_from("<H", payload, offset)[0]
        offset += 2

        for _ in range(item_count):
            if offset + 4 > len(payload):
                break
            type_id, length = struct.unpack_from("<HH", payload, offset)
            offset += 4

            if type_id == 0x000C and length > 20:
                id_offset = offset
                id_offset += 2  # protocol_version
                id_offset += 16  # socket address

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
                id_offset += 2  # status
                serial = struct.unpack_from("<I", payload, id_offset)[0]
                id_offset += 4
                name_len = payload[id_offset]
                id_offset += 1
                product_name = payload[id_offset:id_offset + name_len].decode(
                    "ascii", errors="replace"
                )

                exp_vendor_id = expected.get("vendor_id")
                if exp_vendor_id is not None:
                    results.append(CheckResult(
                        device_name=exp.device_name,
                        device_ip=exp.ip_address,
                        protocol="ethernet_ip",
                        check_name="EtherNet/IP vendor_id",
                        expected=str(exp_vendor_id),
                        actual=str(vendor_id),
                        passed=vendor_id == exp_vendor_id,
                        detail=f"{vendor_id} (expected: {exp_vendor_id})",
                    ))

                exp_product_name = expected.get("product_name", "")
                results.append(CheckResult(
                    device_name=exp.device_name,
                    device_ip=exp.ip_address,
                    protocol="ethernet_ip",
                    check_name="EtherNet/IP product_name",
                    expected=exp_product_name or "(any)",
                    actual=product_name or "EMPTY",
                    passed=bool(product_name),
                    detail=f"'{product_name}'" if product_name else "EMPTY",
                ))

                results.append(CheckResult(
                    device_name=exp.device_name,
                    device_ip=exp.ip_address,
                    protocol="ethernet_ip",
                    check_name="EtherNet/IP serial_number",
                    expected="non-zero",
                    actual=f"0x{serial:08X}",
                    passed=serial != 0,
                    detail=f"0x{serial:08X}",
                ))

                results.append(CheckResult(
                    device_name=exp.device_name,
                    device_ip=exp.ip_address,
                    protocol="ethernet_ip",
                    check_name="EtherNet/IP revision",
                    expected="(any)",
                    actual=f"{rev_major}.{rev_minor}",
                    passed=True,
                    detail=f"{rev_major}.{rev_minor}",
                ))
                return results

            offset += length

    except Exception as e:
        results.append(CheckResult(
            device_name=exp.device_name,
            device_ip=exp.ip_address,
            protocol="ethernet_ip",
            check_name="EtherNet/IP parse",
            expected="parseable",
            actual=str(e),
            passed=False,
            detail=f"Parse error: {e}",
        ))
    return results


def _parse_dcp_blocks(
    exp: DeviceExpectation,
    payload: bytes,
    expected: dict,
) -> list[CheckResult]:
    """Parse PROFINET DCP blocks for identity data."""
    results = []
    try:
        offset = 12  # Skip FrameID + ServiceID + ServiceType + Xid + ResponseDelay + DataLength
        if offset >= len(payload):
            return results

        found_vendor_id = None
        found_device_id = None
        found_station_name = None
        found_oem_device_id = None

        while offset + 4 <= len(payload):
            option = payload[offset]
            suboption = payload[offset + 1]
            block_len = struct.unpack_from(">H", payload, offset + 2)[0]
            offset += 4

            if offset + block_len > len(payload):
                break

            block_data = payload[offset:offset + block_len]

            if option == 0x02:  # Device Properties
                if suboption == 0x03 and len(block_data) >= 4:
                    found_vendor_id = struct.unpack_from(">H", block_data, 0)[0]
                    found_device_id = struct.unpack_from(">H", block_data, 2)[0]
                elif suboption == 0x02 and len(block_data) >= 1:
                    found_station_name = block_data.decode("ascii", errors="replace").rstrip("\x00")
                elif suboption == 0x08 and len(block_data) >= 5:
                    found_oem_device_id = block_data.decode("ascii", errors="replace").rstrip("\x00")

            offset += block_len
            if block_len % 2 == 1:
                offset += 1

        # Validate vendor_id
        exp_vendor_id = expected.get("vendor_id")
        if found_vendor_id is not None:
            passed = found_vendor_id == exp_vendor_id if exp_vendor_id else True
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="profinet",
                check_name="PROFINET vendor_id",
                expected=f"0x{exp_vendor_id:04X}" if exp_vendor_id else "(any)",
                actual=f"0x{found_vendor_id:04X}",
                passed=passed,
                detail=f"0x{found_vendor_id:04X}" + (f" (expected: 0x{exp_vendor_id:04X})" if exp_vendor_id else ""),
            ))
        else:
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="profinet",
                check_name="PROFINET vendor_id",
                expected=f"0x{exp_vendor_id:04X}" if exp_vendor_id else "(any)",
                actual="not found",
                passed=False,
                detail="NOT found in DCP blocks",
            ))

        # Validate station_name
        if found_station_name:
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="profinet",
                check_name="PROFINET station_name",
                expected="(any non-empty)",
                actual=found_station_name,
                passed=True,
                detail=f"'{found_station_name}'",
            ))
        else:
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="profinet",
                check_name="PROFINET station_name",
                expected="station name",
                actual="not found",
                passed=False,
                detail="NOT found in DCP blocks",
            ))

        # Validate OEM Device ID (firmware, serial, order code)
        if found_oem_device_id:
            oem_parts: dict[str, str] = {}
            for part in found_oem_device_id.split(";"):
                if ":" in part:
                    k, v = part.split(":", 1)
                    oem_parts[k.strip()] = v.strip()

            for oem_key, label in [
                ("SW", "PROFINET firmware (OEM)"),
                ("SN", "PROFINET serial (OEM)"),
                ("OrderID", "PROFINET order_code (OEM)"),
            ]:
                val = oem_parts.get(oem_key, "")
                results.append(CheckResult(
                    device_name=exp.device_name,
                    device_ip=exp.ip_address,
                    protocol="profinet",
                    check_name=label,
                    expected="(present)",
                    actual=val or "MISSING",
                    passed=bool(val),
                    detail=f"{oem_key}='{val}'" if val else f"{oem_key} field MISSING in OEM",
                ))
        else:
            results.append(CheckResult(
                device_name=exp.device_name,
                device_ip=exp.ip_address,
                protocol="profinet",
                check_name="PROFINET OEM Device ID",
                expected="OEM block",
                actual="not found",
                passed=False,
                detail="OEM Device ID NOT found in DCP blocks",
            ))

    except Exception as e:
        results.append(CheckResult(
            device_name=exp.device_name,
            device_ip=exp.ip_address,
            protocol="profinet",
            check_name="PROFINET DCP parse",
            expected="parseable",
            actual=str(e),
            passed=False,
            detail=f"Parse error: {e}",
        ))

    return results
