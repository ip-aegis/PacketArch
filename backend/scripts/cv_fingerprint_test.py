#!/usr/bin/env python3
"""CV Fingerprint Diagnostic — Generate PCAPs, inspect identity packets.

Standalone script — NO database, NO server required.
Generates a short PCAP per protocol, parses with scapy, reports PASS/FAIL.

Uses the shared pcap_validators library for protocol-specific parsing.

Usage:
    cd /home/rocsmith/PacketArch/backend
    poetry run python scripts/cv_fingerprint_test.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Suppress noisy scapy warnings
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

from scapy.all import rdpcap

from app.protocol_engines.output import PcapOutput
from app.protocol_engines.types import DeviceContext, FlowContext, ProtocolType
from app.protocol_engines.unified_orchestrator import UnifiedOrchestrator
from app.services.device_templates._fingerprints import get_fingerprint_from_template

from scripts.lib.pcap_validators import (
    DeviceExpectation,
    PcapFingerprintValidator,
)

# ─────────────────────────────────────────────────────────────────
# Test Matrix: one device per protocol
# ─────────────────────────────────────────────────────────────────

TEST_CASES = [
    {
        "name": "Modbus - Schneider M340",
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
        "name": "EtherNet/IP - Rockwell ControlLogix",
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
        "name": "S7comm - Siemens S7-1500",
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
        "name": "PROFINET - Siemens S7-1500",
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
        "name": "BACnet - Honeywell JACE 8000",
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
        "name": "SNMP - Schneider ConneXium",
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

    # Phase 2: Analyze PCAPs using shared validator
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

        # Build DeviceExpectation for the shared validator
        expectation = DeviceExpectation(
            device_id="device-under-test",
            device_name=name,
            mac_address=dst_mac.upper(),
            ip_address=dst_ip,
            vendor=fp.get("vendor", "unknown"),
            model=fp.get("model", "unknown"),
            fingerprint=fp,
            expected_oui_prefixes=tc.get("expected_oui", []),
            protocols_serving={tc["protocol"]},
        )

        # Run shared validator
        validator = PcapFingerprintValidator(
            packets,
            {dst_mac.upper(): expectation},
        )
        device_reports = validator.validate_all()

        # Convert structured results to the legacy console format
        for dr in device_reports:
            for check in dr.checks:
                report(name, check.check_name, check.detail, check.passed)

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
