#!/usr/bin/env python3
"""
Create a test scenario with devices covering all fingerprinting protocols.
Each device has explicit CVE data with known firmware versions for validation.

Usage:
    cd /home/rocsmith/PacketArch/backend
    poetry run python scripts/create_fingerprint_test_scenario.py

This creates:
1. A scenario with 4 test devices (one per vendor/protocol combination)
2. /tmp/expected_fingerprints.json with expected values for validation
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import async_session_maker
from app.models.scenario import Scenario
from app.services.cve_fingerprint_service import CVEFingerprintService


# Test device configurations - one per vendor/protocol
TEST_DEVICES = [
    {
        "id": f"siemens-plc-{uuid4().hex[:8]}",
        "name": "Siemens S7-1516 Test",
        "type": "plc",
        "vendor": "Siemens",
        "fingerprintModel": "CPU 1516-3 PN/DP",
        "protocols": ["profinet", "s7comm_plus"],
        "cveIds": ["CVE-2020-15782"],
        "network": {
            "ipAddress": "10.99.0.10",
            "macAddress": "00:0E:8C:01:00:10",  # Siemens AG OUI
            "subnetMask": "255.255.255.0",
            "gateway": "10.99.0.1",
        },
        "expected_firmware": "V2.9.1",
        "expected_fingerprints": {
            "snmp_sys_descr": "Siemens SIMATIC S7-1500 CPU 1516-3 PN/DP V2.9.1",
            "snmp_sys_object_id": "1.3.6.1.4.1.4329.2.51.1516",
            "profinet_sw_release": "V2.9.1",
            "s7_firmware_version": "V2.9.1",
            "s7_order_code": "6ES7 516-3AN01-0AB0",
        }
    },
    {
        "id": f"rockwell-plc-{uuid4().hex[:8]}",
        "name": "Rockwell ControlLogix Test",
        "type": "plc",
        "vendor": "Rockwell",
        "fingerprintModel": "1756-L85E",
        "protocols": ["ethernet_ip"],
        "cveIds": ["CVE-2022-1159"],
        "network": {
            "ipAddress": "10.99.0.20",
            "macAddress": "00:1D:9C:02:00:20",
            "subnetMask": "255.255.255.0",
            "gateway": "10.99.0.1",
        },
        "expected_firmware": "32.011",
        "expected_fingerprints": {
            "snmp_sys_descr_contains": "Rockwell",
            "snmp_sys_descr_contains_fw": "32.011",
            "enip_revision_major": 32,
            "enip_revision_minor": 11,
        }
    },
    {
        "id": f"schneider-plc-{uuid4().hex[:8]}",
        "name": "Schneider M340 Test",
        "type": "plc",
        "vendor": "Schneider Electric",
        "fingerprintModel": "Modicon M340",
        "protocols": ["modbus_tcp"],
        "cveIds": ["CVE-2019-6857"],
        "network": {
            "ipAddress": "10.99.0.30",
            "macAddress": "00:80:F4:03:00:30",
            "subnetMask": "255.255.255.0",
            "gateway": "10.99.0.1",
        },
        "expected_firmware": "2.80",
        "expected_fingerprints": {
            "snmp_sys_descr_contains": "Schneider",
            "snmp_sys_descr_contains_fw": "2.80",
            "modbus_major_minor_revision": "2.80",
        }
    },
    {
        "id": f"jci-controller-{uuid4().hex[:8]}",
        "name": "JCI NAE55 Test",
        "type": "controller",
        "vendor": "Johnson Controls",
        "fingerprintModel": "NAE55",
        "protocols": ["bacnet_ip"],
        "cveIds": [],
        "network": {
            "ipAddress": "10.99.0.40",
            "macAddress": "00:1A:17:04:00:40",  # Johnson Controls OUI
            "subnetMask": "255.255.255.0",
            "gateway": "10.99.0.1",
        },
        "expected_firmware": "12.0.3",
        "expected_fingerprints": {
            "bacnet_firmware_revision": "12.0.3",
            "snmp_sys_descr_contains": "Johnson Controls",
        }
    },
]

# Create an HMI to poll the PLCs
HMI_DEVICE = {
    "id": f"hmi-{uuid4().hex[:8]}",
    "name": "Engineering HMI",
    "type": "hmi",
    "vendor": "Generic",
    "fingerprintModel": "HMI Panel",
    "protocols": [],
    "cveIds": [],
    "network": {
        "ipAddress": "10.99.0.100",
        "macAddress": "00:AA:BB:CC:DD:EE",
        "subnetMask": "255.255.255.0",
        "gateway": "10.99.0.1",
    },
}


async def resolve_cve_overrides(db, device: dict) -> dict:
    """Resolve CVE identity overrides for a device."""
    if not device.get("cveIds"):
        return device

    try:
        # Service expects snake_case keys
        resolved = await CVEFingerprintService.resolve_device_cve_config(
            db=db,
            device_spec={
                "vendor": device["vendor"],
                "fingerprint_model": device["fingerprintModel"],  # snake_case
                "cve_ids": device["cveIds"],  # snake_case
            }
        )

        # Service returns snake_case, we need to convert to camelCase for scenario
        if resolved.get("cve_identity_overrides"):
            device["cveIdentityOverrides"] = resolved["cve_identity_overrides"]
            device["vulnerableFirmware"] = resolved.get("vulnerable_firmware", "")
            print(f"  Resolved CVE overrides for {device['name']}")
            print(f"    Firmware: {device.get('vulnerableFirmware', 'N/A')}")

            # Show what identity data we got
            overrides = device["cveIdentityOverrides"]
            if overrides.get("snmp_identity"):
                snmp = overrides["snmp_identity"]
                print(f"    SNMP sysDescr: {snmp.get('sys_descr', 'N/A')[:60]}...")
    except Exception as e:
        print(f"  Warning: Could not resolve CVE for {device['name']}: {e}")
        import traceback
        traceback.print_exc()

    return device


async def create_test_scenario():
    """Create the fingerprint test scenario."""
    print("=" * 60)
    print("Creating Fingerprint Test Scenario")
    print("=" * 60)

    async with async_session_maker() as db:
        # Resolve CVE overrides for each device
        devices = {}
        for device in TEST_DEVICES:
            print(f"\nProcessing: {device['name']}")
            resolved = await resolve_cve_overrides(db, device.copy())
            devices[resolved["id"]] = resolved

        # Add HMI
        devices[HMI_DEVICE["id"]] = HMI_DEVICE.copy()

        # Create flows from HMI to each PLC
        flows = {}
        for device in TEST_DEVICES:
            for protocol in device["protocols"]:
                flow_id = f"flow-{uuid4().hex[:8]}"
                flows[flow_id] = {
                    "id": flow_id,
                    "sourceDeviceId": HMI_DEVICE["id"],
                    "targetDeviceId": device["id"],
                    "protocol": protocol,
                    "config": {
                        "poll_interval_ms": 1000,
                    },
                    "timing": {
                        "interval_ms": 1000,
                        "jitter_percent": 5,
                    },
                }

        # Create the scenario definition
        scenario_def = {
            "devices": devices,
            "flows": flows,
            "zones": {},
        }

        # Create the scenario
        scenario = Scenario(
            name=f"Fingerprint Validation Test - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            description="Test scenario for validating firmware fingerprinting across all protocols",
            definition=scenario_def,
            user_id=None,  # System-created
        )

        db.add(scenario)
        await db.commit()
        await db.refresh(scenario)

        print(f"\n{'=' * 60}")
        print(f"Created scenario: {scenario.id}")
        print(f"Name: {scenario.name}")
        print(f"{'=' * 60}")

        # Build expected fingerprints with IP mapping
        expected = {}
        for device in TEST_DEVICES:
            ip = device["network"]["ipAddress"]
            expected[ip] = {
                "device_name": device["name"],
                "vendor": device["vendor"],
                "protocols": device["protocols"],
                "expected_firmware": device["expected_firmware"],
                **device["expected_fingerprints"],
            }

        # Write expected values to JSON
        expected_path = Path("/tmp/expected_fingerprints.json")
        with open(expected_path, "w") as f:
            json.dump(expected, f, indent=2)
        print(f"\nExpected values written to: {expected_path}")

        # Print summary
        print("\nTest Devices:")
        print("-" * 60)
        for device in TEST_DEVICES:
            ip = device["network"]["ipAddress"]
            protocols = ", ".join(device["protocols"])
            print(f"  {device['name']}")
            print(f"    IP: {ip}")
            print(f"    Vendor: {device['vendor']}")
            print(f"    Protocols: {protocols}")
            print(f"    Expected Firmware: {device['expected_firmware']}")
            print()

        return str(scenario.id)


async def main():
    """Main entry point."""
    try:
        scenario_id = await create_test_scenario()
        print(f"\nScenario ID: {scenario_id}")
        print("\nNext steps:")
        print("1. Deploy this scenario to the traffic generator")
        print("2. Capture packets: sudo tcpdump -i ens3 -w /tmp/fingerprint_test.pcap -c 5000")
        print("3. Run validation: poetry run python scripts/validate_fingerprint_packets.py --pcap /tmp/fingerprint_test.pcap")
        return scenario_id
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    scenario_id = asyncio.run(main())
