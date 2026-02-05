#!/usr/bin/env python3
"""Test script to diagnose AI scenario generation fingerprint identity issues.

This script tests the entire flow:
1. Get available fingerprints (what AI sees)
2. Simulate AI scenario generation
3. Verify fingerprint lookup works for AI-selected models
4. Check protocol identity coverage
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.device_templates import (
    get_all_fingerprints,
    get_fingerprint_by_vendor_model,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from app.protocol_engines.protocols import PROTOCOL_TO_IDENTITY_KEY


def test_fingerprint_availability():
    """Test 1: Check available fingerprints and their protocol support."""
    print("\n" + "="*80)
    print("TEST 1: Fingerprint Availability and Protocol Support")
    print("="*80)

    fingerprints = get_all_fingerprints()
    print(f"\nTotal fingerprints available: {len(fingerprints)}")

    # Group by vendor and count protocols
    vendor_stats = {}
    protocol_coverage = {p: 0 for p in PROTOCOL_TO_IDENTITY_KEY.keys()}

    for fp in fingerprints:
        vendor = fp.get("vendor", "Unknown")
        model = fp.get("model", "Unknown")

        if vendor not in vendor_stats:
            vendor_stats[vendor] = {"count": 0, "models": [], "protocols": set()}

        vendor_stats[vendor]["count"] += 1
        vendor_stats[vendor]["models"].append(model)

        # Check which protocols this fingerprint supports
        for protocol, identity_key in PROTOCOL_TO_IDENTITY_KEY.items():
            identity = fp.get(identity_key)
            if identity and isinstance(identity, dict) and len(identity) > 0:
                vendor_stats[vendor]["protocols"].add(protocol)
                protocol_coverage[protocol] += 1

    # Print vendor summary
    print("\nVendors and their fingerprint counts:")
    for vendor, stats in sorted(vendor_stats.items(), key=lambda x: -x[1]["count"]):
        protocols = ", ".join(sorted(stats["protocols"])) if stats["protocols"] else "NONE"
        print(f"  {vendor}: {stats['count']} models, protocols: {protocols}")

    # Print protocol coverage
    print("\nProtocol coverage across all fingerprints:")
    for protocol, count in sorted(protocol_coverage.items(), key=lambda x: -x[1]):
        print(f"  {protocol}: {count} fingerprints")

    return fingerprints


def test_fingerprint_lookup(vendor: str, model: str):
    """Test 2: Test fingerprint lookup for a specific vendor/model."""
    print(f"\n  Testing lookup: vendor='{vendor}', model='{model}'")

    fp = get_fingerprint_by_vendor_model(vendor, model)

    if fp is None:
        print(f"    ❌ FAILED: No fingerprint found")
        return None

    print(f"    ✓ Found fingerprint: {fp.get('vendor')} {fp.get('model')}")

    # Check protocol identities
    supported = []
    missing = []

    for protocol, identity_key in PROTOCOL_TO_IDENTITY_KEY.items():
        identity = fp.get(identity_key)
        if identity and isinstance(identity, dict) and len(identity) > 0:
            supported.append(protocol)
        else:
            missing.append(protocol)

    print(f"    Supported protocols: {', '.join(supported) if supported else 'NONE'}")

    return fp


def test_common_ai_selections():
    """Test 3: Test lookup for common models the AI might select."""
    print("\n" + "="*80)
    print("TEST 3: Testing Common AI Model Selections")
    print("="*80)

    # These are models that AI is likely to select based on the prompt
    common_selections = [
        # Siemens
        ("siemens", "6ES7 517-3AP00-0AB0"),
        ("Siemens", "6ES7 517-3AP00-0AB0"),
        ("siemens", "6ES7 516-3AN02-0AB0"),
        ("siemens", "6ES7 515-2AM02-0AB0"),

        # Rockwell
        ("rockwell", "1756-L85E"),
        ("Rockwell", "1756-L85E"),
        ("rockwell", "1769-L33ER"),

        # Schneider
        ("schneider", "BMEP586040"),
        ("Schneider", "BMEP586040"),

        # ABB
        ("abb", "PM5650"),
        ("ABB", "PM5650"),

        # Generic device types (might fail)
        ("siemens", "S7-1500"),
        ("rockwell", "ControlLogix"),
        ("generic", "PLC"),
    ]

    results = {"success": 0, "failed": 0}

    for vendor, model in common_selections:
        fp = test_fingerprint_lookup(vendor, model)
        if fp:
            results["success"] += 1
        else:
            results["failed"] += 1

    print(f"\nResults: {results['success']} success, {results['failed']} failed")
    return results


def test_protocol_identity_validation():
    """Test 4: Simulate protocol identity validation like deployment does."""
    print("\n" + "="*80)
    print("TEST 4: Protocol Identity Validation Simulation")
    print("="*80)

    # Simulate a device that might be created by AI
    test_devices = [
        {
            "name": "CNC_Cell_A_Main_PLC",
            "vendor": "rockwell",
            "fingerprint_model": "1756-L85E",
            "protocols": ["ethernet_ip", "modbus_tcp"],
        },
        {
            "name": "Cleanroom_Assembly_PLC",
            "vendor": "siemens",
            "fingerprint_model": "6ES7 517-3AP00-0AB0",
            "protocols": ["profinet", "s7comm"],
        },
        {
            "name": "Bath_Temperature_Transmitter",
            "vendor": "siemens",
            "fingerprint_model": None,  # Missing model - common AI mistake
            "protocols": ["modbus_tcp"],
        },
        {
            "name": "Generic_PLC",
            "vendor": "siemens",
            "fingerprint_model": "Generic PLC",  # Invalid model
            "protocols": ["modbus_tcp", "ethernet_ip"],
        },
    ]

    issues = []

    for device in test_devices:
        print(f"\n  Device: {device['name']}")
        print(f"    Vendor: {device['vendor']}, Model: {device['fingerprint_model']}")
        print(f"    Requested protocols: {device['protocols']}")

        # Simulate fingerprint lookup
        fp = None
        if device['vendor'] and device['fingerprint_model']:
            fp = get_fingerprint_by_vendor_model(device['vendor'], device['fingerprint_model'])

        if fp is None:
            print(f"    ❌ No fingerprint found!")
            issues.append(f"{device['name']}: No fingerprint for {device['vendor']}/{device['fingerprint_model']}")
            continue

        # Check each protocol
        device_issues = []
        for protocol in device['protocols']:
            identity_key = PROTOCOL_TO_IDENTITY_KEY.get(protocol)
            if identity_key:
                identity = fp.get(identity_key)
                if not identity or not isinstance(identity, dict) or len(identity) == 0:
                    device_issues.append(protocol)
                    print(f"    ❌ Protocol '{protocol}' has no {identity_key}")
                else:
                    print(f"    ✓ Protocol '{protocol}' has valid {identity_key}")

        if device_issues:
            issues.append(f"{device['name']}: Missing identities for {device_issues}")

    print(f"\n  Total validation issues: {len(issues)}")
    for issue in issues:
        print(f"    - {issue}")

    return issues


def analyze_fingerprint_models():
    """Test 5: List all available model strings for reference."""
    print("\n" + "="*80)
    print("TEST 5: Available Fingerprint Models by Vendor")
    print("="*80)

    fingerprints = get_all_fingerprints()

    by_vendor = {}
    for fp in fingerprints:
        vendor = fp.get("vendor", "Unknown")
        model = fp.get("model", "Unknown")

        if vendor not in by_vendor:
            by_vendor[vendor] = []

        # Get supported protocols
        protocols = []
        for protocol, identity_key in PROTOCOL_TO_IDENTITY_KEY.items():
            identity = fp.get(identity_key)
            if identity and isinstance(identity, dict) and len(identity) > 0:
                protocols.append(protocol)

        by_vendor[vendor].append((model, protocols))

    # Print first 5 models per vendor with their protocols
    for vendor in sorted(by_vendor.keys()):
        models = by_vendor[vendor][:5]
        print(f"\n{vendor}:")
        for model, protocols in models:
            proto_str = ", ".join(protocols) if protocols else "NONE"
            print(f"  '{model}' → {proto_str}")
        if len(by_vendor[vendor]) > 5:
            print(f"  ... and {len(by_vendor[vendor]) - 5} more")


def main():
    """Run all diagnostic tests."""
    print("\n" + "="*80)
    print("AI SCENARIO GENERATION FINGERPRINT DIAGNOSTIC")
    print("="*80)

    # Test 1: Check what fingerprints are available
    fingerprints = test_fingerprint_availability()

    # Test 3: Test common AI selections
    test_common_ai_selections()

    # Test 4: Simulate validation
    test_protocol_identity_validation()

    # Test 5: List all models
    analyze_fingerprint_models()

    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
