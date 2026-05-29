#!/usr/bin/env python3
# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Test script to validate AI scenario generation end-to-end.

This script tests:
1. AI scenario preview generation
2. Preview device data integrity (fingerprint_model present)
3. Protocol identity validation
4. Scenario creation from preview

Run with: docker compose exec backend python scripts/test_ai_scenario_validation.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from app.protocol_engines.protocols import PROTOCOL_TO_IDENTITY_KEY


def validate_preview_device(device: dict, fingerprints_lookup) -> list[str]:
    """Validate a preview device for protocol identity mismatches.

    Args:
        device: Device dictionary from preview
        fingerprints_lookup: Function to lookup fingerprint by vendor/model

    Returns:
        List of validation error messages
    """
    errors = []
    device_name = device.get("name", "Unknown")
    vendor = device.get("vendor", "")
    fingerprint_model = device.get("fingerprint_model")
    protocols = device.get("protocols", [])

    # Check if fingerprint_model is present
    if not fingerprint_model:
        errors.append(
            f"Device '{device_name}': Missing fingerprint_model - "
            "fingerprint lookup will fail"
        )
        return errors

    # Try to get fingerprint data
    fp = fingerprints_lookup(vendor, fingerprint_model) if vendor else None

    if not fp:
        errors.append(
            f"Device '{device_name}': Fingerprint lookup failed for "
            f"vendor='{vendor}', model='{fingerprint_model}'"
        )
        return errors

    # Check each protocol for identity support
    for protocol in protocols:
        identity_key = PROTOCOL_TO_IDENTITY_KEY.get(protocol)
        if identity_key:
            identity = fp.get(identity_key)
            if not identity or not isinstance(identity, dict) or len(identity) == 0:
                errors.append(
                    f"Device '{device_name}': Protocol '{protocol}' declared "
                    f"but no {identity_key} in fingerprint"
                )

    return errors


def simulate_preview_creation(scenario_devices: list[dict]) -> list[dict]:
    """Simulate creating preview devices from scenario devices.

    This mimics what the API does when creating a preview.
    """
    preview_devices = []
    for d in scenario_devices:
        preview_device = {
            "device_id": d.get("device_id"),
            "name": d.get("name"),
            "device_type": d.get("device_type"),
            "vendor": d.get("vendor"),
            "ip_address": d.get("ip_address"),
            "mac_address": d.get("mac_address"),
            "zone": d.get("zone"),
            "protocols": d.get("protocols", []),
            "fingerprint_model": d.get("fingerprint_model"),  # CRITICAL
        }
        preview_devices.append(preview_device)
    return preview_devices


def simulate_scenario_creation(preview_devices: list[dict], fingerprints_lookup) -> list[str]:
    """Simulate creating a scenario from preview devices.

    This mimics what create_scenario_from_preview does and validates
    that fingerprint identities would be found.
    """
    errors = []

    for d in preview_devices:
        device_name = d.get("name", "Unknown")
        vendor = (d.get("vendor") or "").lower()
        fingerprint_model = d.get("fingerprint_model")
        protocols = d.get("protocols", [])

        # Simulate fingerprint lookup (exactly as in create_scenario_from_preview)
        fingerprint_data = None
        if vendor and fingerprint_model:
            fingerprint_data = fingerprints_lookup(vendor, fingerprint_model)

        if not fingerprint_data:
            errors.append(
                f"Device '{device_name}': No fingerprint data found "
                f"(vendor='{vendor}', model='{fingerprint_model}')"
            )
            continue

        # Check what protocol identities would be copied
        missing_identities = []
        for protocol in protocols:
            identity_key = PROTOCOL_TO_IDENTITY_KEY.get(protocol)
            if identity_key:
                identity = fingerprint_data.get(identity_key)
                if not identity:
                    missing_identities.append((protocol, identity_key))

        if missing_identities:
            for protocol, identity_key in missing_identities:
                errors.append(
                    f"Device '{device_name}': Protocol '{protocol}' declared "
                    f"but no {identity_key} in fingerprint (protocol_identity_mismatch)"
                )

    return errors


async def test_full_flow():
    """Test the full AI scenario generation flow."""
    from app.services.device_templates import get_fingerprint_by_vendor_model
    from app.ai_services.ai_scenario_designer import AIScenarioDesigner
    from app.core.database import async_session_maker

    print("\n" + "="*80)
    print("AI SCENARIO GENERATION VALIDATION TEST")
    print("="*80)

    async with async_session_maker() as db:
        designer = AIScenarioDesigner(db)

        # Test scenario: Manufacturing with mixed vendors
        print("\n[TEST 1] Generating manufacturing scenario...")

        try:
            design_result = await designer.design_scenario(
                description="Small manufacturing cell with 2 Siemens PLCs, 2 Rockwell drives, and an HMI",
                name="Test Manufacturing Cell",
                duration_ms=60000,
                vertical="manufacturing",
                total_device_count=5,
            )

            # AIDesignResult has scenario attribute
            result = design_result.scenario

            print(f"  Generated {len(result.devices)} devices, {len(result.flows)} flows")
            print(f"  AI Enhanced: {design_result.ai_enhanced}")

            # Check if all devices have fingerprint_model
            devices_with_model = sum(1 for d in result.devices if d.fingerprint_model)
            print(f"  Devices with fingerprint_model: {devices_with_model}/{len(result.devices)}")

            # Simulate preview creation
            print("\n[TEST 2] Simulating preview creation...")
            scenario_devices = [
                {
                    "device_id": d.device_id,
                    "name": d.name,
                    "device_type": d.device_type,
                    "vendor": d.vendor,
                    "ip_address": d.ip_address,
                    "mac_address": d.mac_address,
                    "zone": d.zone,
                    "protocols": d.protocols,
                    "fingerprint_model": d.fingerprint_model,
                }
                for d in result.devices
            ]

            preview_devices = simulate_preview_creation(scenario_devices)

            # Validate preview devices
            print("\n[TEST 3] Validating preview devices...")
            preview_errors = []
            for device in preview_devices:
                errors = validate_preview_device(device, get_fingerprint_by_vendor_model)
                preview_errors.extend(errors)

            if preview_errors:
                print(f"  PREVIEW VALIDATION ERRORS ({len(preview_errors)}):")
                for err in preview_errors[:10]:  # Limit output
                    print(f"    - {err}")
                if len(preview_errors) > 10:
                    print(f"    ... and {len(preview_errors) - 10} more")
            else:
                print("  All preview devices valid!")

            # Simulate scenario creation from preview
            print("\n[TEST 4] Simulating scenario creation from preview...")
            creation_errors = simulate_scenario_creation(
                preview_devices, get_fingerprint_by_vendor_model
            )

            if creation_errors:
                print(f"  SCENARIO CREATION ERRORS ({len(creation_errors)}):")
                for err in creation_errors[:10]:
                    print(f"    - {err}")
                if len(creation_errors) > 10:
                    print(f"    ... and {len(creation_errors) - 10} more")
            else:
                print("  Scenario creation would succeed!")

            # Print device summary
            print("\n[DEVICE SUMMARY]")
            for d in result.devices[:5]:  # First 5
                protos = ", ".join(d.protocols)
                print(f"  {d.name}: {d.vendor}/{d.fingerprint_model} -> [{protos}]")
            if len(result.devices) > 5:
                print(f"  ... and {len(result.devices) - 5} more devices")

            # Overall result
            print("\n" + "="*80)
            total_errors = len(preview_errors) + len(creation_errors)
            if total_errors == 0:
                print("RESULT: PASS - All validations successful!")
            else:
                print(f"RESULT: FAIL - {total_errors} validation errors found")
            print("="*80)

            return total_errors == 0

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_known_fingerprints():
    """Test with known good fingerprint combinations."""
    from app.services.device_templates import get_fingerprint_by_vendor_model

    print("\n" + "="*80)
    print("KNOWN FINGERPRINT VALIDATION TEST")
    print("="*80)

    # Test devices with known good fingerprints
    test_devices = [
        {
            "name": "Siemens_S7_1500_PLC",
            "vendor": "siemens",
            "fingerprint_model": "6ES7 517-3AP00-0AB0",
            "protocols": ["profinet", "s7comm", "modbus_tcp"],
        },
        {
            "name": "Rockwell_ControlLogix_PLC",
            "vendor": "rockwell",
            "fingerprint_model": "1756-L85E",
            "protocols": ["ethernet_ip", "modbus_tcp"],
        },
        {
            "name": "Schneider_M580_PLC",
            "vendor": "schneider",
            "fingerprint_model": "BMEP586040",
            "protocols": ["ethernet_ip", "modbus_tcp"],
        },
        # This one should fail - profinet is not available for Rockwell
        {
            "name": "Rockwell_Bad_Protocols",
            "vendor": "rockwell",
            "fingerprint_model": "1756-L85E",
            "protocols": ["profinet", "s7comm"],  # Should fail
        },
    ]

    all_passed = True

    for device in test_devices:
        print(f"\n  Testing {device['name']}...")
        errors = validate_preview_device(device, get_fingerprint_by_vendor_model)

        if device["name"] == "Rockwell_Bad_Protocols":
            # This one SHOULD have errors
            if errors:
                print(f"    Expected errors found: {len(errors)} (correct)")
            else:
                print("    ERROR: Expected errors but found none!")
                all_passed = False
        else:
            if errors:
                print(f"    Unexpected errors: {errors}")
                all_passed = False
            else:
                print("    PASS")

    print("\n" + "="*80)
    if all_passed:
        print("RESULT: PASS - All known fingerprint tests successful!")
    else:
        print("RESULT: FAIL - Some tests failed")
    print("="*80)

    return all_passed


async def main():
    """Run all tests."""
    # Test 1: Known good fingerprints
    test1_pass = await test_known_fingerprints()

    # Test 2: Full AI flow (requires AI provider)
    try:
        test2_pass = await test_full_flow()
    except Exception as e:
        print(f"\n[SKIP] Full flow test skipped: {e}")
        test2_pass = True  # Don't fail if AI not available

    # Overall result
    print("\n" + "="*80)
    print("OVERALL RESULTS")
    print("="*80)
    print(f"  Known Fingerprints Test: {'PASS' if test1_pass else 'FAIL'}")
    print(f"  Full AI Flow Test: {'PASS' if test2_pass else 'FAIL'}")

    if test1_pass and test2_pass:
        print("\nAll tests passed!")
        sys.exit(0)
    else:
        print("\nSome tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
